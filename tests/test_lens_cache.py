"""The synthesis cache is keyed by lens: a lens change never reuses another lens's outputs."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tricorder.lenses import load_lens
from tricorder.lenses.cache import (
    PRE_LENS_KEY, current_dir, lens_key, load_cached, migrate_flat, read_current,
    save_cached, synthesis_dir, write_current,
)


class LensKeyedCacheTest(unittest.TestCase):
    def setUp(self):
        self.desk = load_lens("product-engineering-desktop")
        self.ana = load_lens("analytics-engineering")

    def test_two_lenses_get_two_directories(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "synthesis"
            a = synthesis_dir(root, self.ana)
            b = synthesis_dir(root, self.desk)
            self.assertNotEqual(a, b)
            self.assertEqual(a.name, lens_key(self.ana))
            self.assertTrue((b / "pr").is_dir())

    def test_flat_layout_with_lens_json_is_migrated_under_its_own_lens(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "synthesis"
            (root / "pr").mkdir(parents=True)
            (root / "pr" / "1.json").write_text(json.dumps({"patterns": [{"category": "grain"}]}))
            (root / "lens.json").write_text(json.dumps({"name": "analytics-engineering", "version": 2}))
            # a desktop run must not see the dbt outputs
            desk_dir = synthesis_dir(root, self.desk)
            self.assertFalse((desk_dir / "pr" / "1.json").exists())
            moved = root / "analytics-engineering-v2" / "pr" / "1.json"
            self.assertTrue(moved.exists(), list(root.rglob("*")))
            self.assertFalse((root / "pr").exists())
            # and the analytics lens finds its own outputs where they were moved
            self.assertEqual(synthesis_dir(root, self.ana), root / "analytics-engineering-v2")

    def test_flat_layout_without_lens_json_is_parked_as_pre_lens(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "synthesis"
            (root / "pr").mkdir(parents=True)
            (root / "pr" / "7.json").write_text("{}")
            (root / "team-gaps.json").write_text("{}")
            key = migrate_flat(root)
            self.assertEqual(key, PRE_LENS_KEY)
            self.assertTrue((root / PRE_LENS_KEY / "team-gaps.json").exists())
            for lens in (self.ana, self.desk):
                self.assertFalse((synthesis_dir(root, lens) / "pr" / "7.json").exists())

    def test_stamped_file_from_another_lens_is_not_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            save_cached(p, {"patterns": []}, self.ana)
            self.assertIsNone(load_cached(p, self.desk))
            self.assertIsNotNone(load_cached(p, self.ana))
            self.assertEqual(json.loads(p.read_text())["_lens"]["name"], "analytics-engineering")

    def test_errored_and_missing_entries_are_not_loaded(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "e.json"
            p.write_text(json.dumps({"_error": "boom"}))
            self.assertIsNone(load_cached(p, self.desk))
            self.assertIsNone(load_cached(Path(d) / "missing.json", self.desk))

    def test_current_pointer_and_pre_keying_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "synthesis"
            self.assertIsNone(current_dir(root))
            (root / "pr").mkdir(parents=True)
            self.assertEqual(current_dir(root), root)           # flat layout, pre-keying
            synthesis_dir(root, self.desk)                        # migrates flat layout
            write_current(root, self.desk, {"source": "test"})
            self.assertEqual(read_current(root)["lens_key"], lens_key(self.desk))
            self.assertEqual(current_dir(root), root / lens_key(self.desk))


if __name__ == "__main__":
    unittest.main()
