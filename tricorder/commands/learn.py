"""
tricorder learn — Level 3

Reads Level 2 artifacts and runs 4 LLM passes:
  1. Per-PR pattern extraction
  2. Reviewer focus fingerprints
  3. Author growth profiles
  4. Team gap analysis

Writes:
  .tricorder/learnings.json
  .tricorder/standards-candidates.json
  .tricorder/.raw/synthesis/   (intermediate cache — enables resume)

Also writes a Markdown report to --out DIR.

Requires: ANTHROPIC_API_KEY or GEMINI_API_KEY (or provider config).
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_TOKENS = 4096


# ---------------------------------------------------------------------------
# System prompts — Phase 1–4
# ---------------------------------------------------------------------------

SYSTEM_P1 = """\
You are a senior code reviewer analyzing a GitHub pull request.
Extract review signals — patterns, feedback themes, and learning moments — from the PR description and review comments.

When a comment maps to a named standard or best practice, cite it explicitly.
Maturity levels: judgment | guidance | convention | rule | deterministic

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{
  "pr_number": int,
  "patterns": [
    {
      "signal": "one-line description",
      "category": "naming | testing | documentation | style | performance | modeling | schema | business-logic | structure | security | other",
      "maturity": "judgment | guidance | convention | rule | deterministic",
      "standard_citation": "citation or null",
      "comment_evidence": ["quoted snippet"],
      "author": "login",
      "reviewer": "login"
    }
  ],
  "author_strengths": ["..."],
  "author_gaps": ["..."],
  "reviewer_focus_signals": {
    "<login>": ["signal"]
  }
}"""

SYSTEM_P2 = """\
You are analyzing a code reviewer's review history across multiple PRs.
Build a focus fingerprint — what does this reviewer consistently care about, and what do they appear to overlook?

Be specific. "Code quality" is not useful. "Missing grain declaration on fact models" is.
Cite named standards when a focus area maps to one.

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{
  "reviewer": "login",
  "pr_count": int,
  "primary_focus_areas": [
    {
      "area": "description",
      "frequency": "always | often | sometimes",
      "standard_citation": "citation or null",
      "example_comments": ["snippet"]
    }
  ],
  "apparent_blind_spots": [
    {
      "area": "description",
      "basis": "why you infer this is a blind spot"
    }
  ],
  "review_style": "blocking | advisory | conversational | terse | thorough",
  "signal_quality": "high | medium | low",
  "signal_quality_rationale": "one sentence"
}"""

SYSTEM_P3 = """\
You are analyzing a code author's pull request history.
Build a growth profile — where do they consistently do well, and where do they consistently need support?

Look for persistence: if the same gap appears in 3+ PRs, it is a growth area, not a one-off.
Recommend specific, actionable support actions.

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{
  "author": "login",
  "pr_count": int,
  "strengths": [
    {
      "area": "description",
      "persistence": "consistent | emerging",
      "standard_citation": "citation or null"
    }
  ],
  "growth_areas": [
    {
      "area": "description",
      "persistence": "consistent | occasional",
      "standard_citation": "citation or null",
      "support_recommendation": "specific, actionable recommendation"
    }
  ],
  "trajectory": "improving | stable | regressing | insufficient-data",
  "trajectory_rationale": "one sentence based on chronological review signal"
}"""

SYSTEM_P4 = """\
You are analyzing the complete PR review history of a software team.
Identify where the team is collectively strong and where it has review gaps.

Gap taxonomy:
  coverage_gap  — nobody ever reviews for this dimension
  knowledge_gap — reviewers raise it but comments are shallow or inconsistent
  blind_spot    — a named best practice that never appears in any review

