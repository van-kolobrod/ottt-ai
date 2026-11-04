import json
import tempfile
import unittest
from pathlib import Path

from experiments.memory.store import Memory
from experiments.memory.perception import extract_components, component_relations
from experiments.memory.spatial import (
    DEFAULT_DICTIONARY, add_signal, classify, interpret_perception, perceive_event,
)


class SpatialPerceptionTests(unittest.TestCase):
    def test_two_distinct_signal_components_and_relations(self):
        components = extract_components("##...@@\n##...@@")
        self.assertEqual([(c["signal"], c["cell_count"]) for c in components], [("#", 4), ("@", 4)])
        relation = component_relations(components)[0]
        self.assertTrue(relation["left_of"])
        self.assertTrue(relation["vertical_projection_overlap"])
        self.assertAlmostEqual(relation["center_distance"], 5.0)

    def test_diagonal_contact_is_not_connected(self):
        components = extract_components("#.\n.#")
        self.assertEqual(len(components), 2)
        self.assertEqual([component["cell_count"] for component in components], [1, 1])

    def test_internal_hole_is_detected(self):
        component = extract_components("###\n#.#\n###")[0]
        self.assertEqual(component["holes"]["count"], 1)
        self.assertEqual(component["holes"]["cells"], [[1, 1]])
        self.assertTrue(component["features"]["rectangular_frame"])

    def test_signal_source_and_reanalysis_are_immutable_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(str(Path(directory) / "memory.sqlite3"))
            try:
                field = "##..\n##.."
                observation_id = add_signal(memory, field, source="test_sensor")
                original_payload = memory.get(observation_id)["payload"]
                first = perceive_event(memory, observation_id)
                second = perceive_event(memory, observation_id)
                self.assertEqual(first, second)
                self.assertEqual(memory.get(observation_id)["payload"], original_payload)
                self.assertEqual(original_payload["signal"], field)
                self.assertEqual(memory.db.execute(
                    "SELECT COUNT(*) FROM events WHERE parent_id=? AND kind='perception'",
                    (observation_id,),
                ).fetchone()[0], 1)
            finally:
                memory.close()

    def test_dictionary_interprets_previously_saved_perception(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(str(Path(directory) / "memory.sqlite3"))
            try:
                observation_id = add_signal(memory, "###\n#.#\n###")
                perception_id = perceive_event(memory, observation_id)
                # A newly supplied dictionary interprets the already stored feature record.
                dictionary_path = Path(directory) / "new_rules.json"
                dictionary_path.write_text(json.dumps({
                    "version": 42, "rules": {
                        "eight_cell_structure": {"required": {"cell_count": 8},
                                                  "parent": "test_structure"}
                    }
                }), encoding="utf-8")
                interpretation_id = interpret_perception(memory, perception_id, dictionary_path)
                results = memory.get(interpretation_id)["payload"]["results"]
                self.assertIn({"component_id": "component_1", "concept": "eight_cell_structure",
                               "status": "matched", "missing": [], "conflicts": []}, results)
            finally:
                memory.close()

    def test_unknown_features_remain_unknown(self):
        with open(DEFAULT_DICTIONARY, encoding="utf-8") as stream:
            rules = json.load(stream)["rules"]
        results = classify({"cell_count": 1}, rules)
        self.assertEqual([result["status"] for result in results], ["unknown", "unknown"])


if __name__ == "__main__":
    unittest.main()
