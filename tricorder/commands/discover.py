"""
tricorder discover — Level 0

Reads the local repository filesystem. No network. No credentials.
Detects archetype, technology fingerprint, and tooling gaps.
Proposes a discipline lens. Writes two artifacts to .tricorder/.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from tricorder.lenses import LensError, load_all
from tricorder.lenses.detect import (
    DetectionResult, composition_check, confidence_label, detect, walk_local,
)

# Archetype detection signals live in the lens files (tricorder/lenses/data/*.yaml,
# overridable from .tricorder/lenses/ and ~/.tricorder/lenses/). See
# docs/research/repo-lens/ for the evidence behind the weights and the
# global ignore list.

# File extensions to language mapping
EXT_LANGUAGE: dict[str, str] = {
    ".sql": "SQL",
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".go": "Go",
    ".rb": "Ruby",
    ".java": "Java",
    ".tf": "Terraform",
    ".rs": "Rust",
    ".sh": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".md": "Markdown",
    ".html": "HTML",
    ".css": "CSS",
    ".scala": "Scala",
    ".kt": "Kotlin",
}

# Key files that mark frameworks / tooling
KEY_FILES: list[tuple[str, str]] = [
    ("dbt_project.yml", "dbt"),
    ("dbt_project.yaml", "dbt"),
    (".sqlfluff", "SQLFluff"),
    ("profiles.yml", "dbt profiles"),
    ("package.json", "Node.js"),
    ("pyproject.toml", "Python (pyproject)"),
    ("setup.py", "Python (setup.py)"),
    ("requirements.txt", "Python (requirements)"),
    ("go.mod", "Go modules"),
    ("Cargo.toml", "Rust"),
    ("Gemfile", "Ruby"),
    ("pom.xml", "Maven"),
    ("build.gradle", "Gradle"),
    ("Dockerfile", "Docker"),
    ("docker-compose.yml", "Docker Compose"),
    ("docker-compose.yaml", "Docker Compose"),
    (".pre-commit-config.yaml", "pre-commit"),
    ("Makefile", "Make"),
    (".github/PULL_REQUEST_TEMPLATE.md", "PR template"),
    (".github/pull_request_template.md", "PR template"),
    ("PULL_REQUEST_TEMPLATE.md", "PR template"),
    ("SECURITY.md", "Security policy"),
    (".snyk", "Snyk"),
]

# Dirs to skip entirely
SKIP_DIRS = {
    ".git", ".tox", "__pycache__", "node_modules", ".venv", "venv",
    ".env", "dist", "build", ".mypy_cache", ".pytest_cache",
    ".tricorder", ".ruff_cache",
}


# ---------------------------------------------------------------------------
# Filesystem scanning
# ---------------------------------------------------------------------------

def _scan_repo(root: Path) -> dict[str, Any]:
    """Walk the repo and collect file counts, key file presence, etc."""
    ext_counts: dict[str, int] = defaultdict(int)
    total_files = 0
    key_found: set[str] = set()
    has_github_actions = False
    has_gitlab_ci = False
    has_pr_template = False

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        rel_dir = Path(dirpath).relative_to(root)

        for fname in filenames:
            total_files += 1
            rel_path = rel_dir / fname

            ext = Path(fname).suffix.lower()
            if ext:
                ext_counts[ext] += 1

            # Check key files (exact match on relative path or filename)
            for key_file, label in KEY_FILES:
                kp = Path(key_file)
                if str(rel_path) == key_file or fname == kp.name:
                    key_found.add(label)

            # CI detection
            if ".github/workflows" in str(rel_path) and ext in (".yml", ".yaml"):
                has_github_actions = True
            if fname == ".gitlab-ci.yml":
                has_gitlab_ci = True

            # PR template
            if "pull_request_template" in fname.lower():
                has_pr_template = True

    return {
        "ext_counts": dict(ext_counts),
        "total_files": total_files,
        "key_found": sorted(key_found),
        "has_github_actions": has_github_actions,
        "has_gitlab_ci": has_gitlab_ci,
        "has_pr_template": has_pr_template,
    }


def _language_summary(ext_counts: dict[str, int]) -> dict[str, int]:
    lang: dict[str, int] = defaultdict(int)
    for ext, count in ext_counts.items():
        name = EXT_LANGUAGE.get(ext)
        if name:
            lang[name] += count
    return dict(sorted(lang.items(), key=lambda x: x[1], reverse=True))


def _detect_lens(root: Path, out_dir: Path) -> tuple[DetectionResult, dict[str, int], dict]:
    """Run lens detection over the local tree. Returns (result, language_bytes, lenses)."""
    lenses = load_all(extra_dirs=[out_dir / "lenses"])
    paths, lang_bytes = walk_local(root)
    return detect(paths, lenses), lang_bytes, lenses


def _detection_block(result: DetectionResult, lenses: dict, lang_bytes: dict[str, int],
                     user_lens: str | None) -> dict[str, Any]:
    """The ``lens`` section of repository-profile.yml."""
    selected = user_lens or result.selected
    checks = []
    if selected and selected in lenses:
        c = composition_check(lenses[selected], lang_bytes)
        checks.append({"name": c.name, "passed": c.passed, "detail": c.detail})
    matched = {}
    for name, d in result.details.items():
        if d.matched or d.countered:
            matched[name] = {"score": d.score,
                             "matched": [m["pattern"] for m in d.matched],
                             "countered": [m["pattern"] for m in d.countered]}
    return {
        "proposed": result.selected or "unknown",
        "selected": selected or "unknown",
        "source": "user" if user_lens else "auto-detected",
        "state": result.state,
        "runner_up": result.runner_up,
        "margin": result.margin,
        "min_score": result.min_score,
        "min_margin": result.min_margin,
        "scores": result.scores,
        "signals": matched,
        "ignored_paths": result.ignored_paths,
        "tooling_gates_present": result.tooling_gates_present,
        "checks": checks,
        "status": lenses[selected].status if selected in lenses else None,
    }


def _tooling_gaps(scan: dict[str, Any], archetype: str) -> list[str]:
    """Identify common tooling that's absent for the detected archetype."""
    gaps = []
    key_found = set(scan["key_found"])

    if archetype == "analytics-engineering":
        if "SQLFluff" not in key_found:
            gaps.append("SQLFluff (SQL linter) not detected")
        if "pre-commit" not in key_found:
            gaps.append("pre-commit hooks not detected")
        if not scan["has_pr_template"]:
            gaps.append("No PR template found")
        if not scan["has_github_actions"] and not scan["has_gitlab_ci"]:
            gaps.append("No CI configuration detected")

    elif archetype == "platform-engineering":
        if "pre-commit" not in key_found:
            gaps.append("pre-commit hooks not detected")
        if not scan["has_pr_template"]:
            gaps.append("No PR template found")

    elif archetype == "product-engineering":
        if not scan["has_pr_template"]:
            gaps.append("No PR template found")
        if not scan["has_github_actions"] and not scan["has_gitlab_ci"]:
            gaps.append("No CI configuration detected")

    return gaps


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------

