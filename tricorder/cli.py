"""
tricorder — CLI entry point

Dispatches subcommands to the scripts in the repo root.
Install once with:  pip install -e .
Then use anywhere:  tricorder harvest OWNER/REPO
"""

import subprocess
import sys
from pathlib import Path

# The scripts live in the repo root, one level above this package directory.
# Works correctly for `pip install -e .` (editable install).
SCRIPTS_DIR = Path(__file__).parent.parent

SUBCOMMANDS = {
    "ready":      "tricorder-readiness.py",
    "harvest":    "tricorder-harvest.py",
    "synthesize": "tricorder-synthesize.py",
    "probe":      "tricorder-cost-probe.py",
    "render":     "tricorder-render-explorer.py",
    "demo":       "tricorder-demo.py",
}

USAGE = """\
tricorder — PR review analysis for dbt/SQL teams

Usage:
  tricorder ready      OWNER/REPO [--days 90]
  tricorder probe      OWNER/REPO [--limit 20]
  tricorder harvest    OWNER/REPO [--since YYYY-MM-DD] [--limit N] [--force]
  tricorder synthesize OWNER/REPO [--visibility private|team|public] [--out DIR]
  tricorder render     OWNER/REPO [--out PATH] [--name-map PATH]
  tricorder demo       [--fast] [--no-pause]

Run any subcommand with --help for full flag reference.

Recommended order for a new repo:
  1. tricorder ready      OWNER/REPO          # is this repo a good candidate?
  2. tricorder probe      OWNER/REPO          # confirm cost before spending
  3. tricorder harvest    OWNER/REPO --since YYYY-MM-DD
  4. tricorder synthesize OWNER/REPO
  5. tricorder render     OWNER/REPO
"""


def _version() -> str:
    vf = SCRIPTS_DIR / "VERSION"
    return vf.read_text().strip() if vf.exists() else "unknown"


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(USAGE)
        return

    if args[0] in ("-v", "--version"):
        print(f"tricorder {_version()}")
        return

    cmd = args[0]
    if cmd not in SUBCOMMANDS:
        print(f"tricorder: unknown subcommand '{cmd}'")
        print(f"Available: {', '.join(SUBCOMMANDS)}")
        sys.exit(1)

    script = SCRIPTS_DIR / SUBCOMMANDS[cmd]
    result = subprocess.run([sys.executable, str(script)] + args[1:])
    sys.exit(result.returncode)
