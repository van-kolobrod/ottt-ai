import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "experiments" / "memory"))
from store import Memory
from geometry import audit_geometry, classify, load_dictionary


class GeometryMemoryTests(unittest.TestCase):
    def test_three_valued_rule_matching(self):
        rules = load_dictionary()["rules"]
        verdicts = {item["concept"]: item["status"] for item in classify(
            {"closed": True, "sides": 4, "equal_sides": True, "right_angles": True}, rules)}
        self.assertEqual(verdicts, {"квадрат": "matched", "прямоугольник": "matched"})
        self.assertEqual(classify({"closed": False}, rules)[0]["status"], "rejected")
        self.assertEqual(classify({"closed": True}, rules)[0]["status"], "unknown")

    def test_audit_preserves_source_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = Memory(str(Path(directory) / "memory.sqlite3"))
            try:
                observed = memory.add("observation", {
                    "features": {"closed": True, "sides": 4, "equal_sides": True, "right_angles": True}
                }, source="test")
                memory.archive(observed)
                original = memory.get(observed)["payload"]
                first = audit_geometry(memory)
                second = audit_geometry(memory)
                self.assertEqual(len(first), 2)
                self.assertEqual(second, [])
                self.assertEqual(memory.get(observed)["payload"], original)
                self.assertEqual(memory.get(observed)["tier"], "archive")
                derived = memory.get(first[0]["classification_id"])
                self.assertEqual(derived["payload"]["evidence_event_id"], observed)
                self.assertIn(observed, [row["id"] for row in memory.search("квадрат", include_archive=True)])
                memory.reactivate(observed)
                self.assertEqual(memory.get(observed)["tier"], "active")
            finally:
                memory.close()


if __name__ == "__main__":
    unittest.main()
