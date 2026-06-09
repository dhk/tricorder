"""
tricorder improve — Level 5

Reads all prior artifacts and synthesizes them into a prioritized improvement
roadmap. Optionally spawns the skills forge to implement skill-shaped items
as actual SKILL.md files in a target repo.

Writes:
  .tricorder/improvement-plan.md
  .tricorder/roadmap.json
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_TOKENS = 8192

SYSTEM_IMPROVE = """\
You are synthesizing a complete picture of a team's code review practice into
a prioritized improvement roadmap.

You have been given everything tricorder has learned:
- Repository profile (archetype, tech stack, tooling gaps)
- Review patterns and inline comment signals
- Reviewer focus fingerprints
- Author growth profiles
- Team gap analysis
- Lens-specific interpretation (if available)

Produce a roadmap. Each item must be:
- Specific enough to act on immediately
- Tagged with effort (low/medium/high) and impact (high/medium/low)
- Assigned a category that determines how it gets implemented
- Marked if it can be implemented as a skill (a reusable agent skill / checklist
  that a reviewer or author can invoke in future work)

Categories:
  process     — change how the team works (meeting, ritual, agreement)
  checklist   — add to PR template or review checklist
  training    — documentation, pairing, or coaching
  tooling     — configure or install a tool
  ci-gate     — add an automated enforcement step to CI
  skill       — implement as an agent skill or reusable prompt

Skill-implementable means: the recommendation is a pattern or checklist that
can be captured as a SKILL.md and invoked by an AI assistant during review
or authoring.

Order by: impact descending, then effort ascending (quick wins first).

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{
  "summary": "2-3 sentences: the single most important thing this team can do, and why",
  "roadmap": [
    {
      "id": "R001",
      "title": "short imperative title",
      "description": "what to do and why, grounded in evidence from the review record",
      "category": "process | checklist | training | tooling | ci-gate | skill",
      "effort": "low | medium | high",
      "impact": "high | medium | low",
      "priority": 1,
      "skill_implementable": true,
      "skill_name": "slug-for-skill-directory (if skill_implementable)",
      "skill_trigger": "when should this skill be invoked (if skill_implementable)",
      "skill_description": "one sentence describing what the skill does (if skill_implementable)",
      "evidence": "quote or paraphrase from review record that motivates this",
      "standard_citation": "relevant standard or null"
    }
  ],
  "quick_wins": ["id1", "id2"],
  "three_month_horizon": ["id3", "id4"],
  "six_month_horizon": ["id5"]
}"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _call_llm(client: Any, system: str, user: str, max_tokens: int = MAX_TOKENS) -> dict:
    for attempt in range(3):
        try:
            text = _strip_fences(client.generate(system, user, max_tokens))
            return json.loads(text)
        except json.JSONDecodeError as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return {"_error": f"JSON parse failed: {e}", "_raw": text[:500]}
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                return {"_error": str(e)}
    return {"_error": "unknown"}


