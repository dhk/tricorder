"""Shared prompt assembly for the four synthesis phases and interpretation.

The base prompts are domain-neutral. Everything domain-specific comes from the
lens: the category enum, file tags, cited authorities, axes whose absence is a
finding, tooling gates already present, per-phase context, and prohibitions.
Both the v2 ``learn``/``interpret`` commands and the legacy synthesize script
build their system prompts here so they cannot drift apart.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

from tricorder.lenses import Lens

MATURITY_LINE = "judgment | guidance | convention | rule | deterministic"

BASE_P1 = """\
You are a senior code reviewer analyzing a GitHub pull request.
Extract review signals — patterns, feedback themes, and learning moments — from the PR description and review comments.

Each inline comment is annotated with a file tag in square brackets; use it to place the comment in the right part of the codebase.
When a comment clearly maps to a named standard from the AUTHORITIES list, cite it explicitly. Otherwise leave standard_citation null.
Maturity levels: {maturity}

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{{
  "pr_number": int,
  "patterns": [
    {{
      "signal": "one-line description",
      "category": "{categories}",
      "maturity": "{maturity}",
      "standard_citation": "citation or null",
      "comment_evidence": ["quoted snippet"],
      "author": "login",
      "reviewer": "login"
    }}
  ],
  "author_strengths": ["..."],
  "author_gaps": ["..."],
  "reviewer_focus_signals": {{
    "<login>": ["signal"]
  }}
}}"""

BASE_P2 = """\
You are analyzing a code reviewer's review history across multiple PRs.
Build a focus fingerprint — what does this reviewer consistently care about, and what do they appear to overlook?

Be specific. "Code quality" is not useful. "{specific_example}" is.
Cite named standards from the AUTHORITIES list when a focus area maps to one.

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{{
  "reviewer": "login",
  "pr_count": int,
  "primary_focus_areas": [
    {{
      "area": "description",
      "category": "{categories}",
      "frequency": "always | often | sometimes",
      "standard_citation": "citation or null",
      "example_comments": ["snippet"]
    }}
  ],
  "apparent_blind_spots": [
    {{
      "area": "description",
      "basis": "why you infer this is a blind spot"
    }}
  ],
  "review_style": "blocking | advisory | conversational | terse | thorough",
  "signal_quality": "high | medium | low",
  "signal_quality_rationale": "one sentence"
}}"""

BASE_P3 = """\
You are analyzing a code author's pull request history.
Build a growth profile — where do they consistently do well, and where do they consistently need support?

Look for persistence: if the same gap appears in 3+ PRs, it is a growth area, not a one-off.
Recommend specific, actionable support actions grounded in the AUTHORITIES list.

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{{
  "author": "login",
  "pr_count": int,
  "strengths": [
    {{
      "area": "description",
      "persistence": "consistent | emerging",
      "standard_citation": "citation or null"
    }}
  ],
  "growth_areas": [
    {{
      "area": "description",
      "persistence": "consistent | occasional",
      "standard_citation": "citation or null",
      "support_recommendation": "specific, actionable recommendation"
    }}
  ],
  "trajectory": "improving | stable | regressing | insufficient-data",
  "trajectory_rationale": "one sentence based on chronological review signal"
}}"""

BASE_P4 = """\
You are analyzing the complete PR review history of a software team.
Identify where the team is collectively strong and where it has review gaps.

Gap taxonomy:
  coverage_gap  — nobody ever reviews for this dimension
  knowledge_gap — reviewers raise it but comments are shallow or inconsistent
  blind_spot    — a named best practice from this lens that never appears in any review

