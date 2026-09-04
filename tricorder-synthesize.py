#!/usr/bin/env python3
"""
tricorder — synthesize
----------------------
Loads harvest cache for a repo and runs 4 LLM calls:
  1. Per-PR pattern extraction (one call per PR)
  2. Reviewer focus fingerprints (one call per reviewer)
  3. Author growth profiles (one call per author)
  4. Team gap analysis (one aggregate call)

Outputs a Markdown report to adventures-in-ai/tricorder/.

Usage:
  python tricorder-synthesize.py OWNER/REPO [--visibility private|team|public]

Auth:
    Reads the active provider key from the configured environment variable.
    Anthropic still supports the macOS keychain fallback:
        security find-generic-password -a "$USER" -s "anthropic_api_key" -w
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from tricorder.llm import build_llm_provider


# ── config ────────────────────────────────────────────────────────────────────
CACHE_BASE       = Path.home() / ".learn-from-work" / "cache"
_DEFAULT_OUT     = Path.home() / "Documents" / "dev" / "adventures-in-ai" / "tricorder"
OUTPUT_BASE      = _DEFAULT_OUT if _DEFAULT_OUT.exists() else Path("output")
MAX_TOKENS       = 8192


# ── lens ──────────────────────────────────────────────────────────────────────
# Domain knowledge (categories, file tags, authorities, prompt context) comes
# from a YAML lens: tricorder/lenses/data/*.yaml, overridable via
# ~/.tricorder/lenses/. Detection runs over the GitHub tree when --lens is absent.
from tricorder.lenses import Lens, LensError, load_all
from tricorder.lenses.detect import (
    composition_check, detect, fetch_github, github_token, review_path_check,
)
from tricorder.lenses.prompting import (
    authorities_markdown, coerce_categories, secondary_block, smoke_check, system_prompt,
)
from tricorder.lenses.cache import load_cached, save_cached, synthesis_dir, write_current
from tricorder.oversight import compute as compute_oversight, normalize_legacy, oversight_prompt_block


# ── payload assembly ──────────────────────────────────────────────────────────
def build_pr_payload(pr: dict, reviews: list, comments: list, repo_ctx: dict,
                     lens: Lens | None = None, gates: list | None = None) -> str:
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

    lines.append(f"Repo context:")
    gate_names = [f"{g['tool']} ({g['config_file']})" for g in (gates or [])]
    lines.append(f"- Tooling gates present: {', '.join(gate_names) if gate_names else 'none detected'}")
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
        ftype = lens.file_tag(path) if lens else "other"
        cbody = (c.get("body") or "").strip()
        replied = " [has_reply]" if c.get("has_reply") else ""
        lines.append(f"  {user} on {path} [{ftype}]{replied}: {cbody[:300]}")

    return "\n".join(lines)


# ── llm calls ─────────────────────────────────────────────────────────────────
def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def call_llm(client, system: str, user: str, retries: int = 2, max_tokens: int = MAX_TOKENS) -> dict:
    for attempt in range(retries + 1):
        try:
            text = strip_fences(client.generate(system, user, max_tokens))
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
def render_markdown(manifest, pr_results, reviewer_profiles, author_profiles, team_gaps, visibility, repo_slug,
                    lens: Lens | None = None, gates: list | None = None, oversight: dict | None = None):
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
        f"lens: {lens.name if lens else 'unknown'}",
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

    if oversight:
        lines += ["", "---", "", "## 1b. Oversight Density", "",
                  "Computed from the harvested record, no model involved. In agentic development, review is where human oversight concentrates; this section shows where it does and does not land.", ""]
        osum = oversight["summary"]
        lines.append(f"- PRs with no human engagement (approve-only or nothing): **{osum['prs_without_human_engagement']} of {osum['prs']}**")
        lines.append(f"- Silent approvals (approve with no comment): **{osum['silent_approvals']} of {osum['approvals']}**")
        if "inline_comments_by_bots" in osum:
            lines.append(f"- Inline comments: **{osum['inline_comments_by_human_reviewers']}** by human reviewers, "
                         f"**{osum['inline_comments_by_bots']}** by bots or AI reviewers, "
                         f"{osum['inline_comments_by_pr_authors']} by PR authors replying on their own PRs")
            lines.append(f"- PRs where a bot commented and no human reviewer did: **{osum['prs_bot_only']} of {osum['prs']}**")
        if osum.get("prs_with_changed_files"):
            lines += ["", "Per axis: of the PRs that changed files under the axis, who commented on those files.", "",
                      "| Axis | High-stakes | PRs touching | Human reviewer | Bot only | Nobody | Silent share | Comments | Reviewers |", "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
            for a in oversight["per_axis"]:
                if a.get("prs_touching") is None:
                    continue
                e = a.get("engagement") or {}
                human = e.get("human_and_bot", 0) + e.get("human_only", 0)
                lines.append(f"| {a['axis']} | {'yes' if a['high_stakes'] else ''} | {a['prs_touching']} | {human} | {e.get('bot_only', 0)} | {e.get('nobody', 0)} | {(a['silent_share'] or 0):.0%} | {a['comments']} | {a['distinct_reviewers']} |")
        lines += ["", "| Reviewer | PRs | Approvals | Silent approvals | Silent share | Inline comments / PR |", "|---|---:|---:|---:|---:|---:|"]
        for r in oversight["per_reviewer"]:
            share = f"{r['silent_share']:.0%}" if r["silent_share"] is not None else "—"
            lines.append(f"| {r['reviewer']} | {r['prs']} | {r['approvals']} | {r['silent_approvals']} | {share} | {r['comments_per_pr']} |")

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
        f"- **Lens:** {lens.name} (v{lens.version}, {lens.status})" if lens else "- **Lens:** none",
        f"- **Tooling gates present:** {', '.join(g['tool'] for g in (gates or [])) or 'none detected'}",
        f"- **What this analysis cannot see:** verbal review culture (Slack), reviewer availability constraints, domain ownership, or PRs merged without review.",
        "",
        "---",
        "",
        "## Appendix: Reference Standards",
        "",
        *(authorities_markdown(lens) if lens else ["- (no lens selected)"]),
    ]
    return "\n".join(lines)


# ── lens resolution ───────────────────────────────────────────────────────────
def resolve_lens(explicit: str | None, cache_dir: Path, owner: str, repo_name: str):
    """--lens, else the lens recorded in the cache, else GitHub-tree detection.

    Returns (lens, tooling_gates_present, checks, source, secondary). Writes
    <cache>/lens-detection.json so later runs and the explorer renderer agree.
    """
    lenses = load_all(extra_dirs=[cache_dir / "lenses"])
    detection_path = cache_dir / "lens-detection.json"
    recorded = json.loads(detection_path.read_text()) if detection_path.exists() else {}

    comment_paths = []
    for com_path in cache_dir.glob("comments/*.json"):
        try:
            comment_paths += [c.get("path", "") for c in json.load(open(com_path))]
        except Exception:
            pass

    name = None; source = ""; gates = list(recorded.get("tooling_gates_present") or [])
    secondary_name = recorded.get("runner_up") if recorded.get("state") == "mixed" else None
    lang_bytes = recorded.get("language_bytes") or None
    if explicit:
        if explicit not in lenses:
            raise LensError(f"unknown lens {explicit!r}; available: {', '.join(sorted(lenses))}")
        name, source = explicit, "--lens"
    elif recorded.get("selected") and recorded["selected"] in lenses:
        name, source = recorded["selected"], "cache (lens-detection.json)"
    else:
        token = github_token()
        if not token:
            raise LensError("no --lens given, none recorded in the cache, and no GitHub token for detection")
        print(f"    Detecting lens from the GitHub tree of {owner}/{repo_name} …")
        paths, lang_bytes = fetch_github(owner, repo_name, token)
        result = detect(paths, lenses)
        gates = result.tooling_gates_present
        recorded = {"selected": result.selected, "state": result.state, "runner_up": result.runner_up,
                    "margin": result.margin, "scores": result.scores, "min_score": result.min_score,
                    "min_margin": result.min_margin, "ignored_paths": result.ignored_paths,
                    "tooling_gates_present": gates, "language_bytes": lang_bytes,
                    "detected_at": datetime.now(timezone.utc).isoformat()}
        detection_path.write_text(json.dumps(recorded, indent=2))
        if result.state == "unknown":
            best = max(result.scores, key=result.scores.get) if result.scores else "?"
            raise LensError(f"detection returned unknown (best candidate {best} scored "
                            f"{result.scores.get(best, 0)}, below min_score {result.min_score}); pass --lens NAME")
        if result.state == "mixed":
            print(f"    ⚠ mixed detection: {result.runner_up} trails by only {result.margin}; using {result.selected}")
        name = result.selected
        source = f"auto-detected ({result.state}, score {result.scores[name]}, margin {result.margin})"

    lens = lenses[name]
    checks = []
    if lang_bytes:
        checks.append(composition_check(lens, lang_bytes))
    checks.append(review_path_check(lens, comment_paths))
    secondary = lenses.get(secondary_name) if secondary_name and secondary_name != name else None
    return lens, gates, checks, source, secondary


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", help="OWNER/REPO")
    parser.add_argument("--visibility", default="private",
                        choices=["private", "team", "public"])
    parser.add_argument("--provider", choices=["anthropic", "gemini"], default=None,
                        help="Override the active LLM provider")
    parser.add_argument("--model", default=None,
                        help="Override the model for the active provider")
    parser.add_argument("--api-key-env", dest="api_key_env", default=None,
                        help="Override the environment variable name used for the key")
    parser.add_argument("--keychain-service", dest="keychain_service", default=None,
                        help="Override the macOS keychain service used for the key")
    parser.add_argument("--out", default=None,
                        help="Directory for the Markdown report "
                             f"(default: {OUTPUT_BASE})")
    parser.add_argument("--lens", default=None, metavar="NAME",
                        help="Discipline lens. Default: the lens recorded in the cache from a previous run, "
                             "else auto-detected from the GitHub tree (needs GITHUB_TOKEN or keychain PAT).")
    parser.add_argument("--force", action="store_true",
                        help="Proceed even if the lens verification checks fail.")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="Resolve the lens, run verification, print the Phase 1 and 4 prompts, and exit.")
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

    try:
        lens, gates, checks, lens_source, secondary = resolve_lens(args.lens, cache_dir, owner, repo_name)
    except LensError as e:
        sys.exit(f"❌  Lens error: {e}")
    print(f"    Lens:       {lens.name} (v{lens.version}, {lens.status}; {lens_source})")
    if secondary:
        print(f"    Secondary:  {secondary.name} (mixed repository; axes reported only with evidence)")
    for c in checks:
        print(f"      {'✓' if c.passed else '✗'} {c.name}: {c.detail}")
    if any(not c.passed for c in checks) and not args.force:
        sys.exit("❌  Lens verification failed: the selected lens does not fit this repository.\n"
                 "    Pass --lens NAME to choose another lens, or --force to proceed anyway.")
    if args.dry_run:
        print(f"    Gates:      {', '.join(g['tool'] for g in gates) or 'none'}")
        print("\n--- Phase 1 system prompt ---\n" + system_prompt("p1", lens, gates))
        print("\n--- Phase 4 system prompt ---\n" + system_prompt("p4", lens, gates, secondary_block(secondary) or None))
        print("\nDry run: no LLM calls made.")
        return
    sys_p1 = system_prompt("p1", lens, gates)
    sys_p2 = system_prompt("p2", lens, gates)
    sys_p3 = system_prompt("p3", lens, gates)
    sys_p4 = system_prompt("p4", lens, gates, secondary_block(secondary) or None)
    client = build_llm_provider(
        provider=args.provider,
        model=args.model,
        api_key_env=args.api_key_env,
        keychain_service=args.keychain_service,
    )
    print(f"    LLM:        {client.config.provider} / {client.config.model}")
    print(f"    Key env:    {client.config.api_key_env}\n")

    # Cache is keyed by lens: outputs produced under another lens's prompts are never reused.
    synth_root = cache_dir / "synthesis"
    synth_dir = synthesis_dir(synth_root, lens)
    write_current(synth_root, lens, {"source": lens_source})
    print(f"    Cache:      {synth_dir}\n")

    # load author tenure for payloads
    tenure = manifest.get("author_tenure", {})

    # ── Prompt 1: per-PR ──────────────────────────────────────────────────────
    print(f"Phase 1 — Per-PR extraction ({len(pr_files)} PRs)...")
    pr_results = []
    for i, pr_path in enumerate(pr_files, 1):
        out_path = synth_dir / "pr" / pr_path.name
        cached = load_cached(out_path, lens)
        if cached is not None:
            pr_results.append(cached)
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

        payload = build_pr_payload(pr, reviews, comments, repo_ctx, lens, gates)
        result  = call_llm(client, sys_p1, payload)
        result["_pr_number"] = pr["number"]
        result["_author"]    = pr["author"]["login"]
        coerce_categories(result, lens)

        save_cached(out_path, result, lens)
        pr_results.append(result)

        status = "⚠ error" if result.get("_error") else f"{len(result.get('patterns',[]))} patterns"
        print(f"  [{i:03d}/{len(pr_files)}] #{pr['number']:5d} {pr['author']['login']:<16} {status}")
        time.sleep(0.3)

    print(f"\n  ✓ {len(pr_results)} PRs processed\n")

    # ── Oversight density (no LLM): where human attention lands, from the harvest ──
    records = []
    for pr_path in pr_files:
        pr = json.loads(pr_path.read_text())
        rv = cache_dir / "reviews" / f"{pr['number']}-reviews.json"
        cm = cache_dir / "comments" / f"{pr['number']}-comments.json"
        records.append(normalize_legacy(pr, json.loads(rv.read_text()) if rv.exists() else [],
                                        json.loads(cm.read_text()) if cm.exists() else []))
    oversight = compute_oversight(records, lens)
    (synth_dir / "oversight.json").write_text(json.dumps(oversight, indent=2))
    ov = oversight["summary"]
    print(f"Oversight — {ov['prs_without_human_engagement']}/{ov['prs']} PRs with no human engagement; "
          f"silent approvals {ov['silent_approvals']}/{ov['approvals']}; "
          f"changed-file lists for {ov['prs_with_changed_files']} PRs\n")

    # ── Prompt 2: reviewer fingerprints ──────────────────────────────────────
    reviewers = manifest.get("contributors", [])
    print(f"Phase 2 — Reviewer fingerprints ({len(reviewers)} reviewers)...")
    reviewer_profiles = []
    for reviewer in reviewers:
        out_path = synth_dir / "reviewers" / f"{reviewer}.json"
        cached = load_cached(out_path, lens)
        if cached is not None:
            reviewer_profiles.append(cached)
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
        result = call_llm(client, sys_p2, "\n".join(review_lines))
        result["_reviewer"] = reviewer

        save_cached(out_path, result, lens)
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
        cached = load_cached(out_path, lens)
        if cached is not None:
            author_profiles.append(cached)
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
        result = call_llm(client, sys_p3, "\n".join(pr_lines))
        result["_author"] = author

        save_cached(out_path, result, lens)
        author_profiles.append(result)
        status = "⚠ error" if result.get("_error") else result.get("trajectory", "?")
        print(f"  {author:<20} trajectory={status}  prs={pr_count}")
        time.sleep(0.3)

    print(f"\n  ✓ {len(author_profiles)} author profiles\n")

    # ── Prompt 4: team gap analysis ───────────────────────────────────────────
    print("Phase 4 — Team gap analysis...")
    team_gaps_path = synth_dir / "team-gaps.json"
    team_gaps = load_cached(team_gaps_path, lens)
    if team_gaps is not None:
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
            "",
            oversight_prompt_block(oversight),
        ]

        team_gaps = call_llm(client, sys_p4, "\n".join(team_prompt_lines), max_tokens=8192)
        save_cached(team_gaps_path, team_gaps, lens)
        status = "⚠ error" if team_gaps.get("_error") else f"{len(team_gaps.get('gaps',[]))} gaps identified"
        print(f"  ✓ {status}\n")

    # ── lens smoke checks ─────────────────────────────────────────────────────
    smoke_hits = {}
    for label, obj in (("phase1", pr_results), ("phase2", reviewer_profiles),
                       ("phase3", author_profiles), ("phase4", team_gaps)):
        hits = smoke_check(lens, obj)
        if hits:
            smoke_hits[label] = hits
    if smoke_hits:
        print("  ⚠ Lens smoke check failed — off-domain terms in output:")
        for label, hits in smoke_hits.items():
            print(f"      {label}: {', '.join(hits)}")
        print("    Cached phase outputs are kept; fix the lens and delete the affected files to regenerate.\n")
    with open(synth_dir / "lens.json", "w") as f:
        json.dump({**lens.summary(), "source": lens_source,
                   "secondary_lens": secondary.summary() if secondary else None,
                   "tooling_gates_present": gates,
                   "checks": [{"name": c.name, "passed": c.passed, "detail": c.detail} for c in checks],
                   "smoke_check_hits": smoke_hits}, f, indent=2)

    # ── render report ─────────────────────────────────────────────────────────
    print("Rendering Markdown report...")
    out_dir = Path(args.out) if args.out else OUTPUT_BASE
    out_dir.mkdir(parents=True, exist_ok=True)
    today     = datetime.now(timezone.utc).date().isoformat()
    out_file  = out_dir / f"{today}-{repo_slug}.md"

    md = render_markdown(manifest, pr_results, reviewer_profiles, author_profiles, team_gaps, args.visibility, args.repo, lens, gates, oversight)
    with open(out_file, "w") as f:
        f.write(md)

    print(f"\n✓ Report written to: {out_file}")
    if smoke_hits:
        sys.exit("\n❌  Done, but the lens smoke check found off-domain terms (see above).")
    print(f"\nDone.")


if __name__ == "__main__":
    main()
