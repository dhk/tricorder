"""The explorer data index: upsert by slug, stable default, index.js emission."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tricorder.explorer_index import data_path, load_index, slug_for, update_index


class ExplorerIndexTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.explorer = Path(self.tmp.name) / "explorer"

    def tearDown(self):
        self.tmp.cleanup()

    def test_slug_and_data_path(self):
        self.assertEqual(slug_for("block/buzz"), "block__buzz")
        self.assertEqual(data_path(self.explorer, "block/buzz"), self.explorer / "data" / "block__buzz.js")

    def test_first_entry_becomes_default_and_files_are_written(self):
        idx = update_index(self.explorer, {"repo": "cal-itp/data-infra", "pr_count": 190, "anonymized": True})
        self.assertEqual(idx["default"], "cal-itp__data-infra")
        self.assertTrue((self.explorer / "data" / "index.json").exists())
        js = (self.explorer / "data" / "index.js").read_text()
        self.assertTrue(js.startswith("// tricorder"))
        self.assertIn("window.TRICORDER_INDEX = {", js)
        self.assertIn('"slug": "cal-itp__data-infra"', js)
        self.assertTrue(idx["entries"][0]["rendered"])

    def test_upsert_keeps_default_and_sorts(self):
        update_index(self.explorer, {"repo": "cal-itp/data-infra", "anonymized": True})
        update_index(self.explorer, {"repo": "block/buzz", "anonymized": True, "pr_count": 272})
        idx = update_index(self.explorer, {"repo": "block/buzz", "anonymized": True, "pr_count": 300})
        self.assertEqual(idx["default"], "cal-itp__data-infra")
        self.assertEqual([e["slug"] for e in idx["entries"]], ["block__buzz", "cal-itp__data-infra"])
        self.assertEqual(idx["entries"][0]["pr_count"], 300)

    def test_make_default_moves_it(self):
        update_index(self.explorer, {"repo": "cal-itp/data-infra", "anonymized": True})
        idx = update_index(self.explorer, {"repo": "block/berd", "anonymized": True}, make_default=True)
        self.assertEqual(idx["default"], "block__berd")
        self.assertEqual(load_index(self.explorer)["default"], "block__berd")

    def test_missing_index_loads_empty(self):
        idx = load_index(self.explorer)
        self.assertEqual(idx, {"default": None, "entries": []})


if __name__ == "__main__":
    unittest.main()