def _repo_name(root: Path) -> str:
    """Best-effort repo name from directory."""
    return root.name


def _write_fingerprint(out_dir: Path, scan: dict[str, Any], scores: dict[str, int],
                       lang_bytes: dict[str, int] | None = None) -> None:
    fingerprint = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_files": scan["total_files"],
        "language_counts": _language_summary(scan["ext_counts"]),
        "language_bytes": dict(sorted((lang_bytes or {}).items(), key=lambda x: -x[1])),
        "extension_counts": dict(sorted(
            scan["ext_counts"].items(), key=lambda x: x[1], reverse=True
        )),
        "key_tooling_detected": scan["key_found"],
        "ci": {
            "github_actions": scan["has_github_actions"],
            "gitlab_ci": scan["has_gitlab_ci"],
        },
        "pr_template": scan["has_pr_template"],
        "archetype_scores": dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)),
    }
    path = out_dir / "repository-fingerprint.json"
    path.write_text(json.dumps(fingerprint, indent=2))


def _write_profile(
    out_dir: Path,
    root: Path,
    scan: dict[str, Any],
    archetype: str,
    confidence: str,
    proposed_lens: str,
    scores: dict[str, int],
    user_lens: str | None,
    lens_block: dict[str, Any] | None = None,
) -> None:
    gaps = _tooling_gaps(scan, archetype)
    top_languages = list(_language_summary(scan["ext_counts"]).keys())[:5]

    profile: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tricorder_level": 0,
        "repository": {
            "name": _repo_name(root),
            "path": str(root),
        },
        "archetype": {
            "detected": archetype,
            "confidence": confidence,
            "scores": dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)),
        },
        "lens": lens_block or {
            "proposed": proposed_lens,
            "selected": user_lens or proposed_lens,
            "source": "user" if user_lens else "auto-detected",
        },
        "technology": {
            "primary_languages": top_languages,
            "key_tooling": scan["key_found"],
            "total_files": scan["total_files"],
        },
        "tooling_gaps": gaps,
        "next_steps": [
            "tricorder discover --history  # evolution timeline, contributor patterns",
            "tricorder analyze             # review patterns (requires GITHUB_TOKEN)",
        ],
    }

    path = out_dir / "repository-profile.yml"
    path.write_text(yaml.dump(profile, default_flow_style=False, sort_keys=False))


# ---------------------------------------------------------------------------
# Status block
# ---------------------------------------------------------------------------

