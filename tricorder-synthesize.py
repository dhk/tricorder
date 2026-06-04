#!/usr/bin/env python3
"""
tricorder — synthesize
----------------------
Loads harvest cache for a repo and runs 4 Claude API calls:
  1. Per-PR pattern extraction (one call per PR)
  2. Reviewer focus fingerprints (one call per reviewer)
  3. Author growth profiles (one call per author)
  4. Team gap analysis (one aggregate call)

Outputs a Markdown report to adventures-in-ai/tricorder/.

Usage:
  python tricorder-synthesize.py OWNER/REPO [--visibility private|team|public]

Auth:
  Reads ANTHROPIC_API_KEY from macOS keychain:
    security find-generic-password -a "$USER" -s "anthropic_api_key" -w
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import anthropic
except ImportError:
    sys.exit("Missing dependency: pip install anthropic")


# ── config ────────────────────────────────────────────────────────────────────
CACHE_BASE       = Path.home() / ".learn-from-work" / "cache"
_DEFAULT_OUT     = Path.home() / "Documents" / "dev" / "adventures-in-ai" / "tricorder"
OUTPUT_BASE      = _DEFAULT_OUT if _DEFAULT_OUT.exists() else Path("output")
MODEL            = "claude-sonnet-4-6"
MAX_TOKENS       = 2048


# ── auth ──────────────────────────────────────────────────────────────────────
def get_api_key() -> str:
    result = subprocess.run(
        ["security", "find-generic-password", "-a", os.environ["USER"],
         "-s", "anthropic_api_key", "-w"],
        capture_output=True, text=True
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    sys.exit("❌  Anthropic API key not found in keychain or ANTHROPIC_API_KEY env var.")


# ── file type detection ───────────────────────────────────────────────────────
def tag_file(path: str) -> str:
    if not path:
        return "other"
    if "models/" in path and path.endswith(".sql"):
        return "dbt-model"
    if "macros/" in path and path.endswith(".sql"):
        return "dbt-macro"
    if "tests/" in path:
        return "dbt-test"
    if path.endswith(".yml") and "models/" in path:
        return "dbt-schema"
    if path.endswith(".py"):
        return "python"
    if path == "dbt_project.yml":
        return "dbt-config"
    if path.endswith(".md"):
        return "documentation"
    return "other"


# ── payload assembly ──────────────────────────────────────────────────────────
def build_pr_payload(pr: dict, reviews: list, comments: list, repo_ctx: dict) -> str:
    lines = []
    body = pr.get("body") or ""
    dq   = pr.get("description_quality", {})
    conf = " ⚠ LOW CONFIDENCE — description thin, treat pattern extractions as tentative" if dq.get("low_confidence") else ""

    lines.append(f"PR #{pr['number']}: {pr['title']}")
    lines.append(f"Author: {pr['author']['login']} (cache tenure: {pr.get('_tenure_days', '?')} days)")
    lines.append(f"Review iterations before approval: {pr.get('review_iterations', 0)}")
    lines.append(f"Description quality: {dq.get('quality', 'unknown')}{conf}")
    lines.append("")
    lines.append("Description:")
    lines.append((body[:2000] if body else "(none)"))
    lines.append("")

    enforced = repo_ctx.get("sqlfluff_rules_lines", [])
    lines.append(f"Repo context:")
    lines.append(f"- SQLFluff rules enforced: {', '.join(enforced) if enforced else 'none detected'}")
    pr_sections = repo_ctx.get("pr_template_sections", [])
    lines.append(f"- PR template sections: {', '.join(pr_sections) if pr_sections else 'no template'}")
    lines.append("")

    lines.append("Reviews:")
    for rev in reviews:
        reviewer = rev.get("user", {}).get("login", "unknown")
        state    = rev.get("state", "")
        rbody    = (rev.get("body") or "").strip()
        lines.append(f"  [{state}] {reviewer}: {rbody[:500]}")

    lines.append("")
    lines.append("Inline comments:")
    for c in comments[:50]:
        user  = c.get("user", {}).get("login", "unknown")
        path  = c.get("path", "")
        ftype = tag_file(path)
        cbody = (c.get("body") or "").strip()
        replied = " [has_reply]" if c.get("has_reply") else ""
        lines.append(f"  {user} on {path} [{ftype}]{replied}: {cbody[:300]}")

    return "\n".join(lines)


# ── claude calls ──────────────────────────────────────────────────────────────
SYSTEM_P1 = """You are a senior analytics engineering reviewer analyzing a GitHub pull request.
Your job is to extract review signals — patterns, feedback themes, and learning moments — from the PR description and review comments.

