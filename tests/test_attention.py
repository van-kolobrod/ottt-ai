import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from experiments.memory.attention import attend, choose, generate_candidates, observations
from experiments.memory.store import Memory


class AttentionTests(unittest.TestCase):
    def setUp(self):
        self.memory = Memory(":memory:")
        self.addCleanup(self.memory.close)

    def add(self, features, source="sensor", object_id=None, time=None):
        return self.memory.add("observation", {"features": features, "object_id": object_id},
                               source=source, occurred_at=time)

    def candidates(self, kind):
        return [c for c in generate_candidates(observations(self.memory)) if c.type == kind]

    def test_repeated_property_generated_from_distinct_observations(self):
        ids = {self.add({"sides": 4}, source=f"source-{i}") for i in range(3)}
        candidate = self.candidates("repeated_property")[0]
        self.assertEqual(set(candidate.evidence_ids), ids)
        self.assertEqual(candidate.measurements["support_count"], 3)
        self.assertEqual(candidate.metrics["recurrence"], 1)
        self.assertTrue(candidate.question)
        self.assertTrue(candidate.verification)

    def test_rare_combination_relative_to_frequent_marginals(self):
        # Each value recurs; (True, True) occurs once, expected 3*3/5=1.8.
        for a, b in [(True, True), (True, False), (True, False), (False, True), (False, True)]:
            self.add({"a": a, "b": b})
        candidates = self.candidates("rare_combination")
        candidate = next(c for c in candidates if c.features == {"a": True, "b": True})
        self.assertEqual(candidate.measurements["support_count"], 1)
        self.assertAlmostEqual(candidate.measurements["expected_count_under_independence"], 1.8)
        self.assertAlmostEqual(candidate.metrics["novelty"], 1 - 1 / 1.8)
        self.assertEqual(len(candidate.evidence_ids), 5)  # includes comparison evidence

    def test_time_change_and_missing_context_are_not_established_conflicts(self):
        self.add({"temperature": 10}, "a", "object", "2026-11-04T10:00:00+00:00")
        self.add({"temperature": 20}, "b", "object", "2026-11-04T11:00:00+00:00")
        self.add({"temperature": 30}, None, "object")
        candidates = self.candidates("potential_contradiction")
        self.assertEqual(len(candidates), 3)
        self.assertTrue(all(c.uncertainty for c in candidates))
        decision = choose(candidates, threshold=0)
        self.assertIsNone(decision["selected_id"])
        self.assertTrue(any("possible_state_change_between_times" in c.uncertainty for c in candidates))

    def test_same_instant_different_sources_is_only_potential_disagreement(self):
        self.add({"state": "open"}, "a", "door", "2026-11-04T10:00:00Z")
        self.add({"state": "closed"}, "b", "door", "2026-11-04T13:00:00+03:00")
        candidate = self.candidates("potential_contradiction")[0]
        self.assertEqual(candidate.measurements["context_status"], "simultaneous_source_disagreement")
        self.assertEqual(candidate.uncertainty, ())
        self.assertIsNotNone(choose([candidate])["selected_id"])
        self.assertIn("identity", candidate.verification)

    def test_different_objects_are_not_contradictions(self):
        self.add({"state": 1}, "a", "one")
        self.add({"state": 2}, "b", "two")
        self.assertEqual(self.candidates("potential_contradiction"), [])

    def test_two_modes_select_different_memory_derived_candidates(self):
        for i in range(6):
            self.add({"stable": True, "target": i < 2}, f"source-{i}")
        candidates = generate_candidates(observations(self.memory))
        exploratory = choose(candidates)
        directed = choose(candidates, mode="goal_directed", goal={"features": ["target"]})
        by_id = {c.id: c for c in candidates}
        self.assertEqual(by_id[exploratory["selected_id"]].features, {"stable": True})
        self.assertIn("target", by_id[directed["selected_id"]].features)
        self.assertNotEqual(exploratory["selected_id"], directed["selected_id"])
        for assessment in directed["assessments"]:
            self.assertAlmostEqual(assessment["score"], sum(assessment["weighted_contributions"].values()))

    def test_abstention_for_single_observation_or_missing_provenance(self):
        self.add({"value": 1})
        self.assertIsNone(choose(generate_candidates(observations(self.memory)))["selected_id"])
        self.assertIsNone(choose([])["selected_id"])
        with self.assertRaises(ValueError):
            choose([], mode="goal_directed")
        with self.assertRaises(ValueError):
            choose([], threshold=float("nan"))

    def test_unsupported_observations_and_numeric_representation(self):
        raw = self.memory.add("observation", {"signal": "###"})
        self.add({"value": 1}, "a", "same", "2026-11-04T10:00:00Z")
        self.add({"value": 1.0}, "b", "same", "2026-11-04T10:00:00Z")
        self.assertEqual(self.candidates("potential_contradiction"), [])
        self.assertEqual(self.candidates("repeated_property")[0].measurements["support_count"], 2)
        decision = self.memory.get(attend(self.memory))["payload"]
        self.assertEqual(decision["unsupported_observation_ids"], [raw])

    def test_missing_sources_prevent_selection_and_same_source_conflict_is_uncertain(self):
        self.add({"value": 1}, None)
        self.add({"value": 1}, None)
        self.assertIsNone(choose(generate_candidates(observations(self.memory)))["selected_id"])
        self.add({"state": 1}, "same", "object", "2026-11-04T10:00:00Z")
        self.add({"state": 2}, "same", "object", "2026-11-04T10:00:00Z")
        self.assertIn("same_source_not_independent", self.candidates("potential_contradiction")[0].uncertainty)

    def test_refusal_for_unrelated_goal_and_high_threshold(self):
        self.add({"a": True}, "one")
        self.add({"a": True}, "two")
        candidates = generate_candidates(observations(self.memory))
        self.assertIsNone(choose(candidates, mode="goal_directed", goal={"features": ["missing"]})["selected_id"])
        self.assertIsNone(choose(candidates, threshold=1)["selected_id"])

    def test_provenance_idempotence_immutability_and_new_snapshot(self):
        ids = [self.add({"value": True}, f"source-{i}") for i in range(3)]
        before = [tuple(self.memory.db.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()) for eid in ids]
        self.memory.archive(ids[0])
        first = attend(self.memory)
        self.assertEqual(first, attend(self.memory))
        payload = self.memory.get(first)["payload"]
        self.assertEqual(set(payload["input_observation_ids"]), set(ids))
        links = self.memory.db.execute("SELECT target_id FROM event_links WHERE source_id=?", (first,)).fetchall()
        self.assertEqual({row[0] for row in links}, set(ids))
        after = [tuple(self.memory.db.execute("SELECT * FROM events WHERE id=?", (eid,)).fetchone()) for eid in ids]
        self.assertEqual(before, after)
        self.assertEqual(self.memory.get(ids[0])["tier"], "archive")
        self.add({"value": False}, "new")
        self.assertNotEqual(first, attend(self.memory))
        self.assertEqual(self.memory.get(first)["payload"], payload)

    def test_idempotence_survives_reopening_and_separates_configurations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "memory.db")
            memory = Memory(path)
            memory.add("observation", {"features": {"a": 1}}, source="a")
            memory.add("observation", {"features": {"a": 1}}, source="b")
            first = attend(memory)
            memory.close()
            memory = Memory(path)
            try:
                self.assertEqual(first, attend(memory))
                self.assertNotEqual(first, attend(memory, threshold=.99))
                self.assertNotEqual(first, attend(memory, mode="goal_directed", goal={"features": ["a"]}))
            finally:
                memory.close()

    def test_event_and_evidence_links_roll_back_together(self):
        count = self.memory.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):
            self.memory.add("research_decision", {}, concepts=["test"], links=[("considers", "missing")])
        self.assertEqual(self.memory.db.execute("SELECT COUNT(*) FROM events").fetchone()[0], count)


if __name__ == "__main__":
    unittest.main()
