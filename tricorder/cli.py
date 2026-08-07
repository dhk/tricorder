"""
tricorder — CLI entry point

v2 commands are implemented as Python modules in tricorder/commands/.
v1 commands are dispatched to legacy scripts for compatibility. The v2 command
surface is authoritative for new usage.
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent

# v1 legacy script dispatch retained for compatibility.
_LEGACY_SCRIPTS = {
    "ready":      "tricorder-readiness.py",
    "harvest":    "tricorder-harvest.py",
    "synthesize": "tricorder-synthesize.py",
    "probe":      "tricorder-cost-probe.py",
    "render":     "tricorder-render-explorer.py",
    "demo":       "tricorder-demo.py",
}

USAGE = """\
tricorder — repository learning system

Usage:
  tricorder make-it-so [OWNER/REPO]          # run the full pipeline end-to-end

  tricorder discover  [PATH] [--lens NAME] [--history]   # Level 0-1: no credentials
  tricorder analyze   OWNER/REPO                         # Level 2: GitHub read
  tricorder learn     OWNER/REPO                         # Level 3: LLM API
  tricorder interpret OWNER/REPO [--lens NAME]           # Level 4: LLM + lens
  tricorder improve   OWNER/REPO [--forge]               # Level 5: improvement plan
  tricorder build     [OWNER/REPO] [--open]              # Build explorer

  tricorder config                                       # Show config + per-repo data dirs
  tricorder config --init                                # Write starter .tricorder/config.yml

Run any subcommand with --help for full flag reference.
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
    rest = args[1:]

    # make-it-so aliases
    if cmd in ("make-it-so", "--make-it-so", "-make-it-so", "engage", "miso"):
        from tricorder.commands.make_it_so import run
        sys.exit(run(rest))

    # v2 native commands
    if cmd == "discover":
        from tricorder.commands.discover import run
        sys.exit(run(rest))

    if cmd == "config":
        from tricorder.commands.config_cmd import run
        sys.exit(run(rest))

    if cmd == "analyze":
        from tricorder.commands.analyze import run
        sys.exit(run(rest))

    if cmd == "learn":
        from tricorder.commands.learn import run
        sys.exit(run(rest))

    # v1 legacy dispatch
    if cmd in _LEGACY_SCRIPTS:
        script = SCRIPTS_DIR / _LEGACY_SCRIPTS[cmd]
        result = subprocess.run([sys.executable, str(script)] + rest)
        sys.exit(result.returncode)

    # Remaining v2 native commands
    if cmd == "interpret":
        from tricorder.commands.interpret import run
        sys.exit(run(rest))

    if cmd == "improve":
        from tricorder.commands.improve import run
        sys.exit(run(rest))

    if cmd == "build":
        from tricorder.commands.build import run
        sys.exit(run(rest))

    print(f"tricorder: unknown subcommand '{cmd}'")
    all_cmds = sorted({"config", "discover", "analyze", "learn", "interpret", "improve", "build"} | set(_LEGACY_SCRIPTS))
    print(f"Available: {', '.join(all_cmds)}")
    sys.exit(1)
