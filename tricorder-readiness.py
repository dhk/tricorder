#!/usr/bin/env python3
"""
tricorder-readiness.py — check if a repo is a good candidate for tricorder

Runs in seconds, makes no Claude API calls, costs nothing.
Samples up to 20 recent merged PRs and checks:
  - PR volume in the target window
  - Review density (formal reviews + inline comments per PR)
  - dbt/SQL project markers (dbt_project.yml, .sqlfluff)
  - Description quality

Returns GO / CAUTION / NO-GO with specific reasons and a recommended
action for each finding.

Usage:
  tricorder ready OWNER/REPO
  tricorder ready OWNER/REPO --days 90
  tricorder ready OWNER/REPO --since 2026-01-01

Auth:
  GITHUB_TOKEN environment variable (public_repo scope for public repos).
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")


# ── config ────────────────────────────────────────────────────────────────────

SAMPLE_SIZE = 20   # PRs to inspect for review density
MIN_PRS_GO       = 30
MIN_PRS_CAUTION  = 15
MIN_REVIEWS_GO   = 1.5
MIN_REVIEWS_CAUTION = 0.5
MIN_INLINE_CAUTION  = 0.3


# ── auth ──────────────────────────────────────────────────────────────────────

def get_token() -> str:
    import subprocess
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    for svc in ("github-tricorder-pat", "github-fossil-pat"):
        try:
            r = subprocess.run(
                ["security", "find-generic-password", "-a", os.environ.get("USER", ""),
                 "-s", svc, "-w"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except Exception:
            pass
    sys.exit(
        "\n  GITHUB_TOKEN not set.\n"
        "  export GITHUB_TOKEN=ghp_...\n"
    )


# ── github ────────────────────────────────────────────────────────────────────

class GitHub:
    BASE = "https://api.github.com"

    def __init__(self, token):
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def get(self, path, params=None):
        r = self.s.get(f"{self.BASE}{path}", params=params, timeout=15)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def paginate(self, path, params=None, limit=None):
        params = dict(params or {}); params.setdefault("per_page", 100)
        results = []; url = f"{self.BASE}{path}"
        while url:
            r = self.s.get(url, params=params, timeout=15)
            r.raise_for_status()
            batch = r.json()
            results.extend(batch)
            if limit and len(results) >= limit:
                return results[:limit]
            url = r.links.get("next", {}).get("url")
            params = {}
        return results


# ── description quality (same as probe + harvest) ────────────────────────────

def score_desc(body):
    if not body:
        return "low"
    wc = len(body.split())
    has_why  = any(w in body.lower() for w in ["why", "because", "motivation", "context"])
    has_what = any(w in body.lower() for w in ["change", "added", "removed", "updated", "fix"])
    has_test = any(w in body.lower() for w in ["test", "verified", "dbt run", "dbt build", "dbt test"])
    score = sum([wc >= 50, has_why, has_what, has_test])
    return "high" if score >= 3 else "medium" if score >= 2 else "low"


# ── checks ────────────────────────────────────────────────────────────────────

def check_repo_exists(gh, owner, repo):
    data = gh.get(f"/repos/{owner}/{repo}")
    if data is None:
        return False, "Repository not found or not accessible with current token."
    return True, data


def check_dbt_markers(gh, owner, repo):
    markers = []
    for path in ("dbt_project.yml", ".sqlfluff", "profiles.yml"):
        if gh.get(f"/repos/{owner}/{repo}/contents/{path}") is not None:
            markers.append(path)
    return markers


def check_pr_template(gh, owner, repo):
    for path in (".github/PULL_REQUEST_TEMPLATE.md", "PULL_REQUEST_TEMPLATE.md",
                 ".github/pull_request_template.md"):
        if gh.get(f"/repos/{owner}/{repo}/contents/{path}") is not None:
            return True
    return False


def fetch_recent_prs(gh, owner, repo, since_dt, limit):
    prs = []
    params = {"state": "closed", "sort": "updated", "direction": "desc", "per_page": 100}
    url = f"/repos/{owner}/{repo}/pulls"
    page_params = dict(params)
    done = False

    while url and not done:
        full = f"https://api.github.com{url}" if url.startswith("/") else url
        r = gh.s.get(full, params=page_params, timeout=15)
        r.raise_for_status()
        for pr in r.json():
            if not pr.get("merged_at"):
                continue
            merged = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
            if since_dt and merged < since_dt:
                done = True
                break
            login = pr.get("user", {}).get("login", "")
            if "dependabot" in login.lower() or "bot" in login.lower():
                continue
            prs.append(pr)
            if len(prs) >= limit:
                done = True
                break
        url = r.links.get("next", {}).get("url")
        page_params = {}

    return prs


def sample_review_density(gh, owner, repo, prs, sample=SAMPLE_SIZE):
    sampled = prs[:sample]
    total_reviews = 0
    total_inline  = 0
    total_iters   = 0
    desc_quality  = {"high": 0, "medium": 0, "low": 0}

    for pr in sampled:
        num = pr["number"]
        try:
            reviews = gh.get(f"/repos/{owner}/{repo}/pulls/{num}/reviews") or []
            comments = gh.get(f"/repos/{owner}/{repo}/pulls/{num}/comments") or []
        except Exception:
            reviews = []; comments = []

        total_reviews += len(reviews)
        total_inline  += len(comments)
        total_iters   += sum(1 for r in reviews if r.get("state") == "CHANGES_REQUESTED")
        dq = score_desc(pr.get("body") or "")
        desc_quality[dq] += 1
        time.sleep(0.1)

    n = len(sampled)
    return {
        "n": n,
        "avg_reviews": total_reviews / n if n else 0,
        "avg_inline":  total_inline  / n if n else 0,
        "avg_iters":   total_iters   / n if n else 0,
        "desc_quality": desc_quality,
    }


# ── verdict ───────────────────────────────────────────────────────────────────

GO      = "GO"
CAUTION = "CAUTION"
NO_GO   = "NO-GO"

GRN = "\033[32m"; YLW = "\033[33m"; RED = "\033[31m"
BOLD = "\033[1m"; DIM = "\033[2m"; RST = "\033[0m"

def verdict_color(v):
    return {GO: GRN, CAUTION: YLW, NO_GO: RED}.get(v, "")


def print_finding(verdict, label, detail, action=None):
    vc = verdict_color(verdict)
    sym = {"GO": "✓", "CAUTION": "⚠", "NO-GO": "✗"}.get(verdict, "·")
    print(f"  {vc}{sym}{RST}  {BOLD}{label}{RST}")
    print(f"     {DIM}{detail}{RST}")
    if action:
        print(f"     → {action}")
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", help="OWNER/REPO")
    ap.add_argument("--days", type=int, default=90,
                    help="Look-back window in days (default: 90)")
    ap.add_argument("--since", default=None,
                    help="Start date YYYY-MM-DD (overrides --days)")
    args = ap.parse_args()

    if "/" not in args.repo:
        ap.error("Repo must be OWNER/REPO")

    owner, repo_name = args.repo.split("/", 1)
    token = get_token()
    gh    = GitHub(token)

    since_dt = None
    if args.since:
        since_dt = datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc)
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(days=args.days)

    since_str = since_dt.date().isoformat()

    print()
    print(f"{BOLD}tricorder — readiness check{RST}")
    print(f"  {DIM}Repo:   {args.repo}{RST}")
    print(f"  {DIM}Window: since {since_str} ({args.days} days){RST}")
    print()

    # ── 1. repo exists ────────────────────────────────────────────────────────
    print(f"  Checking repo access…", end=" ", flush=True)
    ok, repo_data = check_repo_exists(gh, owner, repo_name)
    if not ok:
        print()
        print(f"  {RED}✗  {repo_data}{RST}")
        sys.exit(1)
    is_private = repo_data.get("private", False)
    print("✓")

    # ── 2. dbt markers ────────────────────────────────────────────────────────
    print(f"  Checking dbt/SQL markers…", end=" ", flush=True)
    markers = check_dbt_markers(gh, owner, repo_name)
    has_template = check_pr_template(gh, owner, repo_name)
    print(f"found: {', '.join(markers) if markers else 'none'}")

    # ── 3. PR volume ──────────────────────────────────────────────────────────
    print(f"  Fetching merged PRs since {since_str}…", end=" ", flush=True)
    prs = fetch_recent_prs(gh, owner, repo_name, since_dt, limit=200)
    print(f"{len(prs)} found")

    # ── 4. review density ─────────────────────────────────────────────────────
    if prs:
        n_sample = min(SAMPLE_SIZE, len(prs))
        print(f"  Sampling review density ({n_sample} PRs)…", end=" ", flush=True)
        density = sample_review_density(gh, owner, repo_name, prs, n_sample)
        print("done")
    else:
        density = {"n": 0, "avg_reviews": 0, "avg_inline": 0, "avg_iters": 0,
                   "desc_quality": {"high": 0, "medium": 0, "low": 0}}

    # ── verdicts ──────────────────────────────────────────────────────────────
    print()
    hr = "  " + "─" * 62
    print(hr)
    print(f"  {BOLD}READINESS REPORT — {args.repo}{RST}")
    print(hr)
    print()

    findings = []

    # PR volume
    n_prs = len(prs)
    if n_prs >= MIN_PRS_GO:
        v = GO
        detail = f"{n_prs} merged PRs in the window. Strong sample size."
        action = None
    elif n_prs >= MIN_PRS_CAUTION:
        v = CAUTION
        detail = f"{n_prs} merged PRs — below the 30-PR threshold for confident findings."
        action = "Widen the window (--days 180) or accept that profiles will be thinner."
    else:
        v = NO_GO
        detail = f"Only {n_prs} merged PRs in {args.days} days. Tricorder needs 30+ to produce reliable findings."
        action = "Wait until the repo has more merge history, or try a longer window."
    print_finding(v, "PR volume", detail, action)
    findings.append(v)

    # Review density — formal reviews
    avg_rev = density["avg_reviews"]
    if avg_rev >= MIN_REVIEWS_GO:
        v = GO
        detail = f"{avg_rev:.1f} formal reviews/PR average. Good signal."
        action = None
    elif avg_rev >= MIN_REVIEWS_CAUTION:
        v = CAUTION
        detail = f"{avg_rev:.1f} formal reviews/PR — reviewers are engaging but not consistently."
        action = "Findings will be valid but some reviewer fingerprints may be thin."
    else:
        v = NO_GO
        detail = f"{avg_rev:.1f} formal reviews/PR. PRs appear to be merging without review."
        action = "If review happens in Slack or verbally, tricorder will miss it. Signal will be very thin."
    print_finding(v, "Review density", detail, action)
    findings.append(v)

    # Inline comments
    avg_inl = density["avg_inline"]
    if avg_inl >= MIN_INLINE_CAUTION:
        v = GO
        detail = f"{avg_inl:.1f} inline diff comments/PR. Reviewers are leaving specific, quoted feedback."
        action = None
    else:
        v = CAUTION
        detail = f"{avg_inl:.1f} inline comments/PR. Reviewers may be approving at PR level without inline discussion."
        action = "Phase 1 extraction still works but evidence quotes will be sparse."
    print_finding(v, "Inline review comments", detail, action)
    findings.append(v)

    # dbt markers
    if "dbt_project.yml" in markers:
        v = GO
        detail = f"dbt_project.yml found. Category taxonomy and standard citations are calibrated for this."
        if ".sqlfluff" in markers:
            detail += " SQLFluff config also found — synthesis will avoid recommending rules already enforced."
    elif markers:
        v = CAUTION
        detail = f"Found: {', '.join(markers)} — but no dbt_project.yml. May be a SQL/dbt repo without the root config."
        action = "Synthesis will still run but dbt-specific findings may be less precise."
    else:
        v = CAUTION
        detail = "No dbt_project.yml or .sqlfluff found. Tricorder is scoped to dbt/SQL analytics repos."
        action = "Output will be more generic. Standard citations (dbt-project-evaluator, Kimball) will still apply."
    print_finding(v, "dbt/SQL markers", detail, action)
    findings.append(v)

    # Description quality
    dq = density["desc_quality"]
    n_dq = sum(dq.values()) or 1
    low_pct = dq["low"] / n_dq
    if low_pct <= 0.2:
        v = GO
        detail = f"Description quality — high: {dq['high']}  medium: {dq['medium']}  low: {dq['low']}. Synthesis confidence will be high."
        action = None
    elif low_pct <= 0.5:
        v = CAUTION
        detail = f"Description quality — high: {dq['high']}  medium: {dq['medium']}  low: {dq['low']}. {dq['low']} PRs have thin descriptions."
        action = "Consider adding a PR template before your next synthesis run (tricorder will flag low-confidence results)."
    else:
        v = CAUTION
        detail = f"{int(low_pct*100)}% of PRs have low-quality descriptions. Claude will mark many extractions as tentative."
        action = "Add a PR template with Why / What / How-tested sections. Run probe again after a month."
    print_finding(v, "PR description quality", detail, action)
    findings.append(v)

    # PR template
    if has_template:
        print_finding(GO, "PR template", "PR template found. Structured descriptions help synthesis accuracy.", None)
    else:
        print_finding(CAUTION, "PR template", "No PR template found.", "Add one to improve description quality over time.")
    findings.append(GO if has_template else CAUTION)

    # ── overall verdict ───────────────────────────────────────────────────────
    print(hr)
    n_no_go   = findings.count(NO_GO)
    n_caution = findings.count(CAUTION)

    if n_no_go >= 1:
        overall = NO_GO
        summary = "One or more hard blockers found. Address them before running synthesis."
    elif n_caution >= 3:
        overall = CAUTION
        summary = "Several cautions — synthesis will work but findings may be thinner than ideal."
    else:
        overall = GO
        summary = "Repo looks like a strong candidate. Proceed with confidence."

    vc = verdict_color(overall)
    print()
    print(f"  {BOLD}{vc}{overall}{RST}  —  {summary}")
    print()

    if overall in (GO, CAUTION):
        print(f"  {DIM}Next steps:{RST}")
        print(f"    tricorder probe      {args.repo} --limit 20   # confirm cost")
        print(f"    tricorder harvest    {args.repo} --since {since_str}")
        print(f"    tricorder synthesize {args.repo}")
    print()


if __name__ == "__main__":
    main()