def _render_plan_md(repo: str, roadmap: dict) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    lines = []
    lines.append(f"# Improvement Plan — {repo}")
    lines.append(f"*Generated {today} by tricorder improve — Level 5*")
    lines.append("")
    summary = roadmap.get("summary", "")
    if summary:
        lines.append(f"> {summary}")
        lines.append("")
    lines.append("---")
    lines.append("")

    quick = set(roadmap.get("quick_wins", []))
    items = roadmap.get("roadmap", [])

    if quick:
        lines.append("## Quick Wins")
        lines.append("")
        for item in items:
            if item["id"] in quick:
                flag = " 🎯" if item.get("skill_implementable") else ""
                lines.append(f"### {item['id']} — {item['title']}{flag}")
                lines.append(f"*{item['category']} · effort: {item['effort']} · impact: {item['impact']}*")
                lines.append("")
                lines.append(item.get("description", ""))
                if item.get("evidence"):
                    lines.append(f"> {item['evidence']}")
                if item.get("standard_citation"):
                    lines.append(f"*Standard: {item['standard_citation']}*")
                lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Full Roadmap")
    lines.append("")
    lines.append("| ID | Title | Category | Effort | Impact | Skill |")
    lines.append("|----|-------|----------|--------|--------|-------|")
    for item in items:
        skill_mark = "✓" if item.get("skill_implementable") else ""
        lines.append(
            f"| {item['id']} | {item['title']} | {item['category']} "
            f"| {item['effort']} | {item['impact']} | {skill_mark} |"
        )
    lines.append("")

    for horizon, label in [
        ("three_month_horizon", "3-Month Horizon"),
        ("six_month_horizon", "6-Month Horizon"),
    ]:
        ids = set(roadmap.get(horizon, []))
        if not ids:
            continue
        lines.append(f"## {label}")
        lines.append("")
        for item in items:
            if item["id"] not in ids:
                continue
            flag = " 🎯" if item.get("skill_implementable") else ""
            lines.append(f"### {item['id']} — {item['title']}{flag}")
            lines.append(f"*{item['category']} · effort: {item['effort']} · impact: {item['impact']}*")
            lines.append("")
            lines.append(item.get("description", ""))
            if item.get("evidence"):
                lines.append(f"> {item['evidence']}")
            if item.get("standard_citation"):
                lines.append(f"*Standard: {item['standard_citation']}*")
            lines.append("")
        lines.append("---")
        lines.append("")

    n_skills = sum(1 for i in items if i.get("skill_implementable"))
    if n_skills:
        lines.append(f"*{n_skills} items marked 🎯 can be implemented as agent skills.*")
        lines.append(f"*Run `tricorder improve --forge` to generate them.*")
        lines.append("")

    return "\n".join(lines)


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