Context: This is a dbt/SQL analytics repository. Relevant standards include:
- dbt Labs style guide (https://docs.getdbt.com/best-practices/how-we-style/0-how-we-style-our-dbt-projects)
- SQLFluff rule catalog
- Kimball dimensional modeling principles
- dbt-project-evaluator checks
- The Checklist Manifesto (Gawande) — when a pattern is checklist-worthy, say so

When a comment maps to a named standard, cite it explicitly.

Maturity levels: judgment | guidance | convention | rule | deterministic

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{
  "pr_number": int,
  "patterns": [
    {
      "signal": "one-line description of the pattern",
      "category": "grain | naming | testing | documentation | style | performance | modeling | schema | business-logic | incremental | exposure-contract | source-freshness | macro-complexity | test-pyramid | other",
      "maturity": "judgment | guidance | convention | rule | deterministic",
      "standard_citation": "citation or null",
      "comment_evidence": ["quoted snippet 1"],
      "author": "login",
      "reviewer": "login"
    }
  ],
  "author_strengths": ["..."],
  "author_gaps": ["..."],
  "reviewer_focus_signals": {
    "<reviewer_login>": ["signal 1"]
  }
}"""

SYSTEM_P2 = """You are analyzing a code reviewer's review history across multiple PRs in a dbt/SQL analytics repository.
Your job is to build a focus fingerprint — what does this reviewer consistently care about, and what do they appear to overlook or underweight?

Be specific. "Code quality" is not useful. "Grain declaration on fact models" is.
When a focus area maps to a named dbt or SQL standard, cite it.

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
      "example_comments": ["snippet 1"]
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

SYSTEM_P3 = """You are analyzing a code author's pull request history in a dbt/SQL analytics repository.
Your job is to build a growth profile — where do they consistently do well, and where do they consistently need support?

Look for persistence: if the same gap appears in 3+ PRs, it is a growth area, not a one-off.
Cite dbt/SQL standards when relevant. Recommend specific support actions.

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

SYSTEM_P4 = """You are analyzing the complete PR review history of an analytics engineering team working in a dbt/SQL repository.
Your job is to identify where the team is strong collectively and where it has review gaps.

Gap taxonomy:
- coverage_gap: nobody ever reviews for this dimension
- knowledge_gap: reviewers raise this topic but comments are shallow or inconsistent
- blind_spot: this is a named best practice that never appears in any review

Reference the dbt Labs style guide, dbt-project-evaluator check catalog, SQLFluff rules, and Kimball principles explicitly.
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
      "recommendation": "specific action — training, tooling, checklist, or CI gate"
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


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def call_claude(client, system: str, user: str, retries: int = 2, max_tokens: int = MAX_TOKENS) -> dict:
    for attempt in range(retries + 1):
        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            text = strip_fences(msg.content[0].text)
            return json.loads(text)
        except json.JSONDecodeError as e:
            if attempt < retries:
                time.sleep(2)
                continue
            return {"_error": f"JSON parse failed: {e}", "_raw": text[:200]}
        except Exception as e:
            if attempt < retries:
                time.sleep(5)
                continue
            return {"_error": str(e)}


# ── markdown report ───────────────────────────────────────────────────────────
def render_markdown(manifest, pr_results, reviewer_profiles, author_profiles, team_gaps, visibility, repo_slug):
    today    = datetime.now(timezone.utc).date().isoformat()
    dr       = manifest["date_range"]
    n        = manifest["pr_count"]
    contribs = manifest["contributors"]

    lines = [
        f"---",
        f"date: {today}",
        f"repo: {manifest['repo']}",
        f"window: {dr['from']} → {dr['to']}",
        f"pr_count: {n}",
        f"contributors: {contribs}",
        f"visibility: {visibility}",
        f"generated_by: tricorder v1.1.0",
        f"---",
        f"",
        f"# PR Review Analysis — {repo_slug} — {today}",
        f"",
        f"> Window: {dr['from']} → {dr['to']} | {n} PRs | {len(contribs)} contributors",
        f"",
        f"---",
        f"",
        f"## 1. Patterns Ready to Institutionalize",
        f"",
    ]

    # collect all patterns across PRs, filter to convention+ maturity
    all_patterns = []
    for r in pr_results:
        all_patterns.extend(r.get("patterns", []))

    inst_candidates = team_gaps.get("institutionalization_candidates", [])
    if inst_candidates:
        lines.append("| Pattern | Category | Current Maturity | Next Step | Standard |")
        lines.append("|---------|----------|-----------------|-----------|----------|")
        for c in inst_candidates:
            std = c.get("maturity_path_target") or ""
            lines.append(f"| {c['pattern']} | — | {c['current_maturity']} | {c['next_step']} | {c.get('standard_citation') or std} |")
    else:
        lines.append("*No strong institutionalization candidates identified in this window.*")

    lines += ["", "---", "", "## 2. Reviewer Focus Fingerprints", ""]
    for rp in reviewer_profiles:
        if rp.get("_error"):
            continue
        lines.append(f"### {rp['reviewer']}")
        lines.append(f"**Style:** {rp.get('review_style','?')} | **Signal quality:** {rp.get('signal_quality','?')} — {rp.get('signal_quality_rationale','')}")
        lines.append("")
        lines.append("**Primary focus areas:**")
        for fa in rp.get("primary_focus_areas", []):
            cite = f" — *{fa['standard_citation']}*" if fa.get("standard_citation") else ""
            lines.append(f"- {fa['area']} ({fa['frequency']}){cite}")
        lines.append("")
        lines.append("**Apparent blind spots:**")
        for bs in rp.get("apparent_blind_spots", []):
            lines.append(f"- {bs['area']} — {bs['basis']}")
        lines.append("")

    lines += ["---", "", "## 3. Author Growth Profiles", ""]
    if visibility == "team":
        lines.append("> *Individual author profiles omitted in team-visibility reports. Run with --visibility private to include.*")
    else:
        for ap in author_profiles:
            if ap.get("_error"):
                continue
            lines.append(f"### {ap['author']}")
            lines.append(f"**Trajectory:** {ap.get('trajectory','?')} — {ap.get('trajectory_rationale','')}")
            lines.append("")
            lines.append("**Strengths:**")
            for s in ap.get("strengths", []):
                cite = f" — *{s['standard_citation']}*" if s.get("standard_citation") else ""
                lines.append(f"- {s['area']} ({s['persistence']}){cite}")
            lines.append("")
            lines.append("**Growth areas:**")
            for g in ap.get("growth_areas", []):
                cite = f" — *{g['standard_citation']}*" if g.get("standard_citation") else ""
                lines.append(f"- {g['area']} ({g['persistence']}){cite}")
                lines.append(f"  → **Support:** {g.get('support_recommendation','')}")
            lines.append("")

    lines += ["---", "", "## 4. Team Gap Analysis", ""]
    ts = team_gaps.get("team_strengths", [])
    if ts:
        lines.append("### Where the team is strong")
        lines.append("| Area | Evidence | Standard |")
        lines.append("|------|----------|----------|")
        for s in ts:
            lines.append(f"| {s['area']} | {s['evidence']} | {s.get('standard_citation') or '—'} |")
        lines.append("")

    gaps = team_gaps.get("gaps", [])
    if gaps:
        lines.append("### Gaps and blind spots")
        lines.append("| Area | Gap Type | Missing Standard | Recommendation |")
        lines.append("|------|----------|-----------------|----------------|")
        for g in gaps:
            lines.append(f"| {g['area']} | {g['gap_type']} | {g.get('standard_citation') or '—'} | {g['recommendation']} |")
        lines.append("")

    lines.append("### Review culture")
    lines.append(team_gaps.get("review_culture_observations", ""))
    lines += [
        "",
        "---",
        "",
        "## Methodology & Caveats",
        "",
        f"- **Window:** {dr['from']} → {dr['to']} | **PRs analyzed:** {n} | **PRs skipped (no reviews):** {manifest.get('no_review_prs', 0)}",
        f"- **Repo context:** SQLFluff config found | PR template found | dbt_project.yml found",
        f"- **What this analysis cannot see:** verbal review culture (Slack), reviewer availability constraints, domain ownership, or PRs merged without review.",
        "",
        "---",
        "",
        "## Appendix: Reference Standards",
        "",
        "- **dbt Labs style guide**: https://docs.getdbt.com/best-practices/how-we-style/0-how-we-style-our-dbt-projects",
        "- **dbt-project-evaluator**: https://github.com/dbt-labs/dbt-project-evaluator",
        "- **SQLFluff rule catalog**: https://docs.sqlfluff.com/en/stable/rules.html",
        "- **Kimball dimensional modeling**: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/",
        "- **Google Engineering Practices — code review**: https://google.github.io/eng-practices/review/",
        "- **Smart Bear — peer review best practices**: https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/",
    ]
    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", help="OWNER/REPO")
    parser.add_argument("--visibility", default="private",
                        choices=["private", "team", "public"])
    parser.add_argument("--out", default=None,
                        help="Directory for the Markdown report "
                             f"(default: {OUTPUT_BASE})")
    args = parser.parse_args()

    owner, repo_name = args.repo.split("/", 1)
    repo_slug        = f"{owner}__{repo_name}"
    cache_dir        = CACHE_BASE / repo_slug

    if not (cache_dir / "harvest-manifest.json").exists():
        sys.exit(f"❌  No harvest cache found at {cache_dir}. Run harvest first.")

    with open(cache_dir / "harvest-manifest.json") as f:
        manifest = json.load(f)
    with open(cache_dir / "repo-context.json") as f:
        repo_ctx = json.load(f)

    pr_files = sorted(cache_dir.glob("prs/*.json"))
    print(f"\n🔬  tricorder — synthesize")
    print(f"    Repo:       {args.repo}")
    print(f"    PRs:        {len(pr_files)}")
    print(f"    Window:     {manifest['date_range']['from']} → {manifest['date_range']['to']}")
    print(f"    Visibility: {args.visibility}")
    print(f"    Model:      {MODEL}\n")

    api_key = get_api_key()
    client  = anthropic.Anthropic(api_key=api_key)

    synth_dir = cache_dir / "synthesis"
    synth_dir.mkdir(exist_ok=True)
    (synth_dir / "pr").mkdir(exist_ok=True)
    (synth_dir / "reviewers").mkdir(exist_ok=True)
    (synth_dir / "authors").mkdir(exist_ok=True)

    # load author tenure for payloads
    tenure = manifest.get("author_tenure", {})

    # ── Prompt 1: per-PR ──────────────────────────────────────────────────────
    print(f"Phase 1 — Per-PR extraction ({len(pr_files)} PRs)...")
    pr_results = []
    for i, pr_path in enumerate(pr_files, 1):
        out_path = synth_dir / "pr" / pr_path.name
        if out_path.exists():
            with open(out_path) as f:
                pr_results.append(json.load(f))
            continue

        with open(pr_path) as f:
            pr = json.load(f)
        pr["_tenure_days"] = tenure.get(pr["author"]["login"], {}).get("cache_days", "?")

        rev_path = cache_dir / "reviews" / f"{pr['number']}-reviews.json"
        com_path = cache_dir / "comments" / f"{pr['number']}-comments.json"
        reviews  = json.load(open(rev_path)) if rev_path.exists() else []
        comments = json.load(open(com_path)) if com_path.exists() else []

        if not reviews and not comments:
            print(f"  [{i:03d}/{len(pr_files)}] #{pr['number']} — skipped (no reviews)")
            continue

        payload = build_pr_payload(pr, reviews, comments, repo_ctx)
        result  = call_claude(client, SYSTEM_P1, payload)
        result["_pr_number"] = pr["number"]
        result["_author"]    = pr["author"]["login"]

        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        pr_results.append(result)

        status = "⚠ error" if result.get("_error") else f"{len(result.get('patterns',[]))} patterns"
        print(f"  [{i:03d}/{len(pr_files)}] #{pr['number']:5d} {pr['author']['login']:<16} {status}")
        time.sleep(0.3)

    print(f"\n  ✓ {len(pr_results)} PRs processed\n")

    # ── Prompt 2: reviewer fingerprints ──────────────────────────────────────
    reviewers = manifest.get("contributors", [])
    print(f"Phase 2 — Reviewer fingerprints ({len(reviewers)} reviewers)...")
    reviewer_profiles = []
    for reviewer in reviewers:
        out_path = synth_dir / "reviewers" / f"{reviewer}.json"
        if out_path.exists():
            with open(out_path) as f:
                reviewer_profiles.append(json.load(f))
            print(f"  {reviewer:<20} (cached)")
            continue

        # collect all reviews by this reviewer
        review_lines = [f"Reviewer: {reviewer}", ""]
        pr_count = 0
        for pr_path in pr_files:
            with open(pr_path) as f:
                pr = json.load(f)
            rev_path = cache_dir / "reviews" / f"{pr['number']}-reviews.json"
            com_path = cache_dir / "comments" / f"{pr['number']}-comments.json"
            reviews  = json.load(open(rev_path)) if rev_path.exists() else []
            comments = json.load(open(com_path)) if com_path.exists() else []

            my_reviews  = [r for r in reviews  if r.get("user", {}).get("login") == reviewer]
            my_comments = [c for c in comments if c.get("user", {}).get("login") == reviewer]
            if not my_reviews and not my_comments:
                continue

            pr_count += 1
            review_lines.append(f"PR #{pr['number']}: {pr['title']}")
            for r in my_reviews:
                review_lines.append(f"  [{r.get('state','')}] {(r.get('body') or '')[:400]}")
            for c in my_comments:
                review_lines.append(f"  inline on {c.get('path','')}: {(c.get('body') or '')[:300]}")
            review_lines.append("")

        if pr_count == 0:
            print(f"  {reviewer:<20} skipped (no reviews found)")
            continue

        review_lines.insert(1, f"PRs reviewed: {pr_count}")
        result = call_claude(client, SYSTEM_P2, "\n".join(review_lines))
        result["_reviewer"] = reviewer

        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        reviewer_profiles.append(result)
        status = "⚠ error" if result.get("_error") else result.get("signal_quality", "?")
        print(f"  {reviewer:<20} signal_quality={status}  prs={pr_count}")
        time.sleep(0.3)

    print(f"\n  ✓ {len(reviewer_profiles)} reviewer profiles\n")

    # ── Prompt 3: author growth profiles ─────────────────────────────────────
    authors = manifest.get("contributors", [])
    print(f"Phase 3 — Author growth profiles ({len(authors)} authors)...")
    author_profiles = []
    for author in authors:
        out_path = synth_dir / "authors" / f"{author}.json"
        if out_path.exists():
            with open(out_path) as f:
                author_profiles.append(json.load(f))
            print(f"  {author:<20} (cached)")
            continue

        pr_lines = [f"Author: {author}", ""]
        pr_count = 0
        author_pr_files = [p for p in pr_files if json.load(open(p)).get("author", {}).get("login") == author]
        # sort chronologically
        author_pr_files.sort(key=lambda p: json.load(open(p)).get("mergedAt", ""))

        for pr_path in author_pr_files:
            with open(pr_path) as f:
                pr = json.load(f)
            rev_path = cache_dir / "reviews" / f"{pr['number']}-reviews.json"
            com_path = cache_dir / "comments" / f"{pr['number']}-comments.json"
            reviews  = json.load(open(rev_path)) if rev_path.exists() else []
            comments = json.load(open(com_path)) if com_path.exists() else []

            if not reviews and not comments:
                continue
            pr_count += 1
            pr_lines.append(f"PR #{pr['number']} ({pr.get('mergedAt','')[:10]}): {pr['title']}")
            for r in reviews:
                pr_lines.append(f"  reviewer {r.get('user',{}).get('login','')} [{r.get('state','')}]: {(r.get('body') or '')[:300]}")
            for c in comments:
                pr_lines.append(f"  inline on {c.get('path','')}: {(c.get('body') or '')[:200]}")
            pr_lines.append("")

        if pr_count == 0:
            print(f"  {author:<20} skipped (no reviewed PRs)")
            continue

        pr_lines.insert(1, f"PRs in window: {pr_count}")
        result = call_claude(client, SYSTEM_P3, "\n".join(pr_lines))
        result["_author"] = author

        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        author_profiles.append(result)
        status = "⚠ error" if result.get("_error") else result.get("trajectory", "?")
        print(f"  {author:<20} trajectory={status}  prs={pr_count}")
        time.sleep(0.3)

    print(f"\n  ✓ {len(author_profiles)} author profiles\n")

    # ── Prompt 4: team gap analysis ───────────────────────────────────────────
    print("Phase 4 — Team gap analysis...")
    team_gaps_path = synth_dir / "team-gaps.json"
    if team_gaps_path.exists():
        with open(team_gaps_path) as f:
            team_gaps = json.load(f)
        print("  (cached)\n")
    else:
        all_patterns = []
        for r in pr_results:
            all_patterns.extend(r.get("patterns", []))

        team_prompt_lines = [
            f"Team: {', '.join(manifest['contributors'])}",
            f"Window: {manifest['date_range']['from']} → {manifest['date_range']['to']}",
            f"PR count: {manifest['pr_count']}",
            "",
            "Aggregated pattern signals:",
            json.dumps(all_patterns, indent=2)[:8000],
            "",
            "Reviewer fingerprints:",
            json.dumps([{k: v for k, v in rp.items() if not k.startswith("_")} for rp in reviewer_profiles], indent=2)[:4000],
        ]

        team_gaps = call_claude(client, SYSTEM_P4, "\n".join(team_prompt_lines), max_tokens=8192)
        with open(team_gaps_path, "w") as f:
            json.dump(team_gaps, f, indent=2)
        status = "⚠ error" if team_gaps.get("_error") else f"{len(team_gaps.get('gaps',[]))} gaps identified"
        print(f"  ✓ {status}\n")

    # ── render report ─────────────────────────────────────────────────────────
    print("Rendering Markdown report...")
    out_dir = Path(args.out) if args.out else OUTPUT_BASE
    out_dir.mkdir(parents=True, exist_ok=True)
    today     = datetime.now(timezone.utc).date().isoformat()
    out_file  = out_dir / f"{today}-{repo_slug}.md"

    md = render_markdown(manifest, pr_results, reviewer_profiles, author_profiles, team_gaps, args.visibility, args.repo)
    with open(out_file, "w") as f:
        f.write(md)

    print(f"\n✓ Report written to: {out_file}")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
