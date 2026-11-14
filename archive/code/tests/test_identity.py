import tempfile
import unittest
from pathlib import Path

from experiments.memory.identity import add_frame, track
from experiments.memory.store import Memory


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.memory = Memory(":memory:")
        self.addCleanup(self.memory.close)

    def frames(self, fields, times=None):
        times = times or [f"2026-11-04T00:00:0{i}Z" for i in range(len(fields))]
        return [add_frame(self.memory, field, time, frame_id=f"frame-{i}")
                for i, (field, time) in enumerate(zip(fields, times))]

    def payload(self, eid):
        return self.memory.get(eid)["payload"]

    def test_movement_builds_one_entity_history(self):
        ids = self.frames(["#....", ".#...", "..#.."])
        run = track(self.memory, ids)
        self.assertEqual(len(run["current_entities"]), 1)
        history = next(iter(run["current_entities"].values()))["history"]
        self.assertEqual([step["frame_id"] for step in history], ids)
        entities = {self.payload(eid)["entity_id"] for eid in run["identity_hypothesis_ids"]}
        self.assertEqual(len(entities), 1)
        self.assertTrue(all(self.payload(eid)["pairs"][0]["status"] == "same_entity"
                            for eid in run["matching_ids"]))

    def test_two_identical_objects_keep_distinct_trajectories(self):
        ids = self.frames(["#.......#..", ".#.......#.", "..#.......#"])
        run = track(self.memory, ids)
        self.assertEqual(len(run["current_entities"]), 2)
        self.assertEqual(len({v["entity_id"] for v in run["current_entities"].values()}), 2)
        self.assertTrue(all(len(v["history"]) == 3 for v in run["current_entities"].values()))

    def test_indistinguishable_exchange_retains_alternatives_and_no_entity_id(self):
        ids = self.frames([".#..#.", ".#..#."])
        run = track(self.memory, ids)
        comparison = self.payload(run["matching_ids"][0])
        self.assertEqual(len(comparison["alternatives"]), 2)
        for alternative in comparison["alternatives"]:
            matches = alternative["matches"]
            self.assertEqual(len(matches), len({match["from_component"] for match in matches}))
            self.assertEqual(len(matches), len({match["to_component"] for match in matches}))
        self.assertTrue(all(pair["status"] == "unknown_identity" for pair in comparison["pairs"]))
        self.assertEqual(run["current_entities"], {})
        self.assertTrue(all(self.payload(eid)["entity_id"] is None for eid in run["identity_hypothesis_ids"]))

    def test_disappearance_does_not_claim_destruction(self):
        ids = self.frames(["#....", ".#...", "....."])
        run = track(self.memory, ids)
        last = self.payload(run["matching_ids"][-1])
        self.assertEqual(last["unmatched_previous"], ["component_1"])
        self.assertIn("no destruction claim", last["absence_meaning"])
        self.assertEqual(run["current_entities"], {})
        self.assertEqual(self.payload(run["identity_hypothesis_ids"][0])["status"], "same_entity")

    def test_small_shape_change_is_supported_with_recorded_changes(self):
        ids = self.frames([".#....", "..##.."])
        run = track(self.memory, ids)
        pair = self.payload(run["matching_ids"][0])["pairs"][0]
        self.assertEqual(pair["status"], "same_entity")
        self.assertEqual(pair["changes"]["cell_count"], 1)
        self.assertEqual(pair["metrics"]["shape"], .5)

    def test_global_assignment_avoids_greedy_nearest_pair_trap(self):
        ids = self.frames(["#..#..", "..#..#"])
        run = track(self.memory, ids)
        comparison = self.payload(run["matching_ids"][0])
        supported = [p for p in comparison["pairs"] if p["status"] == "same_entity"]
        self.assertEqual(len(supported), 2)
        self.assertEqual(len({p["to_component"] for p in supported}), 2)
        self.assertEqual(len({p["from_component"] for p in supported}), 2)
        self.assertEqual({(p["from_component"], p["to_component"]) for p in supported},
                         {("component_1", "component_1"), ("component_2", "component_2")})

    def test_equal_timestamps_produce_unknown_without_division_by_zero(self):
        ids = self.frames(["#...", ".#.."], ["2026-11-04T00:00:00Z"]*2)
        run = track(self.memory, ids)
        pair = self.payload(run["matching_ids"][0])["pairs"][0]
        self.assertEqual(pair["status"], "unknown_identity")
        self.assertIsNone(pair["cost"])
        self.assertEqual(run["current_entities"], {})

    def test_speed_rejection_and_symbol_not_an_absolute_identifier(self):
        ids = self.frames(["#.......", ".......#"])
        pair = self.payload(track(self.memory, ids)["matching_ids"][0])["pairs"][0]
        self.assertEqual(pair["status"], "different_entity")
        self.assertIn("movement_exceeds_speed_limit", pair["reasons"])
        ids = self.frames([".#..", ".@.."])
        pair = self.payload(track(self.memory, ids)["matching_ids"][0])["pairs"][0]
        self.assertEqual(pair["status"], "same_entity")
        self.assertEqual(pair["metrics"]["signal"], 1)

    def test_immutability_evidence_and_idempotence_after_appending_frame(self):
        ids = self.frames(["#....", ".#..."])
        before = [self.memory.get(eid) for eid in ids]
        first = track(self.memory, ids)
        count = self.memory.db.execute("SELECT count(*) FROM events").fetchone()[0]
        self.assertEqual(first, track(self.memory, ids))
        self.assertEqual(count, self.memory.db.execute("SELECT count(*) FROM events").fetchone()[0])
        self.assertEqual(before, [self.memory.get(eid) for eid in ids])
        extended = ids + [add_frame(self.memory, "..#..", "2026-11-04T00:00:02Z")]
        second = track(self.memory, extended)
        self.assertEqual(first["matching_ids"], second["matching_ids"][:1])
        self.assertEqual(first["identity_hypothesis_ids"], second["identity_hypothesis_ids"][:1])
        for eid in second["matching_ids"] + second["identity_hypothesis_ids"]:
            targets = {row[0] for row in self.memory.db.execute(
                "SELECT target_id FROM event_links WHERE source_id=? AND relation='evidence'", (eid,))}
            self.assertTrue(targets)
            self.assertTrue(targets <= set(extended))

    def test_reopening_reuses_events(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "memory.db")
            memory = Memory(path)
            ids = [add_frame(memory, field, f"2026-11-04T00:00:0{i}Z")
                   for i, field in enumerate(["#...", ".#.."]) ]
            first = track(memory, ids)
            memory.close()
            memory = Memory(path)
            try:
                self.assertEqual(first, track(memory, ids))
            finally:
                memory.close()

    def test_search_bound_and_invalid_configuration(self):
        ids = self.frames(["#.#.#", "#.#.#"])
        run = track(self.memory, ids, {"max_components": 2})
        self.assertEqual(self.payload(run["matching_ids"][0])["status"], "unknown_identity")
        self.assertEqual(run["current_entities"], {})
        with self.assertRaises(ValueError):
            track(self.memory, ids, {"max_speed": 0})
        with self.assertRaises(ValueError):
            track(self.memory, list(reversed(ids)))

    def test_large_time_gap_does_not_reidentify_automatically(self):
        ids = self.frames(["#...", "#..."], ["2026-11-04T00:00:00Z", "2026-11-04T00:01:00Z"])
        run = track(self.memory, ids)
        self.assertEqual(self.payload(run["matching_ids"][0])["pairs"][0]["status"], "unknown_identity")
        self.assertEqual(run["current_entities"], {})


if __name__ == "__main__":
    unittest.main()