Report gaps only against this lens's axes. If a dimension is already enforced by a tooling gate listed below, report it as institutionalized, not as a gap.

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{{
  "team_strengths": [
    {{
      "area": "description",
      "evidence": "brief basis",
      "standard_citation": "citation or null"
    }}
  ],
  "gaps": [
    {{
      "area": "description",
      "axis": "axis id from this lens, or null",
      "gap_type": "coverage_gap | knowledge_gap | blind_spot",
      "standard_citation": "named standard being missed, or null",
      "recommendation": "training | tooling | checklist | ci-gate — be specific"
    }}
  ],
  "institutionalization_candidates": [
    {{
      "pattern": "description",
      "current_maturity": "{maturity}",
      "next_step": "what to do to advance maturity",
      "maturity_path_target": "convention | rule | deterministic"
    }}
  ],
  "review_culture_observations": "2-3 sentences on overall review culture health"
}}"""

BASE_INTERPRET = """\
You are a domain expert applying a discipline lens to a team's code review learnings.

You have been given:
1. The team's extracted patterns and gaps (from code review analysis)
2. A discipline lens with domain-specific standards and interpretation axes

Your job:
- Map each significant pattern and gap to the most relevant standard or authority for this lens
- Identify which gaps are highest priority for THIS domain (not generically)
- Identify which patterns are already well-aligned with domain best practices
- Identify which domain best practices are MISSING from the review record entirely
  (not just blind spots, but things this lens says are critical and the team never discusses)
- Produce prioritized, domain-specific recommendations

