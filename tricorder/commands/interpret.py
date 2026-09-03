"""
tricorder interpret — Level 4

Reads Level 3 artifacts and applies a discipline lens.
The lens provides domain-specific interpretation: which standards apply,
which authorities to cite, how to read the patterns for this repo type.

Writes: .tricorder/interpretations.json

Requires: LLM API key. Reads learnings.json from Level 3.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_TOKENS = 8192

# Lens definitions live in tricorder/lenses/data/*.yaml. See tricorder.lenses.


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _call_llm(client: Any, system: str, user: str, retries: int = 2) -> dict:
    for attempt in range(retries + 1):
        try:
            text = _strip_fences(client.generate(system, user, MAX_TOKENS))
            return json.loads(text)
        except json.JSONDecodeError as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
            else:
                return {"_error": f"JSON parse failed: {e}", "_raw": text[:500]}
        except Exception as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
            else:
                return {"_error": str(e)}
    return {"_error": "unknown"}


def _load_lens_from_profile(tri_dir: Path) -> tuple[str | None, list] | None:
    profile_path = tri_dir / "repository-profile.yml"
    if not profile_path.exists():
        return None
    try:
        import yaml
        profile = yaml.safe_load(profile_path.read_text())
        block = profile.get("lens", {}) or {}
        return block.get("selected"), list(block.get("tooling_gates_present") or [])
    except Exception:
        return None


def _infer_repo_from_remote() -> str | None:
    import subprocess
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        for prefix in ("git@github.com:", "https://github.com/", "http://github.com/"):
            if url.startswith(prefix):
                slug = url[len(prefix):].removesuffix(".git")
                if "/" in slug:
                    return slug
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Status block
# ---------------------------------------------------------------------------

def _print_status(repo: str, lens: str, out_dir: Path, result: dict) -> None:
    n_mappings = len(result.get("standard_mappings", []))
    n_blind = len(result.get("domain_blind_spots", []))
    n_wins = len(result.get("quick_wins", []))
    summary = result.get("lens_summary", "")

    print()
    print("Tricorder — Lens Interpretation")
    print()
    print("Access used")
    print(f"  ✓ LLM API  (Level 3 artifacts + {lens} lens)")
    print(f"  — No GitHub API calls")
    print()
    print("Completed")
    print(f"  ✓ Interpretations  → {out_dir}/interpretations.json")
    print()
    print("Findings")
    print(f"  Lens:              {lens}")
    print(f"  Standard mappings: {n_mappings}")
    print(f"  Domain blind spots: {n_blind}")
    print(f"  Quick wins:        {n_wins}")
    if summary:
        print()
        # Wrap the summary at ~72 chars
        words = summary.split()
        line = "  "
        for word in words:
            if len(line) + len(word) + 1 > 74:
                print(line)
                line = "  " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(line)
    print()
    print("Not yet unlocked")
    print("  ○ Improvement Plan  →  tricorder improve")
    print()
    print("Next")
    if repo:
        print(f"  tricorder improve {repo}")
    else:
        print(f"  tricorder improve")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(args: list[str]) -> int:
    import argparse
    from tricorder.llm import build_llm_provider

    parser = argparse.ArgumentParser(
        prog="tricorder interpret",
        description="Level 4: apply a discipline lens to Level 3 learnings.",
    )
    parser.add_argument("repo", nargs="?", default=None,
                        help="OWNER/REPO (default: inferred from git remote)")
    parser.add_argument("--lens", default=None, metavar="NAME",
                        help="Discipline lens to apply (see `tricorder lenses`). "
                             "Default: read from repository-profile.yml (set by discover).")
    parser.add_argument("--provider", choices=["anthropic", "gemini"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key-env", dest="api_key_env", default=None)
    parser.add_argument("--tricorder-dir", default=None, metavar="DIR",
                        help="Path to .tricorder/ directory (default: .tricorder/ in cwd)")

    parsed = parser.parse_args(args)

    from tricorder.config import load_config as _load_tri_config, repo_dir as _repo_dir, get as _cfg_get, resolve_repo as _resolve_repo
    tri_base = Path.cwd() / ".tricorder"
    tri_config = _load_tri_config(tri_base)

    repo, repo_source = _resolve_repo(tri_base, parsed.repo, _infer_repo_from_remote)
    if repo_source == "config":
        print(f"  Repo: {repo}  (from .tricorder/config.yml — pass OWNER/REPO to override)")
    elif repo_source == "git":
        print(f"  Repo: {repo}  (inferred from git remote)")

    if parsed.tricorder_dir:
        tri_dir = Path(parsed.tricorder_dir).expanduser().resolve()
    elif repo:
        tri_dir = _repo_dir(tri_base, repo)
    else:
        tri_dir = tri_base

    if not parsed.provider:
        parsed.provider = _cfg_get(tri_config, "llm", "provider")
    if not parsed.model:
        parsed.model = _cfg_get(tri_config, "llm", "model")

    # Require Level 3 artifacts
    learnings_path = tri_dir / "learnings.json"
    if not learnings_path.exists():
        print(f"learnings.json not found in {tri_dir}", file=sys.stderr)
        print("Run tricorder learn first.", file=sys.stderr)
        return 1

    # Resolve lens (YAML lens files; repo-local .tricorder/lenses/ may override)
    from tricorder.lenses import LensError, load_all
    from tricorder.lenses.prompting import interpret_context, smoke_check, system_prompt

    try:
        lenses = load_all(extra_dirs=[tri_dir / "lenses", tri_base / "lenses"])
    except LensError as e:
        print(f"Lens files failed to load: {e}", file=sys.stderr)
        return 1

    lens_name = parsed.lens
    if lens_name and lens_name not in lenses:
        print(f"Unknown lens '{lens_name}'. Valid options: {', '.join(sorted(lenses))}", file=sys.stderr)
        return 1

    profile_lens, gates = _load_lens_from_profile(tri_dir) or _load_lens_from_profile(tri_base) or (None, [])
    if not lens_name:
        lens_name = profile_lens

    if not lens_name or lens_name == "unknown":
        print("No lens selected and none detected from repository-profile.yml.", file=sys.stderr)
        print(f"Run `tricorder discover` first, or pass --lens <name>.", file=sys.stderr)
        print(f"Available lenses: {', '.join(sorted(lenses))}", file=sys.stderr)
        return 1
    if lens_name not in lenses:
        print(f"Lens '{lens_name}' named in repository-profile.yml is not installed.", file=sys.stderr)
        print(f"Available lenses: {', '.join(sorted(lenses))}", file=sys.stderr)
        return 1
    lens_obj = lenses[lens_name]
    lens = lens_name

    # Load Level 3 artifacts
    learnings = json.loads(learnings_path.read_text())
    standards_path = tri_dir / "standards-candidates.json"
    standards = json.loads(standards_path.read_text()) if standards_path.exists() else {}
    if not gates:
        gates = learnings.get("tooling_gates_present", [])

    # Build LLM client
    client = build_llm_provider(
        provider=parsed.provider,
        model=parsed.model,
        api_key_env=parsed.api_key_env,
    )

    print(f"\ntricorder interpret — {repo or '(local)'}")
    print(f"  Lens:    {lens} (v{lens_obj.version}, {lens_obj.status})")
    print(f"  LLM:     {client.config.provider} / {client.config.model}")
    print()

    # Build user prompt
    lens_ctx = interpret_context(lens_obj, gates)

    user_lines = [
        lens_ctx,
        "",
        "--- TEAM LEARNINGS ---",
        "",
        f"Pattern count: {learnings.get('pattern_count', 0)}",
        f"Reviewer profiles: {len(learnings.get('reviewer_profiles', []))}",
        f"Author profiles: {len(learnings.get('author_profiles', []))}",
        "",
        "Patterns:",
        json.dumps(learnings.get("patterns", [])[:60], indent=2)[:6000],
        "",
        "Team gaps:",
        json.dumps(learnings.get("gaps", []), indent=2)[:3000],
        "",
        "Team strengths:",
        json.dumps(learnings.get("team_strengths", []), indent=2)[:2000],
        "",
        "Institutionalization candidates:",
        json.dumps(standards.get("candidates", []), indent=2)[:2000],
        "",
        "Review culture observations:",
        learnings.get("review_culture_observations", "(none)"),
    ]

    print("Running lens interpretation …", flush=True)
    system = system_prompt("interpret", lens_obj, gates)
    result = _call_llm(client, system, "\n".join(user_lines))

    if result.get("_error"):
        print(f"LLM error: {result['_error']}", file=sys.stderr)
        raw = result.get("_raw", "")
        if raw:
            print(f"Raw output: {raw[:300]}", file=sys.stderr)
        return 1

    # Stamp metadata
    result["lens"] = lens
    result["lens_detail"] = lens_obj.summary()
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["tricorder_level"] = 4
    hits = smoke_check(lens_obj, result)
    if hits:
        result["smoke_check_hits"] = hits
        print(f"  ⚠ smoke check: off-domain terms in output: {', '.join(hits)}", file=sys.stderr)

    (tri_dir / "interpretations.json").write_text(json.dumps(result, indent=2))

    _print_status(repo or "", lens, tri_dir, result)
    return 1 if result.get("smoke_check_hits") else 0