def _print_status(repo: str, tri_dir: Path, plan_path: Path, roadmap: dict) -> None:
    items = roadmap.get("roadmap", [])
    n_skills = sum(1 for i in items if i.get("skill_implementable"))
    quick = roadmap.get("quick_wins", [])
    summary = roadmap.get("summary", "")

    print()
    print("Tricorder — Improvement Plan")
    print()
    print("Access used")
    print(f"  ✓ LLM API  (all prior artifacts as input)")
    print(f"  — No GitHub API calls")
    print()
    print("Completed")
    print(f"  ✓ Improvement Plan  → {tri_dir}/improvement-plan.md")
    print(f"  ✓ Roadmap           → {tri_dir}/roadmap.json")
    print()
    print("Findings")
    print(f"  Roadmap items:  {len(items)}")
    print(f"  Quick wins:     {len(quick)}")
    print(f"  Skill-shaped:   {n_skills}  (can be implemented as agent skills)")
    if summary:
        print()
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

    if n_skills:
        print(f"  {n_skills} recommendations can be implemented as skills.")
        print(f"  Run `tricorder improve --forge` to generate them.")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(args: list[str]) -> int:
    import argparse
    from tricorder.llm import build_llm_provider

    parser = argparse.ArgumentParser(
        prog="tricorder improve",
        description="Level 5: synthesize all learnings into a prioritized improvement roadmap.",
    )
    parser.add_argument("repo", nargs="?", default=None,
                        help="OWNER/REPO (default: inferred from git remote)")
    parser.add_argument("--provider", choices=["anthropic", "gemini"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key-env", dest="api_key_env", default=None)
    parser.add_argument("--tricorder-dir", default=None, metavar="DIR",
                        help="Path to .tricorder/ directory (default: .tricorder/ in cwd)")
    parser.add_argument("--forge", action="store_true",
                        help="After generating the roadmap, offer to implement skill-shaped "
                             "items as SKILL.md files in a target repo.")

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

    # Require at least Level 3
    learnings_path = tri_dir / "learnings.json"
    if not learnings_path.exists():
        print(f"learnings.json not found in {tri_dir}", file=sys.stderr)
        print("Run tricorder learn first.", file=sys.stderr)
        return 1

    # Load all available artifacts
    learnings = json.loads(learnings_path.read_text())

    standards_path = tri_dir / "standards-candidates.json"
    standards = json.loads(standards_path.read_text()) if standards_path.exists() else {}

    interpretations_path = tri_dir / "interpretations.json"
    interpretations = json.loads(interpretations_path.read_text()) if interpretations_path.exists() else {}

    profile_path = tri_dir / "repository-profile.yml"
    profile_text = profile_path.read_text() if profile_path.exists() else ""

    client = build_llm_provider(
        provider=parsed.provider,
        model=parsed.model,
        api_key_env=parsed.api_key_env,
    )

    print(f"\ntricorder improve — {repo or '(local)'}")
    print(f"  LLM: {client.config.provider} / {client.config.model}")
    print()

    # Check for cached roadmap
    roadmap_path = tri_dir / "roadmap.json"
    if roadmap_path.exists():
        print("  Loading cached roadmap …")
        roadmap = json.loads(roadmap_path.read_text())
    else:
        print("  Synthesizing improvement roadmap …", flush=True)

        user_lines = []
        if profile_text:
            user_lines += ["--- REPOSITORY PROFILE ---", profile_text, ""]
        user_lines += [
            "--- LEARNINGS (Level 3) ---",
            f"Patterns: {learnings.get('pattern_count', 0)}",
            f"Reviewer profiles: {len(learnings.get('reviewer_profiles', []))}",
            f"Author profiles: {len(learnings.get('author_profiles', []))}",
            "",
            "Team gaps:",
            json.dumps(learnings.get("gaps", []), indent=2)[:3000],
            "",
            "Team strengths:",
            json.dumps(learnings.get("team_strengths", []), indent=2)[:2000],
            "",
            "Review culture:",
            learnings.get("review_culture_observations", "(none)"),
            "",
            "Standards candidates:",
            json.dumps(standards.get("candidates", []), indent=2)[:2000],
        ]

        if interpretations:
            user_lines += [
                "",
                "--- LENS INTERPRETATION (Level 4) ---",
                f"Lens: {interpretations.get('lens', 'unknown')}",
                "",
                "Standard mappings:",
                json.dumps(interpretations.get("standard_mappings", [])[:20], indent=2)[:3000],
                "",
                "Domain blind spots:",
                json.dumps(interpretations.get("domain_blind_spots", []), indent=2)[:2000],
                "",
                "Quick wins (from lens):",
                json.dumps(interpretations.get("quick_wins", []), indent=2)[:1000],
                "",
                "Lens summary:",
                interpretations.get("lens_summary", ""),
            ]

        roadmap = _call_llm(client, SYSTEM_IMPROVE, "\n".join(user_lines))
        if roadmap.get("_error"):
            print(f"LLM error: {roadmap['_error']}", file=sys.stderr)
            return 1

        roadmap["generated_at"] = datetime.now(timezone.utc).isoformat()
        roadmap["tricorder_level"] = 5
        roadmap_path.write_text(json.dumps(roadmap, indent=2))

    # Write Markdown plan
    plan_md = _render_plan_md(repo or "repo", roadmap)
    plan_path = tri_dir / "improvement-plan.md"
    plan_path.write_text(plan_md)

    _print_status(repo or "", tri_dir, plan_path, roadmap)

    # Offer skills forge
    skill_items = [i for i in roadmap.get("roadmap", []) if i.get("skill_implementable")]
    if skill_items and (parsed.forge or _prompt_forge(skill_items)):
        from tricorder.commands.skills_forge import run_forge
        run_forge(skill_items, tri_dir, repo or "")

    return 0


def _prompt_forge(skill_items: list[dict]) -> bool:
    """Ask whether to implement skill-shaped items."""
    print(f"  {len(skill_items)} roadmap items can be implemented as skills:")
    for item in skill_items[:6]:
        print(f"    [{item['id']}] {item['title']}")
    if len(skill_items) > 6:
        print(f"    … and {len(skill_items) - 6} more")
    print()
    try:
        answer = input("Implement these as skills? [Y/n] ").strip().lower()
        return answer in ("", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
