#!/usr/bin/env python3
"""
tricorder — cost probe
----------------------------
Dry-harvest up to N merged PRs from a GitHub repo, assemble the exact
Prompt 1 payload for each PR, count tokens, and print a cost estimate
table. No Claude API calls made.

Usage:
  python tricorder-cost-probe.py OWNER/REPO [--limit N] [--since YYYY-MM-DD]

Requirements:
  pip install requests

Auth:
  Reads GITHUB_TOKEN from environment. This script uses the GitHub REST API
  (not git operations), so SSH keys don't apply here. You need a PAT with
  public_repo scope (classic) or Pull requests: read (fine-grained).

  Set it once:
    export GITHUB_TOKEN=your_token          # session only
    echo 'export GITHUB_TOKEN=your_token' >> ~/.zshrc   # permanent

  The token needs no special scopes to read public repos like cal-itp/data-infra.
  A classic PAT with public_repo is sufficient. Fine-grained PAT needs:
    - Repository access: cal-itp/data-infra (or All public repositories)
    - Permissions: Pull requests — read-only
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone


# ── pricing (Sonnet 4, May 2026) ──────────────────────────────────────────────
PRICE_INPUT_PER_M  = 3.00   # $ per 1M input tokens
PRICE_OUTPUT_PER_M = 15.00  # $ per 1M output tokens

# Estimated output tokens per Prompt 1 call (~300 tokens structured JSON)
EST_OUTPUT_TOKENS_PER_PR = 300

# System prompt + output schema overhead per Prompt 1 call (~600 tokens)
SYSTEM_PROMPT_OVERHEAD = 600

# Multiplier for Prompts 2–4 (reviewer fingerprints, author profiles, team gaps)
# These re-read subsets of the same data — empirically ~1.5× the Prompt 1 total
AGGREGATION_PASS_MULTIPLIER = 1.5

# Token approximation: chars / 4 for prose, chars / 3.5 for technical content
# We use 3.8 as a conservative middle ground (slightly overestimates = safer)
CHARS_PER_TOKEN = 3.8


# ── auth ──────────────────────────────────────────────────────────────────────
def get_github_token() -> str:
    """
    SSH keys handle git operations (push/pull to your own repos) but don't
    work for the GitHub REST API. This script needs a PAT in GITHUB_TOKEN.

    Create one at: https://github.com/settings/tokens
    Scope needed:  public_repo (classic) — or Pull requests: read (fine-grained)

    Set it:
      export GITHUB_TOKEN=ghp_your_token          # current session
      echo 'export GITHUB_TOKEN=ghp_...' >> ~/.zshrc   # permanent
    """
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    sys.exit(
        "\n❌  GITHUB_TOKEN not set.\n\n"
        "    SSH keys cover git operations but the GitHub API needs a PAT.\n"
        "    Create one: https://github.com/settings/tokens\n"
        "    Scope: public_repo (classic) or Pull requests: read (fine-grained)\n\n"
        "    Then: export GITHUB_TOKEN=your_token\n"
    )


# ── github api ────────────────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")


class GitHub:
    BASE = "https://api.github.com"

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def get(self, path: str, params: dict = None) -> dict | list:
        url = f"{self.BASE}{path}"
        r = self.session.get(url, params=params, timeout=15)
        self._check_rate(r)
        r.raise_for_status()
        return r.json()

    def _check_rate(self, r):
        remaining = int(r.headers.get("X-RateLimit-Remaining", 999))
        if remaining < 50:
            reset = int(r.headers.get("X-RateLimit-Reset", 0))
            wait = max(0, reset - int(time.time())) + 2
            print(f"\n⚠  Rate limit low ({remaining} remaining). "
                  f"Waiting {wait}s…", flush=True)
            time.sleep(wait)


# ── token counting ─────────────────────────────────────────────────────────────
def count_tokens(text: str) -> int:
    """
    Approximation: chars / 3.8
    Accurate to ±10% for mixed prose + technical content.
    Slightly conservative (overestimates) — better for cost planning.
    For reference: tiktoken cl100k_base gives ~chars/4 for English prose
    and ~chars/3.5 for code/JSON. We split the difference.
    """
    return max(1, int(len(text) / CHARS_PER_TOKEN))


# ── description quality scoring ───────────────────────────────────────────────
def score_description(body: str) -> dict:
    if not body:
        return {"quality": "low", "word_count": 0}
    wc = len(body.split())
    has_why     = any(w in body.lower() for w in
                      ["why", "because", "motivation", "context"])
    has_what    = any(w in body.lower() for w in
                      ["change", "added", "removed", "updated", "refactor"])
    has_testing = any(w in body.lower() for w in
                      ["test", "verified", "checked", "validated", "dbt run",
                       "dbt build", "dbt test"])
    score = sum([wc >= 50, has_why, has_what, has_testing])
    quality = "high" if score >= 3 else "medium" if score >= 2 else "low"
    return {"quality": quality, "word_count": wc}


def count_iterations(reviews: list) -> int:
    return sum(1 for r in reviews if r.get("state") == "CHANGES_REQUESTED")


# ── payload assembly ──────────────────────────────────────────────────────────
def assemble_prompt1_payload(pr: dict, reviews: list, comments: list) -> str:
    """
    Assembles the USER portion of Prompt 1 exactly as the skill would send it.
    System prompt overhead is added as a fixed constant separately.
    """
    lines = []

    lines.append(f"PR #{pr['number']}: {pr['title']}")
    lines.append(f"Author: {pr['user']['login']}")
    lines.append(f"Review iterations before approval: {count_iterations(reviews)}")

    body = pr.get("body") or ""
    dq = score_description(body)
    conf_flag = " ⚠ LOW CONFIDENCE" if dq["quality"] == "low" else ""
    lines.append(f"Description quality: {dq['quality']}{conf_flag}")
    lines.append("")
    lines.append("Description:")
    lines.append(body[:2000] if body else "(none)")
    lines.append("")

    lines.append("Reviews:")
    for rev in reviews:
        reviewer = rev.get("user", {}).get("login", "unknown")
        state    = rev.get("state", "")
        rbody    = (rev.get("body") or "").strip()
        lines.append(f"  [{state}] {reviewer}: {rbody[:500]}")

    lines.append("")
    lines.append("Inline comments:")
    for c in comments[:50]:  # cap runaway PRs
        user   = c.get("user", {}).get("login", "unknown")
        path   = c.get("path", "")
        cbody  = (c.get("body") or "").strip()
        lines.append(f"  {user} on {path}: {cbody[:300]}")

    return "\n".join(lines)


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Estimate Claude API token cost for tricorder synthesis."
    )
    parser.add_argument("repo",
                        help="OWNER/REPO  e.g. cal-itp/data-infra")
    parser.add_argument("--limit", type=int, default=20,
                        help="Max PRs to sample (default: 20)")
    parser.add_argument("--since", type=str, default=None,
                        help="Only PRs merged after this date (YYYY-MM-DD)")
    args = parser.parse_args()

    owner, repo_name = args.repo.split("/", 1)
    token = get_github_token()
    gh    = GitHub(token)

    print(f"\n📡  tricorder — cost probe")
    print(f"    Repo:   {args.repo}")
    print(f"    Sample: {args.limit} PRs")
    if args.since:
        print(f"    Since:  {args.since}")
    print(f"    Token approximation: chars / {CHARS_PER_TOKEN} (±10%)")
    print()

    # ── 1. fetch merged PRs ───────────────────────────────────────────────────
    print("Fetching merged PRs…", flush=True)
    params = {
        "state": "closed",
        "sort": "updated",
        "direction": "desc",
        "per_page": min(args.limit * 3, 100),
    }
    raw_prs = gh.get(f"/repos/{owner}/{repo_name}/pulls", params)

    since_dt = None
    if args.since:
        since_dt = datetime.fromisoformat(args.since).replace(
            tzinfo=timezone.utc)

    prs = []
    for pr in raw_prs:
        if not pr.get("merged_at"):
            continue
        if since_dt:
            merged = datetime.fromisoformat(
                pr["merged_at"].replace("Z", "+00:00"))
            if merged < since_dt:
                continue
        prs.append(pr)
        if len(prs) >= args.limit:
            break

    if not prs:
        sys.exit("\n❌  No merged PRs found in the specified window.\n"
                 "    Try removing --since or increasing --limit.\n")

    print(f"Found {len(prs)} merged PRs. Fetching reviews + comments…\n")

    # ── 2. per-PR fetch + measure ─────────────────────────────────────────────
    rows                 = []
    total_p1_input       = 0
    total_p1_output      = 0
    desc_quality_counts  = {"high": 0, "medium": 0, "low": 0}
    iteration_counts     = []
    skipped_no_reviews   = 0

    for i, pr in enumerate(prs, 1):
        num = pr["number"]
        print(f"  [{i:02d}/{len(prs)}] #{num:5d}  "
              f"{pr['title'][:55]:<55}", end="", flush=True)

        try:
            reviews  = gh.get(f"/repos/{owner}/{repo_name}/pulls/{num}/reviews")
        except Exception:
            reviews  = []

        try:
            comments = gh.get(f"/repos/{owner}/{repo_name}/pulls/{num}/comments")
        except Exception:
            comments = []

        # skip PRs with zero reviews — they're noise in synthesis
        if not reviews and not comments:
            skipped_no_reviews += 1
            print("  (skipped — no reviews)")
            continue

        payload      = assemble_prompt1_payload(pr, reviews, comments)
        user_tokens  = count_tokens(payload)
        p1_input     = user_tokens + SYSTEM_PROMPT_OVERHEAD
        p1_output    = EST_OUTPUT_TOKENS_PER_PR

        dq           = score_description(pr.get("body") or "")
        iterations   = count_iterations(reviews)

        desc_quality_counts[dq["quality"]] += 1
        iteration_counts.append(iterations)

        rows.append({
            "pr":         num,
            "author":     pr["user"]["login"],
            "reviews":    len(reviews),
            "inline":     len(comments),
            "desc":       dq["quality"],
            "iter":       iterations,
            "p1_input":   p1_input,
            "p1_output":  p1_output,
            "payload_chars": len(payload),
        })

        total_p1_input  += p1_input
        total_p1_output += p1_output

        print(f"  {len(reviews)}rev  {len(comments)}inline  "
              f"{dq['quality']:6}  {p1_input:>6,}tok")

        time.sleep(0.15)  # polite rate limit headroom

    if not rows:
        sys.exit("\n❌  All sampled PRs had no review activity. "
                 "Try a different window.\n")

    # ── 3. aggregation pass estimates ─────────────────────────────────────────
    # Prompts 2-4 re-read subsets of the data already loaded in Prompt 1.
    # Reviewer fingerprints + author profiles + team gaps ≈ 1.5× Prompt 1 input.
    agg_input  = int(total_p1_input  * AGGREGATION_PASS_MULTIPLIER)
    agg_output = int(total_p1_output * 0.5)   # profiles are terser than per-PR JSON

    grand_input  = total_p1_input  + agg_input
    grand_output = total_p1_output + agg_output

    # ── 4. cost ───────────────────────────────────────────────────────────────
    p1_cost    = ((total_p1_input  / 1_000_000) * PRICE_INPUT_PER_M +
                  (total_p1_output / 1_000_000) * PRICE_OUTPUT_PER_M)
    agg_cost   = ((agg_input       / 1_000_000) * PRICE_INPUT_PER_M +
                  (agg_output      / 1_000_000) * PRICE_OUTPUT_PER_M)
    total_cost = p1_cost + agg_cost
    per_pr     = total_cost / len(rows)

    n_reviewed = len(rows)
    avg_reviews = sum(r["reviews"] for r in rows) / n_reviewed
    avg_inline  = sum(r["inline"]  for r in rows) / n_reviewed
    avg_iter    = sum(iteration_counts) / len(iteration_counts) if iteration_counts else 0
    avg_tokens  = total_p1_input / n_reviewed

    # ── 5. report ─────────────────────────────────────────────────────────────
    HR = "─" * 70

    print()
    print(HR)
    print(f"  COST PROBE RESULTS — {args.repo}")
    print(HR)
    print()

    # per-PR breakdown
    print(f"  {'PR':>5}  {'Author':<16}  {'Rev':>3}  {'Inl':>3}  "
          f"{'Desc':>4}  {'Iter':>4}  {'Input tok':>9}")
    print(f"  {'─'*5}  {'─'*16}  {'─'*3}  {'─'*3}  "
          f"{'─'*4}  {'─'*4}  {'─'*9}")
    for r in rows:
        flag = " ⚠" if r["iter"] >= 2 else "  "
        print(f"  {r['pr']:>5}  {r['author']:<16}  {r['reviews']:>3}  "
              f"{r['inline']:>3}  {r['desc']:>4}  "
              f"{r['iter']:>4}{flag}  {r['p1_input']:>9,}")

    print()
    print(f"  ⚠ = 2+ review iterations (high-signal PRs)")
    if skipped_no_reviews:
        print(f"  {skipped_no_reviews} PRs skipped — no review activity")
    print()

    print(f"  SAMPLE STATS  ({n_reviewed} PRs with reviews)")
    print(f"  Avg review comments/PR:    {avg_reviews:.1f}")
    print(f"  Avg inline comments/PR:    {avg_inline:.1f}")
    print(f"  Avg review iterations/PR:  {avg_iter:.1f}")
    print(f"  Avg input tokens/PR:       {avg_tokens:,.0f}")
    print(f"  Desc quality — "
          f"high: {desc_quality_counts['high']}  "
          f"medium: {desc_quality_counts['medium']}  "
          f"low: {desc_quality_counts['low']}")
    print()

    print(f"  TOKEN BREAKDOWN")
    print(f"  Prompt 1 — per-PR extraction:")
    print(f"    Input:                 {total_p1_input:>12,}")
    print(f"    Output (est):          {total_p1_output:>12,}")
    print(f"  Prompts 2–4 — aggregation (×{AGGREGATION_PASS_MULTIPLIER}):")
    print(f"    Input:                 {agg_input:>12,}")
    print(f"    Output (est):          {agg_output:>12,}")
    print(f"  Grand total input:       {grand_input:>12,}")
    print(f"  Grand total output:      {grand_output:>12,}")
    print()

    print(f"  COST  (Sonnet 4 — $3/M input · $15/M output)")
    print(f"  Prompt 1:              ${p1_cost:>8.4f}")
    print(f"  Aggregation passes:    ${agg_cost:>8.4f}")
    print(f"  This sample total:     ${total_cost:>8.4f}  ({n_reviewed} PRs)")
    print(f"  Per PR:                ${per_pr:>8.5f}")
    print()

    print(f"  EXTRAPOLATIONS  (based on per-PR rate of ${per_pr:.5f})")
    print(f"  {'Window':>8}   {'Est PRs':>8}   {'Cost':>8}   Notes")
    print(f"  {'─'*8}   {'─'*8}   {'─'*8}   {'─'*30}")
    windows = [
        (30,  "1 month, quiet team"),
        (60,  "2 months, recommended first run"),
        (90,  "3 months, standard window"),
        (150, "5 months, rich signal"),
        (300, "heavy repo, 6–12 months"),
    ]
    for est_prs, note in windows:
        est_cost = per_pr * est_prs
        print(f"  {est_prs:>8}   {'~'+str(est_prs):>8}   ${est_cost:>7.2f}   {note}")
    print()

    # ── warnings ──────────────────────────────────────────────────────────────
    warnings = []
    insights = []

    low_pct = desc_quality_counts["low"] / n_reviewed
    if low_pct > 0.4:
        warnings.append(
            f"{desc_quality_counts['low']}/{n_reviewed} PRs ({low_pct:.0%}) have "
            f"low-quality descriptions. Synthesis confidence will be reduced. "
            f"Consider documenting a PR template before full run."
        )

    high_iter = sum(1 for r in rows if r["iter"] >= 2)
    if high_iter:
        insights.append(
            f"{high_iter} PRs had 2+ review iterations — these are your "
            f"highest-signal PRs for pattern extraction."
        )

    if avg_tokens > 4000:
        warnings.append(
            f"Average payload is {avg_tokens:,.0f} tokens/PR (high). "
            f"Consider filtering PRs with >500 additions to reduce cost."
        )
    elif avg_tokens < 800:
        warnings.append(
            f"Average payload is {avg_tokens:,.0f} tokens/PR (low). "
            f"Reviews may be thin — synthesis signal may be limited."
        )

    if avg_reviews < 1.5:
        warnings.append(
            f"Average {avg_reviews:.1f} reviews/PR — team may be reviewing "
            f"in Slack rather than GitHub. Signal could be systematically thin."
        )

    if warnings:
        print(f"  ⚠  WARNINGS")
        for w in warnings:
            print(f"     · {w}")
        print()

    if insights:
        print(f"  ✓  INSIGHTS")
        for ins in insights:
            print(f"     · {ins}")
        print()

    print(HR)
    print()

    # ── json output ───────────────────────────────────────────────────────────
    json_path = f"tricorder-cost-probe-{args.repo.replace('/', '__')}.json"
    summary = {
        "repo":               args.repo,
        "prs_sampled":        n_reviewed,
        "skipped_no_reviews": skipped_no_reviews,
        "per_pr_cost_usd":    round(per_pr, 6),
        "sample_cost_usd":    round(total_cost, 4),
        "grand_input_tokens": grand_input,
        "grand_output_tokens": grand_output,
        "avg_tokens_per_pr":  round(avg_tokens, 0),
        "avg_reviews_per_pr": round(avg_reviews, 1),
        "avg_inline_per_pr":  round(avg_inline, 1),
        "avg_iterations":     round(avg_iter, 2),
        "desc_quality":       desc_quality_counts,
        "extrapolations_usd": {
            str(est_prs): round(per_pr * est_prs, 2)
            for est_prs, _ in windows
        },
        "warnings": warnings,
        "insights": insights,
    }
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  JSON summary → {json_path}")
    print()


if __name__ == "__main__":
    main()
