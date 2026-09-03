"""End-to-end checks of the lens wiring without an LLM: discover on a berd-shaped
tree, learn --dry-run on a fixture .tricorder/ directory, and the explorer
taxonomy derived from a lens."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_lenses import BERD_PATHS, DBT_PATHS


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    code = "import sys; from tricorder.cli import main; sys.argv = ['tricorder'] + sys.argv[1:]; main()"
    return subprocess.run([sys.executable, "-c", code, *args], cwd=cwd,
                          capture_output=True, text=True, timeout=120)


def _materialize(root: Path, paths: list[str]) -> None:
    for p in paths:
        f = root / p
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x\n")


class DiscoverLensTest(unittest.TestCase):
    def test_berd_shaped_tree_selects_desktop(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _materialize(root, BERD_PATHS)
            r = _run_cli("discover", cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("product-engineering-desktop", r.stdout)
            import yaml
            prof = yaml.safe_load((root / ".tricorder" / "repository-profile.yml").read_text())
            self.assertEqual(prof["lens"]["selected"], "product-engineering-desktop")
            self.assertEqual(prof["lens"]["state"], "selected")
            self.assertEqual(prof["archetype"]["detected"], "product-engineering")
            self.assertGreaterEqual(prof["lens"]["ignored_paths"], 4)
            gates = {g["tool"] for g in prof["lens"]["tooling_gates_present"]}
            self.assertIn("biome", gates)
            fp = json.loads((root / ".tricorder" / "repository-fingerprint.json").read_text())
            self.assertIn("language_bytes", fp)

    def test_agent_files_only_is_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _materialize(root, ["README.md", "CLAUDE.md", "AGENTS.md", ".agents/skills/x/SKILL.md", "SECURITY.md"])
            r = _run_cli("discover", cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("unknown", r.stdout)
            self.assertIn("--lens", r.stdout)

    def test_dbt_tree_selects_analytics(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            _materialize(root, DBT_PATHS)
            r = _run_cli("discover", cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("analytics-engineering", r.stdout)


class LearnDryRunTest(unittest.TestCase):
    """learn --dry-run resolves the lens from repository-profile.yml, runs the
    checks, prints the prompts, and exits before any LLM client is built."""

    def _fixture(self, root: Path, lens: str, comment_paths: list[str]) -> None:
        tri = root / ".tricorder"
        repo_dir = tri / "acme__widgets"
        (repo_dir / ".raw").mkdir(parents=True)
        (tri / "config.yml").write_text("current_repo: acme/widgets\n")
        obs = {"observations": [{
            "number": 1, "title": "t", "author": "alice", "merged_at": "2026-08-01",
            "reviews": [{"reviewer": "bob", "state": "APPROVED", "body": "lgtm"}],
            "inline_comments": [{"reviewer": "bob", "path": p, "body": "validate this input"} for p in comment_paths],
        }]}
        (repo_dir / "review-observations.json").write_text(json.dumps(obs))
        (repo_dir / ".raw" / "repo-context.json").write_text(json.dumps({"pr_template_sections": ["Summary"]}))
        import yaml
        (tri / "repository-profile.yml").write_text(yaml.safe_dump({"lens": {
            "selected": lens, "state": "selected",
            "tooling_gates_present": [{"tool": "biome", "config_file": "biome.json", "enforces": ["style"]}],
        }}))

    def test_dry_run_desktop_prompts_are_on_domain(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root, "product-engineering-desktop", ["src-tauri/src/cmd.rs", "src/App.tsx"])
            r = _run_cli("learn", "acme/widgets", "--dry-run", cwd=root)
            self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
            self.assertIn("LENS: product-engineering-desktop", r.stdout)
            self.assertIn("review_path_check", r.stdout)
            self.assertIn("TOOLING GATES present", r.stdout)
            self.assertIn("biome", r.stdout)
            # dbt authorities must not be citable; they may appear only inside MUST NOT
            self.assertNotIn("Kimball dimensional", r.stdout)
            self.assertNotIn("docs.getdbt.com", r.stdout)
            self.assertIn("MUST NOT:\n- Cite dbt, SQLFluff, Kimball", r.stdout)
            self.assertIn("Dry run", r.stdout)

    def test_wrong_lens_fails_verification_unless_forced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            # analytics lens over comments that are all on Rust and TSX files
            self._fixture(root, "analytics-engineering", ["src-tauri/src/cmd.rs", "src/App.tsx", "src/x.tsx"])
            r = _run_cli("learn", "acme/widgets", "--dry-run", cwd=root)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("verification failed", r.stderr)
            r2 = _run_cli("learn", "acme/widgets", "--dry-run", "--force", cwd=root)
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

    def test_explicit_lens_overrides_profile(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._fixture(root, "analytics-engineering", ["src-tauri/src/cmd.rs", "src/App.tsx"])
            r = _run_cli("learn", "acme/widgets", "--dry-run", "--lens", "product-engineering-desktop", cwd=root)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("--lens", r.stdout)
            self.assertIn("LENS: product-engineering-desktop", r.stdout)


class ExplorerTaxonomyTest(unittest.TestCase):
    def test_taxonomy_from_desktop_lens(self):
        from tricorder.commands.build import taxonomy_from_lens, _taxonomy_for
        from tricorder.lenses import load_lens
        tax = taxonomy_from_lens(load_lens("product-engineering-desktop"))
        self.assertEqual(len(tax["categories"]), 22)
        self.assertEqual(len(tax["radar"]), 9)
        self.assertNotIn("other", tax["radar"])
        self.assertEqual(tax["groups"]["ipc-boundary"], "data")
        self.assertEqual(tax["groups"]["security"], "tool")
        self.assertIn("ipc boundary", tax["keywords"]["ipc-boundary"])
        self.assertEqual(tax["lens"]["name"], "product-engineering-desktop")

    def test_legacy_learnings_keep_dbt_set(self):
        from tricorder.commands.build import _taxonomy_for
        tax = _taxonomy_for({"patterns": []})
        self.assertIn("grain", tax["categories"])
        self.assertIsNone(tax["lens"])


if __name__ == "__main__":
    unittest.main()
