"""
tricorder make-it-so

Runs the full pipeline from Level 0 to explorer in a single command.
Each level is attempted in sequence. Levels that require credentials
not currently present are skipped with a clear note — the pipeline
continues with whatever was achieved.

At the end: a summary table of what was completed, what was skipped,
and what to do next.

  tricorder make-it-so [OWNER/REPO] [--lens NAME] [--out DIR] [--open]
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


DIVIDER = "─" * 60

# Level definitions in run order
LEVELS = [
    {
        "id": "L0",
        "name": "Repository Profile",
        "cmd": "discover",
        "description": "filesystem scan, archetype detection",
        "requires": [],
    },
    {
        "id": "L1",
        "name": "Evolution Timeline",
        "cmd": "discover --history",
        "description": "git history, contributors, hotspots",
        "requires": ["git"],
    },
    {
        "id": "L2",
        "name": "Review Patterns",
        "cmd": "analyze",
        "description": "PR & review data from GitHub",
        "requires": ["github_token"],
    },
    {
        "id": "L3",
        "name": "Organizational Learnings",
        "cmd": "learn",
        "description": "LLM synthesis of review record",
        "requires": ["llm_key", "L2"],
    },
    {
        "id": "L4",
        "name": "Lens Interpretation",
        "cmd": "interpret",
        "description": "domain-specific interpretation",
        "requires": ["llm_key", "L3"],
    },
    {
        "id": "L5",
        "name": "Improvement Plan",
        "cmd": "improve",
        "description": "prioritized roadmap",
        "requires": ["llm_key", "L3"],
    },
    {
        "id": "BUILD",
        "name": "Explorer",
        "cmd": "build",
        "description": "interactive HTML explorer",
        "requires": ["L3"],
    },
]


# ---------------------------------------------------------------------------
# Credential checks
# ---------------------------------------------------------------------------

def _has_github_token() -> bool:
    if os.environ.get("GITHUB_TOKEN"):
        return True
    try:
        r = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0 and bool(r.stdout.strip())
    except Exception:
        return False


def _has_llm_key() -> bool:
    return bool(
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY")
    )


def _has_git() -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


def _infer_repo() -> str | None:
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return None
        url = r.stdout.strip()
        for prefix in ("git@github.com:", "https://github.com/", "http://github.com/"):
            if url.startswith(prefix):
                slug = url[len(prefix):].removesuffix(".git")
                if "/" in slug:
                    return slug
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Pipeline runner
# ---------------------------------------------------------------------------

def _check_prereqs(level: dict, creds: dict, completed: set[str]) -> tuple[bool, str]:
    """Return (can_run, reason_if_not)."""
    for req in level["requires"]:
        if req == "github_token" and not creds["github_token"]:
            return False, "no GITHUB_TOKEN / gh auth"
        if req == "llm_key" and not creds["llm_key"]:
            return False, "no ANTHROPIC_API_KEY / GEMINI_API_KEY"
        if req == "git" and not creds["git"]:
            return False, "not a git repository"
        if req.startswith("L") and req not in completed:
            return False, f"{req} did not complete"
    return True, ""


def run(args: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="tricorder make-it-so",
        description="Run the full tricorder pipeline end-to-end.",
    )
    parser.add_argument("repo", nargs="?", default=None,
                        help="OWNER/REPO (default: inferred from git remote)")
    parser.add_argument("--lens", default=None, metavar="NAME",
                        help="Override lens for discover and interpret")
    parser.add_argument("--out", default=None, metavar="DIR",
                        help="Write Markdown report to DIR after learn")
    parser.add_argument("--open", action="store_true",
                        help="Open the explorer after build")
    parser.add_argument("--forge", action="store_true",
                        help="Run skills forge after improve (interactive)")
    parser.add_argument("--minority-report", action="store_true",
                        help="Enable Minority Report mode in learn")
    parser.add_argument("--tricorder-dir", default=None, metavar="DIR")

    parsed = parser.parse_args(args)

    repo = parsed.repo or _infer_repo()

    tri_dir = (
        Path(parsed.tricorder_dir).expanduser().resolve()
        if parsed.tricorder_dir
        else Path.cwd() / ".tricorder"
    )

    # Detect credentials once
    creds = {
        "github_token": _has_github_token(),
        "llm_key":      _has_llm_key(),
        "git":          _has_git(),
    }

    started_at = datetime.now(timezone.utc)

    print()
    print("Tricorder — Make It So")
    print(DIVIDER)
    print(f"  Repo:     {repo or '(unknown — some levels will be skipped)'}")
    print(f"  GitHub:   {'✓ authenticated' if creds['github_token'] else '✗ no token — L2 will be skipped'}")
    print(f"  LLM:      {'✓ key found' if creds['llm_key'] else '✗ no key — L3/L4/L5 will be skipped'}")
    if parsed.lens:
        print(f"  Lens:     {parsed.lens}")
    print()

    # Ask for confirmation if running non-interactively would be surprising
    if creds["llm_key"] and creds["github_token"]:
        # Full pipeline — warn about cost
        print("  This will run the full pipeline (API calls to GitHub + LLM).")
        try:
            answer = input("  Proceed? [Y/n] ").strip().lower()
            if answer and answer not in ("y", "yes"):
                print("  Aborted.")
                return 0
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        print()

    results: dict[str, str] = {}   # level id → "completed" | "skipped:<reason>" | "failed"
    completed: set[str] = set()

    for level in LEVELS:
        lid = level["id"]
        name = level["name"]

        can_run, reason = _check_prereqs(level, creds, completed)
        if not can_run:
            results[lid] = f"skipped:{reason}"
            print(f"  ○ {lid}  {name:<28}  skipped ({reason})")
            continue

        # Skip levels that need repo slug but we don't have one
        needs_repo = lid in ("L2", "L3", "L4", "L5")
        if needs_repo and not repo:
            results[lid] = "skipped:no repo slug"
            print(f"  ○ {lid}  {name:<28}  skipped (no OWNER/REPO — pass it explicitly)")
            continue

        print(f"\n{DIVIDER}")
        print(f"  {lid}  {name}  —  {level['description']}")
        print(DIVIDER)

        rc = _run_level(lid, repo, parsed, tri_dir, creds)

        if rc == 0:
            results[lid] = "completed"
            completed.add(lid)
            print(f"\n  ✓ {lid} complete")
        else:
            results[lid] = "failed"
            print(f"\n  ✗ {lid} failed (exit {rc})")
            # Hard-stop on unexpected failures (not credential issues)
            print(f"  Stopping pipeline at {lid}. Fix the error above and re-run.")
            break

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = (datetime.now(timezone.utc) - started_at).seconds
    mins, secs = divmod(elapsed, 60)

    print()
    print(DIVIDER)
    print("  Tricorder — Make It So — Summary")
    print(DIVIDER)
    print()

    status_icon = {"completed": "✓", "failed": "✗"}

    for level in LEVELS:
        lid = level["id"]
        status = results.get(lid, "not reached")
        if status == "completed":
            icon = "✓"
            note = level["name"]
        elif status.startswith("skipped:"):
            icon = "○"
            note = f"{level['name']}  ({status[8:]})"
        elif status == "failed":
            icon = "✗"
            note = f"{level['name']}  ← stopped here"
        else:
            icon = "·"
            note = f"{level['name']}  (not reached)"
        print(f"  {icon}  {lid:<6}  {note}")

    print()
    elapsed_str = f"{mins}m {secs}s" if mins else f"{secs}s"
    print(f"  Elapsed: {elapsed_str}")
    print()

    # What was produced
    produced = []
    if "L0" in completed:
        produced.append(f".tricorder/repository-profile.yml")
    if "L1" in completed:
        produced.append(f".tricorder/contributors.json  hotspots.json  timeline.json")
    if "L2" in completed:
        produced.append(f".tricorder/review-observations.json  patterns.json  expertise-map.json")
    if "L3" in completed:
        produced.append(f".tricorder/learnings.json  standards-candidates.json")
    if "L4" in completed:
        produced.append(f".tricorder/interpretations.json")
    if "L5" in completed:
        produced.append(f".tricorder/improvement-plan.md  roadmap.json")
    if "BUILD" in completed:
        install_dir = Path(__file__).parent.parent.parent
        produced.append(f"{install_dir}/explorer/data.js  →  open explorer/index.html")

    if produced:
        print("  Artifacts written:")
        for p in produced:
            print(f"    {p}")
        print()

    # What to do next
    not_run = [l for l in LEVELS if results.get(l["id"], "") != "completed"]
    if not_run and not any(results.get(l["id"], "") == "failed" for l in LEVELS):
        print("  To unlock remaining levels:")
        if not creds["github_token"]:
            print("    export GITHUB_TOKEN=ghp_...   # or: gh auth login")
        if not creds["llm_key"]:
            print("    export ANTHROPIC_API_KEY=...  # or: GEMINI_API_KEY=...")
        if not repo:
            print("    tricorder make-it-so OWNER/REPO")
        print()

    return 0 if "failed" not in results.values() else 1


# ---------------------------------------------------------------------------
# Per-level dispatch
# ---------------------------------------------------------------------------

def _run_level(
    lid: str,
    repo: str | None,
    parsed,
    tri_dir: Path,
    creds: dict,
) -> int:

    tri_args = ["--tricorder-dir", str(tri_dir)] if parsed.tricorder_dir else []

    if lid == "L0":
        from tricorder.commands.discover import run as r
        lens_args = ["--lens", parsed.lens] if parsed.lens else []
        return r(lens_args + tri_args)

    if lid == "L1":
        from tricorder.commands.discover import run as r
        lens_args = ["--lens", parsed.lens] if parsed.lens else []
        return r(["--history"] + lens_args + tri_args)

    if lid == "L2":
        from tricorder.commands.analyze import run as r
        return r([repo] + tri_args)

    if lid == "L3":
        from tricorder.commands.learn import run as r
        out_args = ["--out", parsed.out] if parsed.out else []
        mr_args = ["--minority-report"] if parsed.minority_report else []
        return r([repo] + out_args + mr_args + tri_args)

    if lid == "L4":
        from tricorder.commands.interpret import run as r
        lens_args = ["--lens", parsed.lens] if parsed.lens else []
        return r([repo] + lens_args + tri_args)

    if lid == "L5":
        from tricorder.commands.improve import run as r
        forge_args = ["--forge"] if parsed.forge else []
        return r([repo] + forge_args + tri_args)

    if lid == "BUILD":
        from tricorder.commands.build import run as r
        open_args = ["--open"] if parsed.open else []
        repo_args = [repo] if repo else []
        return r(repo_args + open_args + tri_args)

    return 1
