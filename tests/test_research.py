import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from experiments.memory.store import Memory
from experiments.memory.research import research


class ResearchTests(unittest.TestCase):
    def setUp(self):
        self.memory = Memory(":memory:")
        self.addCleanup(self.memory.close)

    def add(self, x, y, memory=None, series="default"):
        return (memory or self.memory).add("observation", {
            "series_id": series, "features": {"x": x, "y": y}}, source="numeric_test")

    def linear(self, count=8):
        return [self.add(x, 2*x) for x in range(1, count+1)]

    def payload(self, eid):
        return self.memory.get(eid)["payload"]

    def test_competing_formulas_fitted_and_supported(self):
        ids = self.linear()
        run = research(self.memory)
        self.assertEqual(len(run["hypothesis_ids"]), 3)
        first = self.payload(run["selected_hypothesis_id"])
        self.assertEqual(first["expression"], "x")
        self.assertAlmostEqual(first["parameters"]["a"], 2)
        self.assertAlmostEqual(first["parameters"]["b"], 0)
        self.assertEqual(first["state"], "proposed")
        self.assertEqual(first["training_ids"], ids[:5])
        self.assertEqual(self.payload(run["result_ids"][0])["state"], "supported")
        self.assertEqual(self.payload(run["result_ids"][0])["holdout_ids"], ids[5:])
        self.assertTrue(any(self.payload(eid)["state"] == "refuted" for eid in run["result_ids"][1:]))

    def test_holdout_values_do_not_affect_training_or_attention(self):
        self.linear()
        first = research(self.memory)
        with closing(Memory(":memory:")) as other:
            for x in range(1, 9):
                self.add(x, 2*x if x <= 5 else 10000+x, memory=other)
            second = research(other)
            for left_id, right_id in zip(first["hypothesis_ids"], second["hypothesis_ids"]):
                left = self.payload(left_id)
                right = other.get(right_id)["payload"]
                for key in ("expression", "parameters", "training_normalized_mse", "ranking_score"):
                    self.assertEqual(left[key], right[key])
            self.assertEqual(other.get(second["result_ids"][0])["payload"]["state"], "refuted")
        question = self.payload(first["question_id"])
        for candidate in question["attention_decision"]["candidates"]:
            self.assertTrue(set(candidate["evidence_ids"]) <= set(question["training_ids"]))

    def test_predictions_errors_and_threshold_are_recorded(self):
        self.linear()
        run = research(self.memory)
        result = self.payload(run["result_ids"][0])
        for item in result["predictions"]:
            self.assertEqual(item["predicted"], 2*item["x"])
            self.assertEqual(item["actual"], item["predicted"])
            self.assertEqual(item["absolute_error"], 0)
            self.assertTrue(item["passed"])
        self.assertEqual(self.payload(result["checking_event_id"])["state"], "testing")

    def test_insufficient_holdout_is_inconclusive(self):
        self.linear(4)
        run = research(self.memory)
        result = self.payload(run["result_ids"][0])
        self.assertEqual(len(result["holdout_ids"]), 1)
        self.assertEqual(result["state"], "inconclusive")

    def test_new_evidence_revises_without_refitting_or_overwriting(self):
        ids = self.linear()
        before = [self.memory.get(eid) for eid in ids]
        first = research(self.memory)
        original_hypothesis = self.payload(first["hypothesis_ids"][0])
        original_result = self.payload(first["result_ids"][0])
        fresh = self.add(9, 999)
        with patch("experiments.memory.research.Researcher.hypotheses", side_effect=AssertionError("must not refit")):
            second = research(self.memory)
        self.assertEqual(first["hypothesis_ids"], second["hypothesis_ids"])
        self.assertEqual(self.payload(second["result_ids"][0])["state"], "refuted")
        self.assertEqual(self.payload(first["hypothesis_ids"][0]), original_hypothesis)
        self.assertEqual(self.payload(first["result_ids"][0]), original_result)
        revisions = self.memory.db.execute("SELECT id FROM events WHERE kind='hypothesis_revision' AND parent_id=?",
                                           (first["hypothesis_ids"][0],)).fetchall()
        revision = self.payload(revisions[0][0])
        self.assertEqual((revision["from_state"], revision["to_state"]), ("supported", "refuted"))
        self.assertEqual(revision["new_evidence_ids"], [fresh])
        self.assertEqual(before, [self.memory.get(eid) for eid in ids])
        count = self.memory.db.execute("SELECT count(*) FROM events").fetchone()[0]
        self.assertEqual(second, research(self.memory))
        self.assertEqual(count, self.memory.db.execute("SELECT count(*) FROM events").fetchone()[0])

    def test_idempotence_and_raw_evidence_links(self):
        ids = self.linear()
        first = research(self.memory)
        count = self.memory.db.execute("SELECT count(*) FROM events").fetchone()[0]
        self.assertEqual(first, research(self.memory))
        self.assertEqual(count, self.memory.db.execute("SELECT count(*) FROM events").fetchone()[0])
        for row in self.memory.db.execute("SELECT id FROM events WHERE kind!='observation'").fetchall():
            eid = row[0]
            evidence = self.payload(eid)["evidence_ids"]
            self.assertTrue(set(evidence) <= set(ids))
            linked = {row[0] for row in self.memory.db.execute(
                "SELECT target_id FROM event_links WHERE source_id=? AND relation='evidence'", (eid,))}
            self.assertEqual(set(evidence), linked)

    def test_inconclusive_becomes_supported_with_additional_holdout(self):
        self.linear(4)
        first = research(self.memory)
        self.add(5, 10)
        second = research(self.memory)
        self.assertEqual(first["hypothesis_ids"], second["hypothesis_ids"])
        self.assertEqual(self.payload(second["result_ids"][0])["state"], "supported")

    def test_short_training_and_invalid_inputs(self):
        self.linear(2)
        first = research(self.memory)
        self.assertEqual(first["hypothesis_ids"], [])
        self.assertEqual(self.payload(first["result_ids"][0])["state"], "inconclusive")
        self.add(3, 6)
        second = research(self.memory)
        self.assertTrue(second["hypothesis_ids"])
        self.assertNotEqual(first["question_id"], second["question_id"])
        with self.assertRaises(ValueError):
            research(self.memory, independent="x", dependent="x")

    def test_attention_adapter_and_series_isolation(self):
        # Repeated x values let 4A select a suitable candidate using training only.
        for x in (1, 1, 2, 2, 3, 4):
            self.add(x, 2*x)
        self.add(10, -100, series="other")
        run = research(self.memory)
        self.assertEqual(self.payload(run["question_id"])["question_origin"], "attention_adapter")
        self.assertEqual(self.payload(run["result_ids"][0])["state"], "supported")

    def test_reopening_keeps_hypotheses_and_event_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "memory.db")
            memory = Memory(path)
            for x in range(1, 9):
                self.add(x, 2*x, memory=memory)
            first = research(memory)
            memory.close()
            memory = Memory(path)
            try:
                self.assertEqual(first, research(memory))
            finally:
                memory.close()

    def test_undefined_prediction_is_recorded_as_failed_test(self):
        for x in range(1, 9):
            self.add(x, 100/x**2)
        first = research(self.memory)
        self.assertEqual(self.payload(first["result_ids"][0])["state"], "supported")
        self.add(0, 0)
        second = research(self.memory)
        last = self.payload(second["result_ids"][0])["predictions"][-1]
        self.assertIsNone(last["predicted"])
        self.assertFalse(last["passed"])
        self.assertEqual(self.payload(second["result_ids"][0])["state"], "refuted")

    def test_constant_inputs_cannot_identify_dependency(self):
        for _ in range(6):
            self.add(1, 2)
        run = research(self.memory)
        self.assertEqual(run["hypothesis_ids"], [])
        self.assertEqual(self.payload(run["result_ids"][0])["state"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
