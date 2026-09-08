"""Phase 4 input digest: counts over the whole record, examples spread across
reviewers, every reviewer profile present, size bounded. No network, no LLM."""

from __future__ import annotations

import unittest

from tricorder.lenses import load_all
from tricorder.lenses.prompting import phase4_record_digest, system_prompt


def _pattern(category, reviewer, maturity="guidance", signal=None, citation=None):
    return {
        "signal": signal or f"{category} signal from {reviewer}",
        "category": category,
        "maturity": maturity,
        "standard_citation": citation,
        "comment_evidence": ["..."],
        "author": "someone",
        "reviewer": reviewer,
    }


class Phase4DigestTest(unittest.TestCase):
    def setUp(self):
        self.lens = load_all()["product-engineering"]
        self.pr_results = [
            {"pr_number": 101, "patterns": [
                _pattern("security", "alice", "rule", citation="OWASP Top 10"),
                _pattern("security", "bob"),
                _pattern("testing", "alice"),
            ]},
            {"pr_number": 102, "patterns": [
                _pattern("security", "carol", "judgment"),
                _pattern("correctness", "bob", "convention"),
            ]},
            {"_error": "JSON parse failed", "_pr_number": 103},
        ]
        self.reviewers = [
            {"reviewer": "alice", "pr_count": 12, "review_style": "thorough", "signal_quality": "high",
             "primary_focus_areas": [{"area": "input validation", "frequency": "always"}],
             "apparent_blind_spots": [{"area": "observability", "basis": "never mentions logs"}]},
            {"reviewer": "bob", "pr_count": 3, "review_style": "terse", "signal_quality": "low",
             "primary_focus_areas": [], "apparent_blind_spots": []},
            {"_error": "boom", "_reviewer": "dave"},
        ]

    def test_counts_cover_the_whole_record(self):
        text = phase4_record_digest(self.pr_results, self.reviewers, self.lens)
        self.assertIn("computed over all 5 patterns from 2 PRs", text)
        self.assertIn("- security: 3 | 2 PRs | 3 reviewers | judgment 1 / guidance 1 / rule 1", text)
        self.assertIn("- testing: 1 | 1 PRs | 1 reviewers | guidance 1", text)
        self.assertIn("- observability: 0 | 0 PRs | 0 reviewers | none", text)

    def test_axis_coverage_marks_absence_from_counts(self):
        text = phase4_record_digest(self.pr_results, self.reviewers, self.lens)
        self.assertIn("- security-hygiene: 3 patterns | 2 PRs | 3 reviewers — present", text)
        self.assertIn("- observability: 0 patterns | 0 PRs | 0 reviewers — ABSENT", text)
        # error-handling axis maps to both error-handling and correctness categories
        self.assertIn("- error-handling: 1 patterns | 1 PRs | 1 reviewers — present", text)

    def test_examples_spread_across_reviewers_and_prefer_maturity(self):
        text = phase4_record_digest(self.pr_results, self.reviewers, self.lens, examples_per_category=2)
        sec = [l for l in text.splitlines() if l.startswith("- [security]")]
        self.assertEqual(len(sec), 2)
        self.assertIn("PR #101 · reviewer alice · rule; cites OWASP Top 10", sec[0])
        self.assertNotIn("alice", sec[1])  # second pick is a different reviewer

    def test_every_reviewer_profile_present_and_errors_skipped(self):
        text = phase4_record_digest(self.pr_results, self.reviewers, self.lens)
        self.assertIn("Reviewer fingerprints (all 2 reviewers, one line each):", text)
        self.assertIn("- alice: 12 PRs | style thorough | signal high | focus: input validation (always) | blind spots: observability", text)
        self.assertIn("- bob: 3 PRs | style terse | signal low | focus: — | blind spots: —", text)
        self.assertNotIn("dave", text)
        self.assertIn("Most-cited standards:", text)
        self.assertIn("- 1× OWASP Top 10", text)

    def test_budget_shrinks_examples_but_never_counts(self):
        big = [{"pr_number": n, "patterns": [
            _pattern("correctness", f"rev{n % 40}", signal="x" * 150) for _ in range(8)]}
            for n in range(400)]
        full = phase4_record_digest(big, self.reviewers, self.lens)
        self.assertIn("Representative signals (up to 6 per category", full)
        budget = len(full) - 1
        small = phase4_record_digest(big, self.reviewers, self.lens, char_budget=budget)
        self.assertLessEqual(len(small), budget)
        self.assertNotIn("up to 6 per category", small)
        for text in (full, small):
            self.assertIn("computed over all 3200 patterns from 400 PRs", text)
            self.assertIn("- correctness: 3200 | 400 PRs | 40 reviewers", text)
            self.assertIn("- error-handling: 3200 patterns | 400 PRs | 40 reviewers — present", text)
        # a budget too small for even one example per category still keeps every count
        tiny = phase4_record_digest(big, self.reviewers, self.lens, char_budget=100)
        self.assertIn("Representative signals (up to 1 per category", tiny)
        self.assertIn("- correctness: 3200 | 400 PRs | 40 reviewers", tiny)

    def test_p4_system_prompt_explains_the_digest(self):
        text = system_prompt("p4", self.lens)
        self.assertIn("RECORD DIGEST", text)
        self.assertIn("Only an axis with zero patterns qualifies as a blind_spot by absence", text)


if __name__ == "__main__":
    unittest.main()