If a known best practice is absent from the review record, name it.

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{
  "team_strengths": [
    {
      "area": "description",
      "evidence": "brief basis",
      "standard_citation": "citation or null"
    }
  ],
  "gaps": [
    {
      "area": "description",
      "gap_type": "coverage_gap | knowledge_gap | blind_spot",
      "standard_citation": "named standard being missed, or null",
      "recommendation": "training | tooling | checklist | ci-gate — be specific"
    }
  ],
  "institutionalization_candidates": [
    {
      "pattern": "description",
      "current_maturity": "judgment | guidance | convention | rule | deterministic",
      "next_step": "what to do to advance maturity",
      "maturity_path_target": "convention | rule | deterministic"
    }
  ],
  "review_culture_observations": "2-3 sentences on overall review culture health"
}"""


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _call_llm(client: Any, system: str, user: str, retries: int = 2, max_tokens: int = MAX_TOKENS) -> dict:
    for attempt in range(retries + 1):
        try:
            text = _strip_fences(client.generate(system, user, max_tokens))
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


# ---------------------------------------------------------------------------
# Payload builders
# ---------------------------------------------------------------------------

def _build_pr_payload(pr: dict, repo_ctx: dict) -> str:
    lines = []
    body = pr.get("body") or ""
    dq = pr.get("description_quality", {})
    low = " ⚠ LOW CONFIDENCE — description thin" if dq.get("quality") == "low" else ""

    lines.append(f"PR #{pr['number']}: {pr.get('title', '')}")
    lines.append(f"Author: {pr.get('author', 'unknown')}")
    lines.append(f"Review iterations before approval: {pr.get('review_iterations', 0)}")
    lines.append(f"Description quality: {dq.get('quality', 'unknown')}{low}")
    lines.append("")
    lines.append("Description:")
    lines.append((body[:2000] if body else "(none)"))
    lines.append("")

    enforced = repo_ctx.get("sqlfluff_rules_lines", [])
    pr_sections = repo_ctx.get("pr_template_sections", [])
    lines.append("Repo context:")
    lines.append(f"- SQLFluff rules enforced: {', '.join(enforced) if enforced else 'none detected'}")
    lines.append(f"- PR template sections: {', '.join(pr_sections) if pr_sections else 'no template'}")
    lines.append("")

    reviews = pr.get("reviews", [])
    if reviews:
        lines.append("Formal reviews:")
        for r in reviews:
            state = r.get("state", "")
            reviewer = r.get("reviewer", "unknown")
            body_r = (r.get("body") or "")[:400]
            lines.append(f"  [{state}] {reviewer}: {body_r}")
        lines.append("")

    comments = pr.get("inline_comments", [])
    if comments:
        lines.append("Inline review comments:")
        for c in comments:
            reviewer = c.get("reviewer", "unknown")
            path = c.get("path", "")
            body_c = (c.get("body") or "")[:300]
            has_reply = " [replied]" if c.get("has_reply") else ""
            lines.append(f"  {reviewer} on {path}{has_reply}: {body_c}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def _render_markdown(
    repo: str,
    pr_results: list[dict],
    reviewer_profiles: list[dict],
    author_profiles: list[dict],
    team_gaps: dict,
    visibility: str,
    pr_count: int,
) -> str:
    today = datetime.now(timezone.utc).date().isoformat()
    lines = []

    lines.append(f"# tricorder — {repo}")
    lines.append(f"*Generated {today} by tricorder learn — Level 3*")
    lines.append("")
    lines.append(f"**PRs analyzed:** {pr_count}  **Visibility:** {visibility}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 1: Patterns ready to institutionalize
    lines.append("## Patterns Ready to Institutionalize")
    lines.append("")
    all_patterns: list[dict] = []
    for r in pr_results:
        all_patterns.extend(r.get("patterns", []))

    candidates = team_gaps.get("institutionalization_candidates", [])
    mature = [p for p in all_patterns if p.get("maturity") in ("convention", "rule", "deterministic")]

    if candidates:
        lines.append("| Pattern | Current Maturity | Next Step | Target |")
        lines.append("|---------|-----------------|-----------|--------|")
        for c in candidates:
            lines.append(f"| {c.get('pattern','')} | {c.get('current_maturity','')} | {c.get('next_step','')} | {c.get('maturity_path_target','')} |")
    elif mature:
        lines.append("| Signal | Category | Maturity | Citation |")
        lines.append("|--------|----------|----------|---------|")
        for p in sorted(mature, key=lambda x: x.get("maturity", ""), reverse=True)[:15]:
            lines.append(f"| {p.get('signal','')} | {p.get('category','')} | {p.get('maturity','')} | {p.get('standard_citation') or '—'} |")
    else:
        lines.append("*No patterns at convention maturity or above detected in this window.*")
    lines.append("")

    # Section 2: Reviewer fingerprints
    lines.append("## Reviewer Focus Fingerprints")
    lines.append("")
    for rp in reviewer_profiles:
        if rp.get("_error"):
            continue
        lines.append(f"### {rp.get('reviewer', rp.get('_reviewer', 'unknown'))}")
        lines.append(f"*{rp.get('pr_count', '?')} PRs · style: {rp.get('review_style', '?')} · signal quality: {rp.get('signal_quality', '?')}*")
        lines.append("")
        for fa in rp.get("primary_focus_areas", []):
            cite = f" ({fa['standard_citation']})" if fa.get("standard_citation") else ""
            lines.append(f"- **{fa.get('area','')}** ({fa.get('frequency','')}){cite}")
        blind = rp.get("apparent_blind_spots", [])
        if blind:
            lines.append("")
            lines.append("*Apparent blind spots:*")
            for b in blind:
                lines.append(f"- {b.get('area','')} — {b.get('basis','')}")
        lines.append("")

    # Section 3: Author growth profiles
    lines.append("## Author Growth Profiles")
    lines.append("")
    if visibility == "team":
        lines.append("> *Individual author profiles omitted in team-visibility reports.*")
        lines.append("")
    elif visibility == "public":
        lines.append("> *Author profiles omitted in public-visibility reports.*")
        lines.append("")
    else:
        for ap in author_profiles:
            if ap.get("_error"):
                continue
            lines.append(f"### {ap.get('author', ap.get('_author', 'unknown'))}")
            lines.append(f"*{ap.get('pr_count', '?')} PRs · trajectory: {ap.get('trajectory', '?')}*")
            lines.append(f"*{ap.get('trajectory_rationale', '')}*")
            lines.append("")
            strengths = ap.get("strengths", [])
            if strengths:
                lines.append("**Strengths**")
                for s in strengths:
                    cite = f" ({s['standard_citation']})" if s.get("standard_citation") else ""
                    lines.append(f"- {s.get('area','')} ({s.get('persistence','')}){cite}")
                lines.append("")
            growth = ap.get("growth_areas", [])
            if growth:
                lines.append("**Growth areas**")
                for g in growth:
                    cite = f" ({g['standard_citation']})" if g.get("standard_citation") else ""
                    lines.append(f"- {g.get('area','')} ({g.get('persistence','')}){cite}")
                    if g.get("support_recommendation"):
                        lines.append(f"  → {g['support_recommendation']}")
                lines.append("")

    # Section 4: Team gap analysis
    lines.append("## Team Gap Analysis")
    lines.append("")
    strengths = team_gaps.get("team_strengths", [])
    if strengths:
        lines.append("### Where the team is strong")
        lines.append("")
        for s in strengths:
            cite = f" ({s['standard_citation']})" if s.get("standard_citation") else ""
            lines.append(f"- **{s.get('area','')}**{cite} — {s.get('evidence','')}")
        lines.append("")

    gaps = team_gaps.get("gaps", [])
    if gaps:
        lines.append("### Review gaps")
        lines.append("")
        lines.append("| Area | Gap type | Standard | Recommendation |")
        lines.append("|------|----------|----------|----------------|")
        for g in gaps:
            lines.append(f"| {g.get('area','')} | {g.get('gap_type','')} | {g.get('standard_citation') or '—'} | {g.get('recommendation','')} |")
        lines.append("")

    obs = team_gaps.get("review_culture_observations", "")
    if obs:
        lines.append("### Review culture")
        lines.append("")
        lines.append(obs)
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*What this analysis cannot see: verbal review culture (Slack/chat), reviewer availability, domain ownership, or PRs merged without review.*")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Artifact builders
# ---------------------------------------------------------------------------

def _build_learnings(pr_results: list[dict], reviewer_profiles: list[dict],
                     author_profiles: list[dict], team_gaps: dict) -> dict:
    all_patterns: list[dict] = []
    for r in pr_results:
        all_patterns.extend(r.get("patterns", []))

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tricorder_level": 3,
        "pattern_count": len(all_patterns),
        "patterns": all_patterns,
        "reviewer_profiles": [
            {k: v for k, v in rp.items() if not k.startswith("_")}
            for rp in reviewer_profiles if not rp.get("_error")
        ],
        "author_profiles": [
            {k: v for k, v in ap.items() if not k.startswith("_")}
            for ap in author_profiles if not ap.get("_error")
        ],
        "team_strengths": team_gaps.get("team_strengths", []),
        "gaps": team_gaps.get("gaps", []),
        "review_culture_observations": team_gaps.get("review_culture_observations", ""),
    }


def _build_standards_candidates(pr_results: list[dict], team_gaps: dict) -> dict:
    all_patterns: list[dict] = []
    for r in pr_results:
        all_patterns.extend(r.get("patterns", []))

    mature = [p for p in all_patterns if p.get("maturity") in ("convention", "rule", "deterministic")]
    candidates = team_gaps.get("institutionalization_candidates", [])

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tricorder_level": 3,
        "candidates": candidates,
        "mature_patterns": mature,
    }


# ---------------------------------------------------------------------------
# Minority Report
# ---------------------------------------------------------------------------

SYSTEM_MINORITY_REPORT = """\
You are comparing team gap analyses produced by multiple different AI models
on the same code review dataset.

