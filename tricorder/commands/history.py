"""
tricorder discover --history — Level 1

Reads local git history only. No network. No credentials.
Writes contributors.json, hotspots.json, repository-timeline.json.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root)] + list(args),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {args[0]} failed")
    return result.stdout


def _assert_git_repo(root: Path) -> None:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-dir"],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"Not a git repository: {root}", file=sys.stderr)
        print("Run tricorder discover --history from inside a git repository.", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------

def _parse_log(root: Path) -> list[dict[str, Any]]:
    """Return one dict per commit: hash, author, date, files changed."""
    # Format: hash|author_name|author_email|iso_date
    raw = _git(root, "log", "--format=%H|%aN|%aE|%aI", "--name-only", "--diff-filter=ACDMR")
    commits = []
    current: dict[str, Any] | None = None

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if "|" in line and len(line.split("|")) == 4:
            if current:
                commits.append(current)
            h, name, email, date_str = line.split("|", 3)
            current = {
                "hash": h,
                "author": name,
                "email": email.lower(),
                "date": date_str,
                "files": [],
            }
        elif current is not None:
            current["files"].append(line)

    if current:
        commits.append(current)

    return commits


def _build_contributors(commits: list[dict]) -> dict[str, Any]:
    """Aggregate per-author stats."""
    authors: dict[str, dict] = {}

    for c in commits:
        name = c["author"]
        email = c["email"]
        key = email or name  # deduplicate by email

        if key not in authors:
            authors[key] = {
                "name": name,
                "email": email,
                "commit_count": 0,
                "files_touched": set(),
                "first_commit": c["date"],
                "last_commit": c["date"],
            }

        a = authors[key]
        a["commit_count"] += 1
        a["files_touched"].update(c["files"])
        if c["date"] < a["first_commit"]:
            a["first_commit"] = c["date"]
        if c["date"] > a["last_commit"]:
            a["last_commit"] = c["date"]

    result = []
    for key, a in sorted(authors.items(), key=lambda x: x[1]["commit_count"], reverse=True):
        first = datetime.fromisoformat(a["first_commit"])
        last = datetime.fromisoformat(a["last_commit"])
        tenure_days = (last - first).days

        result.append({
            "name": a["name"],
            "email": a["email"],
            "commit_count": a["commit_count"],
            "files_touched_count": len(a["files_touched"]),
            "first_commit": a["first_commit"],
            "last_commit": a["last_commit"],
            "tenure_days": tenure_days,
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tricorder_level": 1,
        "total_contributors": len(result),
        "contributors": result,
    }


def _build_hotspots(commits: list[dict]) -> dict[str, Any]:
    """Find files with most changes and most contributors."""
    file_commit_count: dict[str, int] = defaultdict(int)
    file_authors: dict[str, set] = defaultdict(set)
    dir_commit_count: dict[str, int] = defaultdict(int)

    for c in commits:
        author = c["email"] or c["author"]
        for f in c["files"]:
            file_commit_count[f] += 1
            file_authors[f].add(author)
            # Track top-level directory
            parts = Path(f).parts
            if len(parts) > 1:
                dir_commit_count[parts[0]] += 1

    # Top files by commit frequency (churn)
    top_churn = sorted(file_commit_count.items(), key=lambda x: x[1], reverse=True)[:20]

    # Files with most unique contributors (bus-factor signal)
    top_contributors = sorted(
        ((f, len(authors)) for f, authors in file_authors.items()),
        key=lambda x: x[1], reverse=True
    )[:20]

    # Top directories by activity
    top_dirs = sorted(dir_commit_count.items(), key=lambda x: x[1], reverse=True)[:10]

    # Bus factor: files touched by only one contributor
    single_owner = [
        f for f, authors in file_authors.items() if len(authors) == 1
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tricorder_level": 1,
        "top_churn_files": [
            {"file": f, "commit_count": n} for f, n in top_churn
        ],
        "top_contributor_files": [
            {"file": f, "contributor_count": n} for f, n in top_contributors
        ],
        "top_active_directories": [
            {"directory": d, "commit_count": n} for d, n in top_dirs
        ],
        "single_owner_file_count": len(single_owner),
        "bus_factor_note": (
            f"{len(single_owner)} files touched by only one contributor"
            if single_owner else "No single-owner files detected"
        ),
    }


def _build_timeline(commits: list[dict]) -> dict[str, Any]:
    """Monthly activity summary and contributor join dates."""
    monthly: dict[str, dict] = {}
    author_first_seen: dict[str, str] = {}

    for c in commits:
        # Parse date
        date_str = c["date"][:10]  # YYYY-MM-DD
        month = date_str[:7]       # YYYY-MM

        if month not in monthly:
            monthly[month] = {"commits": 0, "authors": set(), "files_changed": 0}

        monthly[month]["commits"] += 1
        monthly[month]["authors"].add(c["email"] or c["author"])
        monthly[month]["files_changed"] += len(c["files"])

        # First appearance of each author
        key = c["email"] or c["author"]
        if key not in author_first_seen or c["date"] < author_first_seen[key]:
            author_first_seen[key] = c["date"]

    # Sort months
    timeline = []
    for month in sorted(monthly.keys()):
        m = monthly[month]
        timeline.append({
            "month": month,
            "commits": m["commits"],
            "active_contributors": len(m["authors"]),
            "files_changed": m["files_changed"],
        })

    # Contributor join sequence
    join_sequence = sorted(
        author_first_seen.items(), key=lambda x: x[1]
    )

    # Detect rapid growth: months where commit count jumped >2x vs prior month
    growth_events = []
    for i in range(1, len(timeline)):
        prev = timeline[i - 1]["commits"]
        curr = timeline[i]["commits"]
        if prev > 0 and curr / prev >= 2 and curr >= 10:
            growth_events.append({
                "month": timeline[i]["month"],
                "commits": curr,
                "prior_month_commits": prev,
            })

    all_dates = [c["date"] for c in commits if c["date"]]
    first_commit = min(all_dates) if all_dates else None
    last_commit = max(all_dates) if all_dates else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tricorder_level": 1,
        "first_commit": first_commit,
        "last_commit": last_commit,
        "total_commits": len(commits),
        "months_active": len(monthly),
        "monthly_activity": timeline,
        "contributor_joins": [
            {"author": k, "first_commit": v} for k, v in join_sequence
        ],
        "growth_events": growth_events,
    }


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------

def _write(out_dir: Path, filename: str, data: dict) -> Path:
    path = out_dir / filename
    path.write_text(json.dumps(data, indent=2))
    return path


# ---------------------------------------------------------------------------
# Status block
# ---------------------------------------------------------------------------

def _print_status(
    root: Path,
    out_dir: Path,
    contributors: dict,
    hotspots: dict,
    timeline: dict,
) -> None:
    total = timeline["total_commits"]
    months = timeline["months_active"]
    n_contributors = contributors["total_contributors"]
    top_churn = hotspots["top_churn_files"][:3]
    bus_note = hotspots["bus_factor_note"]
    first = (timeline.get("first_commit") or "")[:10]
    last = (timeline.get("last_commit") or "")[:10]

    print()
    print("Tricorder — Repository History")
    print()
    print("Access used")
    print(f"  ✓ Local git history: {root}")
    print( "  — No network access")
    print( "  — No credentials used")
    print()
    print("Completed")
    print(f"  ✓ Contributors      → {out_dir}/contributors.json")
    print(f"  ✓ Hotspots          → {out_dir}/hotspots.json")
    print(f"  ✓ Timeline          → {out_dir}/repository-timeline.json")
    print()
    print("Findings")
    print(f"  Commits:       {total:,}  ({first} → {last})")
    print(f"  Active months: {months}")
    print(f"  Contributors:  {n_contributors}")
    if top_churn:
        print(f"  Top churn:     {top_churn[0]['file']} ({top_churn[0]['commit_count']} commits)")
    print(f"  Bus factor:    {bus_note}")
    print()
    print("Not yet unlocked")
    print("  ○ Review Patterns         →  tricorder analyze")
    print("  ○ Organizational Learnings →  tricorder learn")
    print("  ○ Interpretation          →  tricorder interpret")
    print("  ○ Improvement Plan        →  tricorder improve")
    print()
    print("Next")
    print("  tricorder analyze  # requires GITHUB_TOKEN")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(root: Path, out_dir: Path) -> int:
    _assert_git_repo(root)

    print("Reading git history ...", end="", flush=True)
    try:
        commits = _parse_log(root)
    except RuntimeError as e:
        print(file=sys.stderr)
        print(f"git error: {e}", file=sys.stderr)
        print("Ensure you are inside a git repository with commit history.", file=sys.stderr)
        return 1

    print(f" {len(commits):,} commits found.")

    contributors = _build_contributors(commits)
    hotspots = _build_hotspots(commits)
    timeline = _build_timeline(commits)

    _write(out_dir, "contributors.json", contributors)
    _write(out_dir, "hotspots.json", hotspots)
    _write(out_dir, "repository-timeline.json", timeline)

    _print_status(root, out_dir, contributors, hotspots, timeline)
    return 0