def _print_status(
    root: Path,
    archetype: str,
    confidence: str,
    proposed_lens: str,
    user_lens: str | None,
    scan: dict[str, Any],
    gaps: list[str],
    out_dir: Path,
    detection: DetectionResult | None = None,
) -> None:
    lens_line = proposed_lens
    if user_lens and user_lens != proposed_lens:
        lens_line = f"{user_lens}  (override; auto-detected: {proposed_lens})"
    elif detection is not None:
        if detection.state == "mixed":
            lens_line = f"{proposed_lens}  (mixed: {detection.runner_up} trails by only {detection.margin})"
        elif detection.state == "unknown":
            best = max(detection.scores, key=detection.scores.get) if detection.scores else None
            lens_line = (f"unknown  (best candidate {best} scored {detection.scores.get(best, 0)}, "
                         f"below min_score {detection.min_score}; pass --lens NAME to override)")

    top_langs = list(_language_summary(scan["ext_counts"]).keys())[:4]
    langs_str = ", ".join(top_langs) if top_langs else "unknown"

    print()
    print("Tricorder — Repository Discovery")
    print()
    print("Access used")
    print(f"  ✓ Local filesystem: {root}")
    print( "  — No network access")
    print( "  — No credentials used")
    print()
    print("Completed")
    print(f"  ✓ Repository Profile        → {out_dir}/repository-profile.yml")
    print(f"  ✓ Technology Fingerprint    → {out_dir}/repository-fingerprint.json")
    print()
    print("Findings")
    print(f"  Archetype:  {archetype}  ({confidence} confidence)")
    print(f"  Lens:       {lens_line}")
    print(f"  Languages:  {langs_str}")
    print(f"  Files:      {scan['total_files']:,}")
    if scan["key_found"]:
        print(f"  Tooling:    {', '.join(scan['key_found'][:6])}")
    if gaps:
        print()
        print("Tooling gaps")
        for gap in gaps:
            print(f"  ○ {gap}")
    print()
    print("Not yet unlocked")
    print("  ○ Evolution Timeline    →  tricorder discover --history")
    print("  ○ Review Patterns       →  tricorder analyze")
    print("  ○ Organizational Learnings  →  tricorder learn")
    print("  ○ Interpretation        →  tricorder interpret")
    print("  ○ Improvement Plan      →  tricorder improve")
    print()
    print("Next")
    print("  tricorder discover --history")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _valid_lenses() -> set[str]:
    try:
        return set(load_all())
    except LensError as e:
        print(f"Lens files failed to load: {e}", file=sys.stderr)
        return set()


def run(args: list[str]) -> int:
    import argparse

    valid = _valid_lenses()
    parser = argparse.ArgumentParser(
        prog="tricorder discover",
        description="Level 0: scan the local repository. No credentials required.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the repository (default: current directory)",
    )
    parser.add_argument(
        "--lens",
        metavar="NAME",
        help=f"Override lens selection. Choices: {', '.join(sorted(valid))}",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Also analyze git history (Level 1)",
    )
    parser.add_argument(
        "--out",
        metavar="DIR",
        help="Write artifacts to DIR instead of <repo>/.tricorder/",
    )

    parsed = parser.parse_args(args)

    if parsed.history:
        # Level 0 scan runs first to resolve root/out_dir, then Level 1
        root = Path(parsed.path).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            print(f"Path not found or not a directory: {root}", file=sys.stderr)
            return 1
        out_dir = Path(parsed.out).expanduser().resolve() if parsed.out else root / ".tricorder"
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Cannot write to output directory {out_dir}: {e}", file=sys.stderr)
            return 1
        from tricorder.commands.history import run as run_history
        return run_history(root, out_dir)

    if parsed.lens and parsed.lens not in valid:
        print(f"Unknown lens '{parsed.lens}'. Valid options: {', '.join(sorted(valid))}", file=sys.stderr)
        return 1

    # Resolve repository root
    root = Path(parsed.path).expanduser().resolve()
    if not root.exists():
        print(f"Path not found: {root}", file=sys.stderr)
        return 1
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 1

    # Resolve output dir
    if parsed.out:
        out_dir = Path(parsed.out).expanduser().resolve()
    else:
        out_dir = root / ".tricorder"

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Cannot write to output directory {out_dir}: {e}", file=sys.stderr)
        print("Use --out DIR to specify a writable location.", file=sys.stderr)
        return 1

    # Scan
    print(f"Scanning {root} ...", end="", flush=True)
    scan = _scan_repo(root)
    print(f" {scan['total_files']:,} files found.")

    # Lens detection (signals, counter-signals, global ignore list, thresholds
    # all come from the lens files)
    try:
        result, lang_bytes, lenses = _detect_lens(root, out_dir)
    except LensError as e:
        print(f"Lens files failed to load: {e}", file=sys.stderr)
        return 1

    user_lens = parsed.lens
    proposed_lens = result.selected or "unknown"
    chosen = user_lens or result.selected
    archetype = lenses[chosen].archetype if chosen in lenses else "unknown"
    confidence = "high" if user_lens else confidence_label(result)
    scores = result.scores

    # Write artifacts
    _write_fingerprint(out_dir, scan, scores, lang_bytes)
    _write_profile(out_dir, root, scan, archetype, confidence, proposed_lens, scores, user_lens,
                   lens_block=_detection_block(result, lenses, lang_bytes, user_lens))

    # Status
    gaps = _tooling_gaps(scan, archetype)
    _print_status(root, archetype, confidence, proposed_lens, user_lens, scan, gaps, out_dir, result)

    return 0