Your job:
1. Find the CONSENSUS — findings every model agrees on. These are high-confidence.
2. Find the MINORITY REPORTS — findings only one model identified.
   These may be the most interesting: a dissenting view worth examining.
3. Find CONTRADICTIONS — where models actively disagree (e.g. one calls something
   a strength, another calls it a gap).

For each minority finding, state which model raised it and why it might be
significant even though other models missed it.

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{
  "consensus": [
    {
      "finding": "description",
      "type": "gap | strength | candidate",
      "models_agreeing": ["model-a", "model-b"],
      "confidence": "high | medium"
    }
  ],
  "minority_reports": [
    {
      "finding": "description",
      "type": "gap | strength | candidate",
      "raised_by": "model-name",
      "why_notable": "why this dissenting view is worth examining",
      "missed_by": ["model-name"]
    }
  ],
  "contradictions": [
    {
      "topic": "description of the disagreement",
      "positions": [
        {"model": "model-name", "position": "what this model says"}
      ],
      "recommendation": "how to resolve this disagreement"
    }
  ],
  "summary": "2-3 sentences: what does the multi-model view tell you that a single model would miss?"
}"""


def _run_minority_report(
    pr_results: list[dict],
    reviewer_profiles: list[dict],
    synth_dir: Path,
    tri_dir: Path,
    available_providers: list[str],
) -> dict | None:
    """Run Phase 4 with all available providers, then compare."""
    from tricorder.llm import build_llm_provider

    if len(available_providers) < 2:
        print(
            f"  Minority Report requires 2+ providers. "
            f"Found: {', '.join(available_providers) or 'none'}.",
        )
        print("  Set ANTHROPIC_API_KEY and GEMINI_API_KEY to enable.")
        return None

    all_patterns: list[dict] = []
    for r in pr_results:
        all_patterns.extend(r.get("patterns", []))

    team_prompt_lines = [
        f"PR count: {len(pr_results)}",
        "",
        "Aggregated pattern signals:",
        json.dumps(all_patterns, indent=2)[:8000],
        "",
        "Reviewer fingerprints (summary):",
        json.dumps(
            [{k: v for k, v in rp.items() if not k.startswith("_")} for rp in reviewer_profiles],
            indent=2,
        )[:4000],
    ]
    team_prompt = "\n".join(team_prompt_lines)

    print(f"\nMinority Report — running Phase 4 with {len(available_providers)} providers ...")
    per_provider: dict[str, dict] = {}

    for provider in available_providers:
        label = provider
        cache_path = synth_dir / f"team-gaps-{provider}.json"
        if cache_path.exists():
            per_provider[label] = json.loads(cache_path.read_text())
            print(f"  {label:<16}  (cached)")
            continue

        try:
            client = build_llm_provider(provider=provider)
            label = f"{provider}/{client.config.model}"
            print(f"  {label:<28} ...", end="", flush=True)
            result = _call_llm(client, SYSTEM_P4, team_prompt, max_tokens=4096)
            result["_provider"] = label
            cache_path.write_text(json.dumps(result, indent=2))
            per_provider[label] = result
            n = len(result.get("gaps", []))
            print(f"  {n} gaps")
        except Exception as e:
            print(f"  error: {e}")

    if len(per_provider) < 2:
        print("  Not enough successful runs for comparison.")
        return None

    # Comparison call — use the first available provider
    comparison_client = build_llm_provider(provider=available_providers[0])
    print(f"\n  Comparing with {comparison_client.config.provider} / {comparison_client.config.model} ...")

    comparison_lines = []
    for label, gaps in per_provider.items():
        comparison_lines.append(f"=== Model: {label} ===")
        comparison_lines.append(json.dumps(
            {k: v for k, v in gaps.items() if not k.startswith("_")},
            indent=2
        )[:3000])
        comparison_lines.append("")

    report = _call_llm(comparison_client, SYSTEM_MINORITY_REPORT, "\n".join(comparison_lines), max_tokens=4096)

    if report.get("_error"):
        print(f"  Comparison error: {report['_error']}")
        return None

    report["_providers"] = list(per_provider.keys())
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["tricorder_level"] = 3

    out_path = tri_dir / "minority-report.json"
    out_path.write_text(json.dumps(report, indent=2))

    # Print summary
    n_consensus = len(report.get("consensus", []))
    n_minority = len(report.get("minority_reports", []))
    n_contra = len(report.get("contradictions", []))
    summary = report.get("summary", "")

    print()
    print(f"  ✓ Minority Report  → {tri_dir}/minority-report.json")
    print()
    print(f"    Consensus findings:  {n_consensus}")
    print(f"    Minority reports:    {n_minority}")
    print(f"    Contradictions:      {n_contra}")
    if n_minority > 0:
        print()
        print("    Minority findings:")
        for m in report.get("minority_reports", [])[:5]:
            print(f"      [{m.get('raised_by','')}] {m.get('finding','')}")
            print(f"        → {m.get('why_notable','')}")
    if summary:
        print()
        print(f"    {summary}")
    print()

    return report


# ---------------------------------------------------------------------------
# Status block
# ---------------------------------------------------------------------------

def _print_status(repo: str, out_dir: Path, report_path: Path | None,
                  n_pr: int, n_reviewers: int, n_authors: int, n_gaps: int) -> None:
    print()
    print("Tricorder — Organizational Learnings")
    print()
    print("Access used")
    print(f"  ✓ LLM API (Level 3 artifacts as input)")
    print(f"  — No GitHub API calls")
    print(f"  — No repository contents accessed")
    print()
    print("Completed")
    print(f"  ✓ Learnings            → {out_dir}/learnings.json")
    print(f"  ✓ Standards Candidates → {out_dir}/standards-candidates.json")
    if report_path:
        print(f"  ✓ Markdown report      → {report_path}")
    print()
    print("Findings")
    print(f"  PRs processed:    {n_pr}")
    print(f"  Reviewer profiles: {n_reviewers}")
    print(f"  Author profiles:   {n_authors}")
    print(f"  Team gaps:         {n_gaps}")
    print()
    print("Not yet unlocked")
    print("  ○ Interpretation   →  tricorder interpret")
    print("  ○ Improvement Plan →  tricorder improve")
    print()
    print("Next")
    if repo:
        print(f"  tricorder interpret {repo}")
    else:
        print(f"  tricorder interpret")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

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


def _filter_records_by_reviewer_type(pr_records: list[dict], ai_only: bool) -> list[dict]:
    """Return pr_records with reviews/comments filtered to AI-only or human-only."""
    import copy
    out = []
    for pr in pr_records:
        p = copy.copy(pr)
        p["reviews"] = [r for r in pr.get("reviews", []) if r.get("is_ai", False) == ai_only]
        p["inline_comments"] = [c for c in pr.get("inline_comments", []) if c.get("is_ai", False) == ai_only]
        if p["reviews"] or p["inline_comments"]:
            out.append(p)
    return out


def _filter_records_by_focus(pr_records: list[dict], focus_area) -> list[dict]:
    """Keep only review activity that matches focus keywords."""
    import copy
    kw = [k.lower() for k in focus_area.keyword_filters]
    out = []
    for pr in pr_records:
        p = copy.copy(pr)
        p["reviews"] = [
            r for r in pr.get("reviews", [])
            if any(k in (r.get("body") or "").lower() for k in kw)
        ]
        p["inline_comments"] = [
            c for c in pr.get("inline_comments", [])
            if any(k in (c.get("body") or "").lower() for k in kw)
        ]
        if p["reviews"] or p["inline_comments"]:
            out.append(p)
    return out


SYSTEM_AI_DIFF = """\
You are comparing code review patterns from AI reviewers vs human reviewers on the same codebase.

