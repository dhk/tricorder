"""
Smoke tests for `tricorder discover` (Level 0) and `tricorder discover --history`
(Level 1) — the two commands that need no credentials and no network access.

These exercise the real CLI entry point end-to-end against a throwaway git
repo, checking that the commands exit cleanly and write the artifacts the
README promises.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    code = "import sys; from tricorder.cli import main; sys.argv = ['tricorder'] + sys.argv[1:]; main()"
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _init_sample_repo(root: Path) -> None:
    (root / "README.md").write_text("# sample\n")
    (root / "main.py").write_text("print('hello')\n")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial commit"], cwd=root, check=True)


class DiscoverSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        _init_sample_repo(self.repo)

    def test_discover_level0_writes_expected_artifacts(self) -> None:
        result = _run_cli("discover", cwd=self.repo)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        profile = self.repo / ".tricorder" / "repository-profile.yml"
        fingerprint = self.repo / ".tricorder" / "repository-fingerprint.json"
        self.assertTrue(profile.exists(), "discover should write repository-profile.yml")
        self.assertTrue(fingerprint.exists(), "discover should write repository-fingerprint.json")

        data = json.loads(fingerprint.read_text())
        self.assertIn("language_counts", data)

    def test_discover_history_writes_expected_artifacts(self) -> None:
        result = _run_cli("discover", "--history", cwd=self.repo)
        self.assertEqual(result.returncode, 0, msg=result.stderr)

        for name in ("contributors.json", "hotspots.json", "repository-timeline.json"):
            self.assertTrue(
                (self.repo / ".tricorder" / name).exists(),
                f"discover --history should write {name}",
            )

    def test_discover_rejects_unknown_lens(self) -> None:
        result = _run_cli("discover", "--lens", "not-a-real-lens", cwd=self.repo)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unknown lens", result.stderr)


if __name__ == "__main__":
    unittest.main()
