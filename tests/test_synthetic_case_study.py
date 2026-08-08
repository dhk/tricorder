import json
import unittest
from pathlib import Path


CASE_DIR = Path(__file__).parents[1] / "docs" / "case-studies" / "synthetic-review-audit"


class SyntheticCaseStudyTest(unittest.TestCase):
    def load(self, name):
        return json.loads((CASE_DIR / name).read_text())

    def test_fixture_is_synthetic_and_references_resolve(self):
        before = self.load("before.json")
        audit = self.load("audit.json")
        after = self.load("after.json")
        self.assertEqual({before["fixture"], audit["fixture"], after["fixture"]}, {"synthetic"})

        evidence_ids = {pr["id"] for pr in before["pull_requests"]}
        inference_ids = {item["id"] for item in audit["inferences"]}
        recommendation_ids = {item["id"] for item in audit["recommendations"]}
        for inference in audit["inferences"]:
            self.assertTrue(set(inference["evidence_refs"]) <= evidence_ids)
            self.assertTrue(inference["limitations"])
            self.assertTrue(inference["alternatives"])
        for recommendation in audit["recommendations"]:
            self.assertTrue(set(recommendation["inference_refs"]) <= inference_ids)
        for decision in after["decisions"]:
            self.assertIn(decision["recommendation_ref"], recommendation_ids)

    def test_aggregates_match_fixture(self):
        before = self.load("before.json")
        prs = before["pull_requests"]
        self.assertEqual(before["aggregates"]["pr_count"], len(prs))
        self.assertEqual(before["aggregates"]["rollback_note_present"], sum(pr["rollback_note_present"] for pr in prs))


if __name__ == "__main__":
    unittest.main()