Be specific. Cite the exact standard or document from the AUTHORITIES list. "Improve testing" is not useful.

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{{
  "lens": "lens-name",
  "standard_mappings": [
    {{
      "pattern_or_gap": "description of the pattern or gap from learnings",
      "standard": "specific standard or rule name",
      "authority": "source document or framework",
      "authority_url": "url or null",
      "alignment": "well-aligned | needs-work | missing",
      "priority": "high | medium | low",
      "recommendation": "specific, actionable next step"
    }}
  ],
  "domain_blind_spots": [
    {{
      "practice": "best practice name",
      "authority": "source",
      "why_critical": "why this matters for this domain",
      "suggested_action": "how to address it"
    }}
  ],
  "quick_wins": [
    {{
      "action": "specific action",
      "effort": "low | medium",
      "impact": "high | medium",
      "rationale": "one sentence"
    }}
  ],
  "lens_summary": "2-3 sentences: how well does this team's review practice align with domain standards, and what is the single most important thing to improve?"
}}"""

PHASE_KEYS = {
    "p1": "phase1_pr_extraction",
    "p2": "phase2_reviewer_fingerprint",
    "p3": "phase3_author_growth",
    "p4": "phase4_team_gaps",
    "interpret": "interpret",
}


def category_enum(lens: Lens) -> str:
    return " | ".join(lens.category_ids)


def _specific_example(lens: Lens) -> str:
    for c in lens.categories:
        if not c.get("core") and c.get("example_comment"):
            return c["example_comment"].rstrip(".")[:90]
    return "Missing tests for the empty-input path in the retry helper"


def categories_block(lens: Lens) -> str:
    lines = ["CATEGORIES (assign exactly one per pattern):"]
    for c in lens.categories:
        core = " [core]" if c.get("core") else ""
        lines.append(f"- {c['id']}{core}: {c.get('description', '').strip()}")
    return "\n".join(lines)


def authorities_block(lens: Lens) -> str:
    lines = ["AUTHORITIES you may cite (cite only when a comment clearly invokes the practice):"]
    for a in lens.authorities:
        kind = "" if a.get("kind") == "primary" else " (secondary)"
        lines.append(f"- {a['name']}{kind} — {a['url']}")
    return "\n".join(lines)


def file_tags_block(lens: Lens) -> str:
    tags = []
    for t in lens.file_tags:
        if t["tag"] not in tags:
            tags.append(t["tag"])
    return "FILE TAGS used on inline comments: " + ", ".join(tags + ["other"])


def axes_block(lens: Lens, tooling_gates_present: Iterable[dict] = ()) -> str:
    lines = ["AXES of this lens (the review dimensions that matter in this domain):"]
    for x in lens.axes:
        flag = "  [absence from the review record is itself a blind_spot]" if x.get("phase4_absence_is_finding") else ""
        ceiling = f" (max maturity: {x['max_maturity']})" if x.get("max_maturity") else ""
        lines.append(f"- {x['id']}{ceiling}: {x['question'].strip()}{flag}")
    gates = list(tooling_gates_present)
    if gates:
        lines.append("")
        lines.append("TOOLING GATES present in this repository (already deterministic — report as institutionalized, never as gaps):")
        for g in gates:
            enf = ", ".join(g.get("enforces") or [])
            lines.append(f"- {g['tool']} ({g['config_file']}): {enf}")
    return "\n".join(lines)


def secondary_block(secondary: Lens | None) -> str:
    """Runner-up lens axes for a mixed detection. Reported only with evidence, never blended."""
    if secondary is None:
        return ""
    lines = [f"SECONDARY LENS (mixed repository; runner-up {secondary.name}). Report a gap against one of "
             "these axes only when the review record contains direct evidence for it, and label it "
             '"secondary_lens": true. Do not cite this lens\'s authorities for primary-lens findings.']
    for x in secondary.axes:
        lines.append(f"- {x['id']}: {x['question'].strip()}")
    return "\n".join(lines)


def must_not_block(lens: Lens) -> str:
    if not lens.must_not:
        return ""
    return "MUST NOT:\n" + "\n".join(f"- {m}" for m in lens.must_not)


def lens_header(lens: Lens) -> str:
    return f"LENS: {lens.name} (v{lens.version}, {lens.status})\nDOMAIN: {lens.domain}"


def lens_block(lens: Lens, phase: str, tooling_gates_present: Iterable[dict] = ()) -> str:
    key = PHASE_KEYS[phase]
    parts = [lens_header(lens), lens.prompt_context(key)]
    if phase in ("p1", "p2"):
        parts.append(file_tags_block(lens))
        parts.append(categories_block(lens))
    if phase in ("p4", "interpret"):
        parts.append(axes_block(lens, tooling_gates_present))
    parts.append(authorities_block(lens))
    parts.append(must_not_block(lens))
    return "\n\n".join(p for p in parts if p)


def system_prompt(phase: str, lens: Lens, tooling_gates_present: Iterable[dict] = (),
                  extra: str | None = None) -> str:
    """Full system prompt for a phase: neutral base + lens block (+ focus area)."""
    cats = category_enum(lens)
    if phase == "p1":
        base = BASE_P1.format(categories=cats, maturity=MATURITY_LINE)
    elif phase == "p2":
        base = BASE_P2.format(categories=cats, specific_example=_specific_example(lens))
    elif phase == "p3":
        base = BASE_P3
    elif phase == "p4":
        base = BASE_P4.format(maturity=MATURITY_LINE)
    elif phase == "interpret":
        base = BASE_INTERPRET
    else:
        raise ValueError(f"unknown phase {phase!r}")
    out = base + "\n\n" + lens_block(lens, phase, tooling_gates_present)
    if extra:
        out += "\n\n" + extra.strip()
    return out


def interpret_context(lens: Lens, tooling_gates_present: Iterable[dict] = ()) -> str:
    """The lens as rendered into the interpret user prompt."""
    return "\n\n".join([lens_header(lens), axes_block(lens, tooling_gates_present),
                        authorities_block(lens)])


def authorities_markdown(lens: Lens) -> list[str]:
    lines = []
    for a in lens.authorities:
        kind = "" if a.get("kind") == "primary" else " *(secondary)*"
        lines.append(f"- **{a['name']}**{kind}: {a['url']}")
    return lines


# ---------------------------------------------------------------------------
# Smoke checks
# ---------------------------------------------------------------------------

def smoke_check(lens: Lens, obj: Any) -> list[str]:
    """Return the smoke-check strings found in ``obj`` (JSON-serialized, word-bounded, case-insensitive)."""
    if not lens.smoke_checks:
        return []
    text = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    hits = []
    for needle in lens.smoke_checks:
        if re.search(r"(?<![\w-])" + re.escape(needle) + r"(?![\w-])", text, flags=re.IGNORECASE):
            hits.append(needle)
    return hits