Given two sets of extracted patterns — one from AI reviewers, one from human reviewers — identify:
1. What humans catch that AI misses (human advantage)
2. What AI catches that humans miss (AI advantage)
3. Where both overlap (shared coverage)
4. Recommendations for improving AI reviewer configuration to close the gaps

Be specific. Cite actual pattern signals, not vague categories.

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{
  "human_only": [
    {
      "signal": "description",
      "category": "category",
      "why_ai_misses": "hypothesis"
    }
  ],
  "ai_only": [
    {
      "signal": "description",
      "category": "category",
      "why_humans_miss": "hypothesis"
    }
  ],
  "shared_coverage": [
    {
      "signal": "description",
      "category": "category"
    }
  ],
  "recommendations": [
    {
      "action": "specific recommendation",
      "target": "ai-config | human-training | tooling | checklist"
    }
  ],
  "summary": "2-3 sentences on the overall AI vs human review coverage gap"
}"""


def _run_ai_diff(
    pr_records: list[dict],
    client: Any,
    repo_ctx: dict,
    synth_dir: Path,
    tri_dir: Path,
) -> dict | None:
    """Run AI diff: synthesize AI patterns, human patterns, then compare."""
    print("\nAI Diff — comparing AI reviewer vs human reviewer patterns ...")

    ai_records = _filter_records_by_reviewer_type(pr_records, ai_only=True)
    human_records = _filter_records_by_reviewer_type(pr_records, ai_only=False)

    if not ai_records:
        print("  No AI reviewer data found. Run tricorder analyze first (AI reviews are tagged is_ai=true).")
        return None

    def _extract_patterns(records: list[dict], label: str) -> list[dict]:
        cache = synth_dir / f"ai-diff-{label}.json"
        if cache.exists():
            print(f"  {label} patterns: (cached)")
            return json.loads(cache.read_text())
        all_pats = []
        for pr in records:
            payload = _build_pr_payload(pr, repo_ctx)
            result = _call_llm(client, SYSTEM_P1, payload)
            all_pats.extend(result.get("patterns", []))
        cache.write_text(json.dumps(all_pats, indent=2))
        print(f"  {label} patterns: {len(all_pats)} extracted from {len(records)} PRs")
        return all_pats

    ai_patterns = _extract_patterns(ai_records, "ai")
    human_patterns = _extract_patterns(human_records, "human")

    comparison_prompt = json.dumps({
        "ai_reviewer_patterns": ai_patterns[:6000],
        "human_reviewer_patterns": human_patterns[:6000],
    }, indent=2)

    diff_cache = synth_dir / "ai-diff-result.json"
    if diff_cache.exists():
        result = json.loads(diff_cache.read_text())
        print("  Comparison: (cached)")
    else:
        print("  Comparing ...", end="", flush=True)
        result = _call_llm(client, SYSTEM_AI_DIFF, comparison_prompt, max_tokens=4096)
        if result.get("_error"):
            print(f"\n  error: {result['_error']}")
            return None
        diff_cache.write_text(json.dumps(result, indent=2))
        print(f"  {len(result.get('human_only', []))} human-only, {len(result.get('ai_only', []))} AI-only signals")

    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["tricorder_level"] = 3
    out_path = tri_dir / "ai-diff.json"
    out_path.write_text(json.dumps(result, indent=2))

    print(f"\n  ✓ AI Diff → {out_path}")
    print(f"    Human-only signals:  {len(result.get('human_only', []))}")
    print(f"    AI-only signals:     {len(result.get('ai_only', []))}")
    print(f"    Shared coverage:     {len(result.get('shared_coverage', []))}")
    if result.get("summary"):
        print(f"\n    {result['summary']}")
    print()

    return result


def run(args: list[str]) -> int:
    import argparse
    from tricorder.llm import build_llm_provider

    parser = argparse.ArgumentParser(
        prog="tricorder learn",
        description="Level 3: extract organizational learnings via LLM. Reads Level 2 artifacts.",
    )
    parser.add_argument("repo", nargs="?", default=None,
                        help="OWNER/REPO (default: inferred from git remote)")
    parser.add_argument("--visibility", default="private",
                        choices=["private", "team", "public"],
                        help="Output visibility: private (all), team (no author profiles), public (anonymized)")
    parser.add_argument("--provider", choices=["anthropic", "gemini"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key-env", dest="api_key_env", default=None)
    parser.add_argument("--out", default=None, metavar="DIR",
                        help="Write Markdown report to DIR (default: no report)")
    parser.add_argument("--tricorder-dir", default=None, metavar="DIR",
                        help="Path to .tricorder/ directory (default: .tricorder/ in cwd)")
    parser.add_argument("--minority-report", action="store_true",
                        help="Minority Report mode: run Phase 4 with every available LLM provider "
                             "and compare results. Highlights consensus vs. dissenting findings.")
    parser.add_argument("--ai-only", action="store_true",
                        help="Synthesize only from AI reviewer comments (copilot, coderabbit, gemini, etc.). "
                             "Useful for understanding what AI reviewers catch.")
    parser.add_argument("--ai-diff", action="store_true",
                        help="Compare AI reviewer patterns vs human reviewer patterns. "
                             "Writes .tricorder/ai-diff.json surfacing gaps in AI code review coverage.")
    parser.add_argument("--focus-on", dest="focus_on", default=None, metavar="AREA",
                        help=f"Narrow synthesis to a focus area. Available: skills, security")

    parsed = parser.parse_args(args)

    # Load tricorder config
    from tricorder.config import load_config as _load_tri_config, repo_dir as _repo_dir, get as _cfg_get, resolve_repo as _resolve_repo
    tri_base = Path.cwd() / ".tricorder"
    tri_config = _load_tri_config(tri_base)

    repo, repo_source = _resolve_repo(tri_base, parsed.repo, _infer_repo_from_remote)
    if repo_source == "config":
        print(f"  Repo: {repo}  (from .tricorder/config.yml — pass OWNER/REPO to override)")
    elif repo_source == "git":
        print(f"  Repo: {repo}  (inferred from git remote)")

    # Validate --focus-on
    focus_area = None
    if parsed.focus_on:
        from tricorder.focus_areas import get as get_focus, list_names as list_focus
        focus_area = get_focus(parsed.focus_on)
        if focus_area is None:
            print(f"Unknown focus area: {parsed.focus_on!r}. Available: {', '.join(list_focus())}", file=sys.stderr)
            return 1

    # Resolve .tricorder dir — per-repo subdir unless overridden
    if parsed.tricorder_dir:
        tri_dir = Path(parsed.tricorder_dir).expanduser().resolve()
    elif repo:
        tri_dir = _repo_dir(tri_base, repo)
    else:
        tri_dir = tri_base

    # Apply config LLM defaults (CLI flags take precedence)
    if not parsed.provider:
        parsed.provider = _cfg_get(tri_config, "llm", "provider")
    if not parsed.model:
        parsed.model = _cfg_get(tri_config, "llm", "model")

    obs_path = tri_dir / "review-observations.json"
    if not obs_path.exists():
        print(f"review-observations.json not found in {tri_dir}", file=sys.stderr)
        print("Run tricorder analyze first.", file=sys.stderr)
        return 1

    # Load Level 2 artifacts
    observations = json.loads(obs_path.read_text())
    pr_records: list[dict] = observations.get("observations", [])

    repo_ctx_path = tri_dir / ".raw" / "repo-context.json"
    repo_ctx: dict = json.loads(repo_ctx_path.read_text()) if repo_ctx_path.exists() else {}

    # Intermediate synthesis cache
    synth_dir = tri_dir / ".raw" / "synthesis"
    (synth_dir / "pr").mkdir(parents=True, exist_ok=True)
    (synth_dir / "reviewers").mkdir(parents=True, exist_ok=True)
    (synth_dir / "authors").mkdir(parents=True, exist_ok=True)

    # Build LLM client
    client = build_llm_provider(
        provider=parsed.provider,
        model=parsed.model,
        api_key_env=parsed.api_key_env,
    )

    # --ai-only: keep only reviews/comments from AI reviewers
    # --ai-diff: we need both; handled after synthesis
    if parsed.ai_only:
        pr_records = _filter_records_by_reviewer_type(pr_records, ai_only=True)

    # --focus-on: filter inline comment bodies by keyword
    if focus_area:
        pr_records = _filter_records_by_focus(pr_records, focus_area)

    print(f"\ntricorder learn — {repo or '(local)'}")
    print(f"  PRs:        {len(pr_records)}")
    print(f"  Visibility: {parsed.visibility}")
    print(f"  LLM:        {client.config.provider} / {client.config.model}")
    print(f"  Key env:    {client.config.api_key_env}")
    if parsed.ai_only:
        print(f"  Mode:       AI reviewers only")
    if parsed.ai_diff:
        print(f"  Mode:       AI vs human diff")
    if focus_area:
        print(f"  Focus:      {focus_area.name}")
    print()

    # Inter-call delay — overridable via config llm.call_delay
    _default_delay = 0.3
    call_delay = float(_cfg_get(tri_config, "llm", "call_delay") or _default_delay)

    # Purge errored cache files so they get retried
    purged = 0
    for cache_dir in (synth_dir / "pr", synth_dir / "reviewers", synth_dir / "authors"):
        if cache_dir.exists():
            for f in cache_dir.glob("*.json"):
                try:
                    if json.loads(f.read_text()).get("_error"):
                        f.unlink()
                        purged += 1
                except Exception:
                    pass
    for f in (synth_dir / "team-gaps.json", synth_dir / "team-gaps-*.json"):
        pass  # team-gaps handled separately below
    if purged:
        print(f"  Purged {purged} errored cache entries — will retry.\n")

    # Build phase system prompts (optionally augmented with focus area context)
    sys_p1 = SYSTEM_P1 + ("\n\n" + focus_area.system_context if focus_area else "")
    sys_p2 = SYSTEM_P2 + ("\n\n" + focus_area.system_context if focus_area else "")
    sys_p3 = SYSTEM_P3 + ("\n\n" + focus_area.system_context if focus_area else "")
    sys_p4 = SYSTEM_P4 + ("\n\n" + focus_area.system_context if focus_area else "")

    # ── Phase 1: per-PR extraction ────────────────────────────────────────────
    prs_with_reviews = [
        pr for pr in pr_records
        if pr.get("reviews") or pr.get("inline_comments")
    ]
    print(f"Phase 1 — Per-PR pattern extraction ({len(prs_with_reviews)} PRs with review activity) ...")
    pr_results: list[dict] = []

    for i, pr in enumerate(prs_with_reviews, 1):
        num = pr["number"]
        cache_path = synth_dir / "pr" / f"{num}.json"
        if cache_path.exists():
            pr_results.append(json.loads(cache_path.read_text()))
            print(f"  [{i:03d}/{len(prs_with_reviews)}] #{num:5d}  (cached)")
            continue

        payload = _build_pr_payload(pr, repo_ctx)
        result = _call_llm(client, sys_p1, payload)
        result["_pr_number"] = num
        result["_author"] = pr.get("author", "unknown")
        cache_path.write_text(json.dumps(result, indent=2))
        pr_results.append(result)

        status = "⚠ error" if result.get("_error") else f"{len(result.get('patterns', []))} patterns"
        author = pr.get("author", "?")
        print(f"  [{i:03d}/{len(prs_with_reviews)}] #{num:5d}  {author:<20}  {status}")
        time.sleep(call_delay)

    print(f"\n  ✓ {len(pr_results)} PRs processed\n")

    # ── Phase 2: reviewer fingerprints ───────────────────────────────────────
    all_reviewers: set[str] = set()
    for pr in pr_records:
        for r in pr.get("reviews", []):
            login = r.get("reviewer", "")
            if login and login != pr.get("author"):
                all_reviewers.add(login)
        for c in pr.get("inline_comments", []):
            login = c.get("reviewer", "")
            if login and login != pr.get("author"):
                all_reviewers.add(login)

    reviewers_list = sorted(all_reviewers)
    print(f"Phase 2 — Reviewer fingerprints ({len(reviewers_list)} reviewers) ...")
    reviewer_profiles: list[dict] = []

    for reviewer in reviewers_list:
        cache_path = synth_dir / "reviewers" / f"{reviewer}.json"
        if cache_path.exists():
            reviewer_profiles.append(json.loads(cache_path.read_text()))
            print(f"  {reviewer:<22}  (cached)")
            continue

        lines = [f"Reviewer: {reviewer}", ""]
        pr_count = 0
        for pr in pr_records:
            my_reviews = [r for r in pr.get("reviews", []) if r.get("reviewer") == reviewer]
            my_comments = [c for c in pr.get("inline_comments", []) if c.get("reviewer") == reviewer]
            if not my_reviews and not my_comments:
                continue
            pr_count += 1
            lines.append(f"PR #{pr['number']}: {pr.get('title', '')}")
            for r in my_reviews:
                lines.append(f"  [{r.get('state','')}] {(r.get('body') or '')[:400]}")
            for c in my_comments:
                lines.append(f"  inline on {c.get('path','')}: {(c.get('body') or '')[:300]}")
            lines.append("")

        if pr_count == 0:
            print(f"  {reviewer:<22}  skipped (no reviews in dataset)")
            continue

        lines.insert(1, f"PRs reviewed: {pr_count}")
        result = _call_llm(client, sys_p2, "\n".join(lines))
        result["_reviewer"] = reviewer
        cache_path.write_text(json.dumps(result, indent=2))
        reviewer_profiles.append(result)

        status = "⚠ error" if result.get("_error") else result.get("signal_quality", "?")
        print(f"  {reviewer:<22}  signal_quality={status}  prs={pr_count}")
        time.sleep(call_delay)

    print(f"\n  ✓ {len(reviewer_profiles)} reviewer profiles\n")

    # ── Phase 3: author growth profiles ──────────────────────────────────────
    all_authors: set[str] = set(pr.get("author", "") for pr in pr_records if pr.get("author"))
    authors_list = sorted(all_authors)
    print(f"Phase 3 — Author growth profiles ({len(authors_list)} authors) ...")
    author_profiles: list[dict] = []

    for author in authors_list:
        cache_path = synth_dir / "authors" / f"{author}.json"
        if cache_path.exists():
            author_profiles.append(json.loads(cache_path.read_text()))
            print(f"  {author:<22}  (cached)")
            continue

        author_prs = sorted(
            [pr for pr in pr_records if pr.get("author") == author],
            key=lambda p: p.get("merged_at", ""),
        )
        lines = [f"Author: {author}", f"PRs in window: {len(author_prs)}", ""]

        pr_count = 0
        for pr in author_prs:
            reviews = pr.get("reviews", [])
            comments = pr.get("inline_comments", [])
            if not reviews and not comments:
                continue
            pr_count += 1
            lines.append(f"PR #{pr['number']} ({(pr.get('merged_at') or '')[:10]}): {pr.get('title', '')}")
            for r in reviews:
                lines.append(f"  reviewer {r.get('reviewer','')} [{r.get('state','')}]: {(r.get('body') or '')[:300]}")
            for c in comments:
                lines.append(f"  inline on {c.get('path','')}: {(c.get('body') or '')[:200]}")
            lines.append("")

        if pr_count == 0:
            print(f"  {author:<22}  skipped (no reviewed PRs)")
            continue

        result = _call_llm(client, sys_p3, "\n".join(lines))
        result["_author"] = author
        cache_path.write_text(json.dumps(result, indent=2))
        author_profiles.append(result)

        status = "⚠ error" if result.get("_error") else result.get("trajectory", "?")
        print(f"  {author:<22}  trajectory={status}  prs={pr_count}")
        time.sleep(call_delay)

    print(f"\n  ✓ {len(author_profiles)} author profiles\n")

    # ── Phase 4: team gap analysis ────────────────────────────────────────────
    print("Phase 4 — Team gap analysis ...")
    team_cache = synth_dir / "team-gaps.json"
    if team_cache.exists() and json.loads(team_cache.read_text()).get("_error"):
        team_cache.unlink()
    if team_cache.exists():
        team_gaps = json.loads(team_cache.read_text())
        print("  (cached)\n")
    else:
        all_patterns: list[dict] = []
        for r in pr_results:
            all_patterns.extend(r.get("patterns", []))

        team_lines = [
            f"Team members: {', '.join(authors_list)}",
            f"PR count: {len(pr_records)}",
            f"Reviewers: {', '.join(reviewers_list)}",
            "",
            "Aggregated pattern signals:",
            json.dumps(all_patterns, indent=2)[:8000],
            "",
            "Reviewer fingerprints (summary):",
            json.dumps(
                [{k: v for k, v in rp.items() if not k.startswith("_")} for rp in reviewer_profiles],
                indent=2
            )[:4000],
        ]

        team_gaps = _call_llm(client, sys_p4, "\n".join(team_lines), max_tokens=4096)
        team_cache.write_text(json.dumps(team_gaps, indent=2))
        if team_gaps.get("_error"):
            print(f"  ⚠ error: {team_gaps['_error']}\n")
        else:
            n = len(team_gaps.get("gaps", []))
            print(f"  ✓ {n} gaps identified\n")

    # ── Minority Report ───────────────────────────────────────────────────────
    if parsed.minority_report:
        from tricorder.llm import detect_all_available_providers
        available = detect_all_available_providers()
        _run_minority_report(pr_results, reviewer_profiles, synth_dir, tri_dir, available)

    # ── AI Diff ───────────────────────────────────────────────────────────────
    if parsed.ai_diff:
        _run_ai_diff(observations.get("observations", []), client, repo_ctx, synth_dir, tri_dir)

    # ── Write artifacts ───────────────────────────────────────────────────────
    learnings = _build_learnings(pr_results, reviewer_profiles, author_profiles, team_gaps)
    standards = _build_standards_candidates(pr_results, team_gaps)
    (tri_dir / "learnings.json").write_text(json.dumps(learnings, indent=2))
    (tri_dir / "standards-candidates.json").write_text(json.dumps(standards, indent=2))

    # ── Markdown report ───────────────────────────────────────────────────────
    report_path: Path | None = None
    _report_out = parsed.out or _cfg_get(tri_config, "output", "dir")
    if _report_out:
        out_dir = Path(_report_out).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now(timezone.utc).date().isoformat()
        slug = (repo or "repo").replace("/", "__")
        report_path = out_dir / f"{today}-{slug}.md"
        md = _render_markdown(
            repo or "repo",
            pr_results, reviewer_profiles, author_profiles, team_gaps,
            parsed.visibility, len(pr_records),
        )
        report_path.write_text(md)
        print(f"  Report written → {report_path}\n")

    _print_status(
        repo or "", tri_dir, report_path,
        len(pr_results), len(reviewer_profiles),
        len(author_profiles), len(team_gaps.get("gaps", [])),
    )
    return 0
