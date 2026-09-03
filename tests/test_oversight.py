import unittest

from tricorder.lenses import load_lens
from tricorder.oversight import compute, is_human, normalize_legacy, oversight_prompt_block


def rec(n, author, reviews=(), comments=(), files=()):
    return {"number": n, "author": author,
            "reviews": [{"reviewer": r[0], "state": r[1], "body": r[2] if len(r) > 2 else ""} for r in reviews],
            "inline_comments": [{"reviewer": c[0], "path": c[1], "body": "x"} for c in comments],
            "files": list(files)}


class OversightTest(unittest.TestCase):
    def setUp(self):
        self.lens = load_lens("product-engineering-desktop")

    def test_bots_are_not_human(self):
        self.assertFalse(is_human("dependabot[bot]"))
        self.assertFalse(is_human("tulsi-builder"))
        self.assertTrue(is_human("morgmart"))
        self.assertFalse(is_human("someone", extra_bots=["someone"]))

    def test_silent_approvals_and_engagement(self):
        records = [
            rec(1, "alice", reviews=[("bob", "APPROVED", "")], files=["src-tauri/src/cmd.rs"]),        # silent
            rec(2, "alice", reviews=[("bob", "APPROVED", "")], comments=[("bob", "src/App.tsx")]),   # engaged
            rec(3, "alice", reviews=[("bob", "APPROVED", "lgtm, checked the IPC path")]),             # engaged by body
            rec(4, "alice", reviews=[("carol[bot]", "APPROVED", "")]),                                # bot only -> no engagement
            rec(5, "alice", reviews=[("alice", "APPROVED", "")]),                                      # self-approval ignored
        ]
        ov = compute(records, self.lens)
        s = ov["summary"]
        self.assertEqual(s["prs"], 5)
        self.assertEqual(s["approvals"], 3)
        self.assertEqual(s["silent_approvals"], 1)
        self.assertEqual(s["prs_without_human_engagement"], 3)   # 1, 4, 5
        bob = ov["per_reviewer"][0]
        self.assertEqual(bob["reviewer"], "bob")
        self.assertEqual(bob["silent_approvals"], 1)
        self.assertAlmostEqual(bob["silent_share"], 1 / 3, places=3)

    def test_per_tag_and_per_axis_use_changed_files(self):
        records = [
            rec(1, "a", reviews=[("bob", "APPROVED", "")], files=["src-tauri/capabilities/default.json"]),
            rec(2, "a", reviews=[("bob", "APPROVED", "")], files=["src-tauri/capabilities/session.json"]),
            rec(3, "a", reviews=[("bob", "APPROVED", "")], comments=[("bob", "src-tauri/capabilities/x.json")],
                files=["src-tauri/capabilities/x.json"]),
            rec(4, "a", reviews=[("bob", "APPROVED", "")], files=["src/App.tsx"], comments=[("bob", "src/App.tsx")]),
        ]
        ov = compute(records, self.lens)
        caps = ov["per_tag"]["desktop-capabilities"]
        self.assertEqual(caps["prs_touching"], 3)
        self.assertEqual(caps["prs_commented"], 1)
        self.assertEqual(caps["prs_touching_without_comment"], 2)
        axis = next(a for a in ov["per_axis"] if a["axis"] == "capability-minimality")
        self.assertTrue(axis["high_stakes"])
        self.assertEqual(axis["prs_touching"], 3)
        self.assertEqual(axis["prs_touching_without_comment"], 2)
        self.assertAlmostEqual(axis["silent_share"], 2 / 3, places=3)
        # sorted most-silent first
        self.assertEqual(ov["per_axis"][0]["axis"], "capability-minimality")
        block = oversight_prompt_block(ov)
        self.assertIn("capability-minimality [high-stakes]: 2 of 3 PRs", block)

    def test_without_changed_files_touch_counts_are_none(self):
        records = [rec(1, "a", reviews=[("bob", "APPROVED", "")], comments=[("bob", "src/App.tsx")])]
        ov = compute(records, self.lens)
        self.assertEqual(ov["summary"]["prs_with_changed_files"], 0)
        self.assertIsNone(ov["per_tag"]["ui-react"]["prs_touching"])
        self.assertEqual(ov["per_tag"]["ui-react"]["comments"], 1)
        self.assertIn("Changed-file lists are not in this cache", oversight_prompt_block(ov))

    def test_normalize_legacy_shape(self):
        pr = {"number": 9, "author": {"login": "a"}, "files": [{"filename": "src/x.ts"}]}
        r = normalize_legacy(pr, [{"user": {"login": "b"}, "state": "APPROVED", "body": None}],
                             [{"user": {"login": "b"}, "path": "src/x.ts", "body": "hm"}])
        self.assertEqual(r["author"], "a")
        self.assertEqual(r["files"], ["src/x.ts"])
        self.assertEqual(r["reviews"][0]["body"], "")


if __name__ == "__main__":
    unittest.main()
