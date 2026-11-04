from copy import deepcopy
from dataclasses import fields
import json
import unittest
from unittest.mock import patch

from experiments.memory.identity import DEFAULT_CONFIG, add_frame, configuration, match_components, track
from experiments.memory.identity_data import PublicFrame, SCENARIOS, dataset_splits, generate
from experiments.memory.identity_learning import (
    VERSION, evaluate, experiment, fit, loss, persist_experiment, score_transition,
)
from experiments.memory.store import Memory


def only(seed, scenario):
    return [sequence for sequence in generate(seed) if sequence.scenario == scenario]


class IdentityLearningTests(unittest.TestCase):
    def test_reproducible_generator_covers_scenarios(self):
        self.assertEqual(generate(11), generate(11))
        self.assertNotEqual(generate(11), generate(23))
        self.assertEqual({sequence.scenario for sequence in generate(11)}, set(SCENARIOS))

    def test_private_labels_never_enter_perception_or_matching(self):
        self.assertEqual({field.name for field in fields(PublicFrame)}, {"signal", "occurred_at"})
        seen = []

        def checked(left, right, interval, config):
            self.assertNotIn("control-", json.dumps([left, right, config]))
            self.assertFalse(any("entity_id" in c for c in left+right))
            seen.append(True)
            return match_components(left, right, interval, config)

        with patch("experiments.memory.identity_learning.match_components", side_effect=checked):
            evaluate(generate(11), configuration())
        self.assertTrue(seen)

    def test_disjoint_seeds_and_no_test_access_during_fit(self):
        splits = dataset_splits()
        train = {s.seed for s in splits["training"]}
        test = {s.seed for s in splits["test"]}
        self.assertFalse(train & test)
        with self.assertRaises(ValueError):
            dataset_splits(training=(11,), validation=(11,), test=(23,))
        first = experiment(splits)
        changed_test = {**splits, "test": generate(999)}
        second = experiment(changed_test)
        self.assertEqual(first["selected_config"], second["selected_config"])
        self.assertEqual(first["search_scores"], second["search_scores"])

    def test_metrics_distinguish_all_error_and_uncertainty_categories(self):
        comparison = {"pairs": [
            {"from_component": "a", "to_component": "x", "status": "same_entity"},
            {"from_component": "b", "to_component": "y", "status": "same_entity"},
            {"from_component": "c", "to_component": "z", "status": "unknown_identity"},
            {"from_component": "d", "to_component": "w", "status": "different_entity"}]}
        left = {"a": "A", "b": "B", "c": "C", "d": "D"}
        right = {"x": "A", "y": "OTHER", "z": "C", "w": "D"}
        result = score_transition(comparison, left, right)
        self.assertEqual(result["correct_matches"], 1)
        self.assertEqual(result["false_matches"], 1)
        self.assertEqual(result["missed_correspondences"], 2)
        self.assertEqual(result["missed_decisive"], 1)
        self.assertEqual(result["avoidable_unknown"], 1)
        self.assertEqual(result["justified_unknown"], 0)
        justified = score_transition(comparison, left, right, ambiguous=True)
        self.assertEqual(justified["justified_unknown"], 1)
        self.assertEqual(justified["avoidable_unknown"], 0)
        self.assertEqual(result["true_correspondences"], result["correct_matches"]+result["missed_correspondences"])

    def test_false_identification_cost_exceeds_abstention_and_miss(self):
        errors = {"false_matches": 1, "missed_decisive": 0, "avoidable_unknown": 0}
        missed = {"false_matches": 0, "missed_decisive": 1, "avoidable_unknown": 0}
        unknown = {"false_matches": 0, "missed_decisive": 0, "avoidable_unknown": 1}
        self.assertGreater(loss(errors), loss(missed))
        self.assertGreater(loss(missed), loss(unknown))
        # Replacement controls prevent learning an overly permissive area threshold.
        result = experiment()
        self.assertEqual(result["selected_config"]["max_area_change"], .6)
        self.assertEqual(result["test_selected"]["metrics"]["false_matches"], 0)

    def test_baseline_is_preserved_and_new_parameters_are_explicit(self):
        baseline = deepcopy(DEFAULT_CONFIG)
        result = experiment()
        self.assertEqual(DEFAULT_CONFIG, baseline)
        self.assertEqual(configuration(), baseline)
        self.assertEqual(result["baseline_config"], baseline)
        self.assertEqual(result["test_outcome"], "improved")
        self.assertNotEqual(result["selected_config"], baseline)
        self.assertEqual(result["selected_config"]["weights"], baseline["weights"])

    def test_no_improvement_is_reported_and_baseline_retained(self):
        result = experiment(candidates=[configuration()])
        self.assertEqual(result["selection"], "baseline_retained")
        self.assertEqual(result["test_outcome"], "no_improvement")
        self.assertEqual(result["test_baseline"], result["test_selected"])

    def test_overfitting_and_negative_test_result_are_reported(self):
        splits = {"training": only(11, "resize"), "validation": only(101, "resize"),
                  "test": only(211, "replacement")}
        result = experiment(splits)
        self.assertEqual(result["test_outcome"], "worse")
        self.assertGreater(result["test_selected"]["metrics"]["false_matches"],
                           result["test_baseline"]["metrics"]["false_matches"])

    def test_ambiguous_crossing_stays_unknown(self):
        result = experiment()
        for config in (result["baseline_config"], result["selected_config"]):
            metrics = evaluate(only(211, "crossing"), config)["metrics"]
            self.assertEqual(metrics["correct_matches"], 0)
            self.assertEqual(metrics["false_matches"], 0)
            self.assertEqual(metrics["justified_unknown"], 2)

    def test_persistence_preserves_old_events_and_keeps_control_labels_separate(self):
        memory = Memory(":memory:")
        try:
            ids = [add_frame(memory, field, f"2026-11-04T00:00:0{i}Z")
                   for i, field in enumerate(["#...", ".#.."]) ]
            track(memory, ids)
            before = {row[0]: tuple(row) for row in memory.db.execute("SELECT * FROM events")}
            splits = dataset_splits(training=(11,), validation=(101,), test=(211,))
            result = experiment(splits)
            eid = persist_experiment(memory, result, splits)
            count = memory.db.execute("SELECT count(*) FROM events").fetchone()[0]
            self.assertEqual(eid, persist_experiment(memory, result, splits))
            self.assertEqual(count, memory.db.execute("SELECT count(*) FROM events").fetchone()[0])
            for old_id, row in before.items():
                self.assertEqual(row, tuple(memory.db.execute("SELECT * FROM events WHERE id=?", (old_id,)).fetchone()))
            for row in memory.db.execute("SELECT payload FROM events WHERE kind='observation'"):
                payload = json.loads(row[0])
                self.assertEqual(set(payload), {"signal", "format", "frame_id"})
                self.assertNotIn("control-", json.dumps(payload))
            study = memory.get(eid)
            self.assertEqual(study["payload"]["algorithm_version"], VERSION)
            self.assertTrue(study["parent_id"])
            self.assertTrue(memory.db.execute("SELECT 1 FROM event_links WHERE source_id=?", (eid,)).fetchone())
        finally:
            memory.close()


if __name__ == "__main__":
    unittest.main()
