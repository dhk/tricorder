#!/usr/bin/env python3
"""
tricorder-harvest.py — pull merged PRs from GitHub into local cache

Writes to ~/.learn-from-work/cache/<owner>__<repo>/:
  harvest-manifest.json          contributor index + date range + author tenure
  repo-context.json              dbt_project.yml, .sqlfluff, PR template
  prs/{number}.json              per-PR metadata + description quality score
  reviews/{number}-reviews.json  formal review threads
  comments/{number}-comments.json  inline diff comments + has_reply flag

Incremental: re-running only fetches PRs merged after the last harvest.
Re-run with --force to re-fetch everything.

Usage:
  python tricorder-harvest.py OWNER/REPO
  python tricorder-harvest.py OWNER/REPO --since 2026-01-01
  python tricorder-harvest.py OWNER/REPO --since 2026-01-01 --limit 50
  python tricorder-harvest.py OWNER/REPO --force

Auth:
  GITHUB_TOKEN environment variable — classic PAT with public_repo scope
  (or repo scope for private repos).

  Set it:
    export GITHUB_TOKEN=ghp_your_token
    # or store in macOS keychain:
    security add-generic-password -a "$USER" -s "github-tricorder-pat" -w "ghp_..."
    # then:
    export GITHUB_TOKEN=$(security find-generic-password -a "$USER" -s "github-tricorder-pat" -w)

Requirements:
  pip install requests
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")


# ── config ────────────────────────────────────────────────────────────────────

CACHE_BASE = Path.home() / ".learn-from-work" / "cache"


# ── auth ──────────────────────────────────────────────────────────────────────

def get_github_token() -> str:
    """
    Try GITHUB_TOKEN env var first, then macOS keychain (github-tricorder-pat).
    """
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    # Try keychain
    for service in ("github-tricorder-pat", "github-fossil-pat"):
        try:
            result = subprocess.run(
                ["security", "find-generic-password", "-a", os.environ.get("USER", ""),
                 "-s", service, "-w"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass

    sys.exit(
        "\n❌  GITHUB_TOKEN not set and not found in keychain.\n\n"
        "    Create a classic PAT: https://github.com/settings/tokens\n"
        "    Scope: public_repo (for public repos) or repo (for private)\n\n"
        "    Then set it:\n"
        "      export GITHUB_TOKEN=ghp_your_token\n\n"
        "    Or store in keychain:\n"
        "      security add-generic-password -a \"$USER\" -s \"github-tricorder-pat\" "
        "-w \"ghp_...\"\n"
        "      export GITHUB_TOKEN=$(security find-generic-password -a \"$USER\" "
        "-s \"github-tricorder-pat\" -w)\n"
    )


# ── github api ────────────────────────────────────────────────────────────────

class GitHub:
    BASE = "https://api.github.com"
    RATE_FLOOR = 50  # pause when remaining requests drop below this

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def get(self, path: str, params: dict = None) -> list | dict:
        url = f"{self.BASE}{path}"
        r = self.session.get(url, params=params, timeout=20)
        self._check_rate(r)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def paginate(self, path: str, params: dict = None) -> list:
        """Fetch all pages for a list endpoint."""
        params = dict(params or {})
        params.setdefault("per_page", 100)
        results = []
        url = f"{self.BASE}{path}"
        while url:
            r = self.session.get(url, params=params, timeout=20)
            self._check_rate(r)
            r.raise_for_status()
            results.extend(r.json())
            url = r.links.get("next", {}).get("url")
            params = {}  # params already encoded in next URL
        return results

    def _check_rate(self, r):
        remaining = int(r.headers.get("X-RateLimit-Remaining", 999))
        if remaining < self.RATE_FLOOR:
            reset = int(r.headers.get("X-RateLimit-Reset", 0))
            wait = max(0, reset - int(time.time())) + 3
            print(f"\n  ⚠  Rate limit low ({remaining} remaining). "
                  f"Sleeping {wait}s…", flush=True)
            time.sleep(wait)


# ── description quality scoring ───────────────────────────────────────────────

def score_description(body: str) -> dict:
    if not body:
        return {"quality": "low", "word_count": 0, "low_confidence": True}
    wc = len(body.split())
    has_why     = any(w in body.lower() for w in
                      ["why", "because", "motivation", "context", "reason"])
    has_what    = any(w in body.lower() for w in
                      ["change", "added", "removed", "updated", "refactor", "fix"])
    has_testing = any(w in body.lower() for w in
                      ["test", "verified", "checked", "validated",
                       "dbt run", "dbt build", "dbt test", "ci"])
    score = sum([wc >= 50, has_why, has_what, has_testing])
    quality = "high" if score >= 3 else "medium" if score >= 2 else "low"
    return {
        "quality":        quality,
        "word_count":     wc,
        "low_confidence": quality == "low",
    }


# ── bot detection ─────────────────────────────────────────────────────────────

def is_bot(login: str) -> bool:
    bot_markers = ["dependabot", "github-actions", "renovate", "bot[bot]", "app/"]
    return any(m in login.lower() for m in bot_markers)


# ── repo context ──────────────────────────────────────────────────────────────

def fetch_file_content(gh: GitHub, owner: str, repo: str, path: str) -> str | None:
    """Fetch a file from the repo, decode from base64. Returns None if missing."""
    data = gh.get(f"/repos/{owner}/{repo}/contents/{path}")
    if not data or "content" not in data:
        return None
    try:
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        return None


def extract_sqlfluff_rules(content: str) -> list[str]:
    """Parse .sqlfluff and return the list of explicitly enabled/configured rules."""
    if not content:
        return []
    rules = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("rules") or line.startswith("rule_"):
            rules.append(line.split("=")[0].strip())
        if line.startswith("[sqlfluff:rules:"):
            rules.append(line.strip("[]").replace("sqlfluff:rules:", ""))
    return rules[:20]  # cap


def extract_pr_template_sections(content: str) -> list[str]:
    """Return the H2/H3 section headings from a PR template."""
    if not content:
        return []
    sections = []
    for line in content.splitlines():
        if line.startswith("## ") or line.startswith("### "):
            sections.append(line.lstrip("#").strip())
    return sections


def fetch_repo_context(gh: GitHub, owner: str, repo: str) -> dict:
    """Fetch dbt_project.yml, .sqlfluff, and PR template from the repo."""
    print("  Fetching repo context…", end=" ", flush=True)

    dbt_project  = fetch_file_content(gh, owner, repo, "dbt_project.yml")
    sqlfluff     = fetch_file_content(gh, owner, repo, ".sqlfluff")
    pr_template  = (
        fetch_file_content(gh, owner, repo, ".github/PULL_REQUEST_TEMPLATE.md")
        or fetch_file_content(gh, owner, repo, "PULL_REQUEST_TEMPLATE.md")
        or fetch_file_content(gh, owner, repo, ".github/pull_request_template.md")
    )

    flags = []
    if dbt_project: flags.append("dbt_project.yml")
    if sqlfluff:    flags.append(".sqlfluff")
    if pr_template: flags.append("PR template")
    print(f"found: {', '.join(flags) if flags else 'none'}")

    return {
        "dbt_project":            (dbt_project or "")[:3000],
        "sqlfluff":               (sqlfluff or "")[:2000],
        "pr_template":            (pr_template or "")[:2000],
        "sqlfluff_rules_lines":   extract_sqlfluff_rules(sqlfluff or ""),
        "pr_template_sections":   extract_pr_template_sections(pr_template or ""),
    }


# ── comment reply detection ───────────────────────────────────────────────────

def mark_has_reply(comments: list) -> list:
    """
    Mark inline comments that received at least one reply.
    Replies have in_reply_to_id set to the parent comment's id.
    """
    parent_ids = {c["in_reply_to_id"] for c in comments if c.get("in_reply_to_id")}
    for c in comments:
        c["has_reply"] = c["id"] in parent_ids
    return comments


# ── main harvest ──────────────────────────────────────────────────────────────

def harvest(args):
    owner, repo_name = args.repo.split("/", 1)
    repo_slug        = f"{owner}__{repo_name}"
    cache_dir        = CACHE_BASE / repo_slug

    # Create cache dirs
    for d in ("prs", "reviews", "comments"):
        (cache_dir / d).mkdir(parents=True, exist_ok=True)

    token = get_github_token()
    gh    = GitHub(token)

    print(f"\n📡  tricorder — harvest")
    print(f"    Repo:    {args.repo}")
    print(f"    Cache:   {cache_dir}")

    # ── determine since date ──────────────────────────────────────────────────
    manifest_path = cache_dir / "harvest-manifest.json"
    existing_manifest = {}

    if manifest_path.exists() and not args.force:
        existing_manifest = json.loads(manifest_path.read_text())
        last_harvest = existing_manifest.get("harvested_at", "")
        if last_harvest and not args.since:
            # Incremental: pick up from last harvest
            since_str = last_harvest[:10]
            print(f"    Mode:    incremental (since {since_str})")
        else:
            since_str = args.since
    else:
        since_str = args.since

    if args.force:
        print(f"    Mode:    force re-fetch")
    elif not since_str:
        print(f"    Mode:    full harvest (no --since)")

    if since_str:
        print(f"    Since:   {since_str}")
    if args.limit:
        print(f"    Limit:   {args.limit} PRs")
    print()

    since_dt = None
    if since_str:
        since_dt = datetime.fromisoformat(since_str).replace(tzinfo=timezone.utc)

    # ── fetch repo context ────────────────────────────────────────────────────
    ctx_path = cache_dir / "repo-context.json"
    if not ctx_path.exists() or args.force:
        repo_ctx = fetch_repo_context(gh, owner, repo_name)
        ctx_path.write_text(json.dumps(repo_ctx, indent=2))
    else:
        print("  Repo context: (cached)")

    # ── fetch PRs ─────────────────────────────────────────────────────────────
    print("  Fetching merged PRs…", flush=True)

    params = {
        "state":     "closed",
        "sort":      "updated",
        "direction": "desc",
        "per_page":  100,
    }

    prs_fetched     = 0
    prs_cached      = 0
    prs_skipped_bot = 0
    newest_date     = None
    oldest_date     = None

    # We paginate but stop early if we've gone past our since window
    url = f"/repos/{owner}/{repo_name}/pulls"
    page_params = dict(params)
    seen_numbers = set()
    done = False

    all_pr_data = []

    while url and not done:
        full_url = f"https://api.github.com{url}" if url.startswith("/") else url
        r = gh.session.get(
            f"https://api.github.com{url}" if url.startswith("/") else url,
            params=page_params, timeout=20,
        )
        gh._check_rate(r)
        r.raise_for_status()
        batch = r.json()

        for pr in batch:
            if not pr.get("merged_at"):
                continue

            merged_dt = datetime.fromisoformat(
                pr["merged_at"].replace("Z", "+00:00"))

            # Stop if we've gone past our window
            if since_dt and merged_dt < since_dt:
                done = True
                break

            if pr["number"] in seen_numbers:
                continue
            seen_numbers.add(pr["number"])

            all_pr_data.append((pr, merged_dt))

            if args.limit and len(all_pr_data) >= args.limit:
                done = True
                break

        url = r.links.get("next", {}).get("url")
        page_params = {}  # URL already has params encoded

    print(f"  Found {len(all_pr_data)} merged PRs in window.")
    print()

    # ── per-PR fetch ──────────────────────────────────────────────────────────
    all_authors = {}  # login → {first_seen, last_seen}
    total = len(all_pr_data)

    for i, (pr, merged_dt) in enumerate(sorted(all_pr_data, key=lambda x: x[1]), 1):
        num    = pr["number"]
        author = pr.get("user", {})
        login  = author.get("login", "unknown")

        # Bot filter
        if is_bot(login) or author.get("type") == "Bot":
            prs_skipped_bot += 1
            print(f"  [{i:03d}/{total}] #{num:5d}  {login:<16}  [skipped — bot]")
            continue

        merged_str = merged_dt.date().isoformat()
        title      = pr.get("title", "")[:60]

        # Track author tenure
        if login not in all_authors:
            all_authors[login] = {"first_seen": merged_str, "last_seen": merged_str}
        else:
            if merged_str < all_authors[login]["first_seen"]:
                all_authors[login]["first_seen"] = merged_str
            if merged_str > all_authors[login]["last_seen"]:
                all_authors[login]["last_seen"] = merged_str

        # Track date range
        if oldest_date is None or merged_str < oldest_date:
            oldest_date = merged_str
        if newest_date is None or merged_str > newest_date:
            newest_date = merged_str

        # Check if already cached
        pr_path  = cache_dir / "prs"      / f"{num}.json"
        rev_path = cache_dir / "reviews"  / f"{num}-reviews.json"
        com_path = cache_dir / "comments" / f"{num}-comments.json"

        if pr_path.exists() and rev_path.exists() and com_path.exists() and not args.force:
            prs_cached += 1
            print(f"  [{i:03d}/{total}] #{num:5d}  {login:<16}  (cached)")
            continue

        print(f"  [{i:03d}/{total}] #{num:5d}  {login:<16}  {title:<50}", end="", flush=True)

        # Fetch reviews
        try:
            reviews = gh.paginate(f"/repos/{owner}/{repo_name}/pulls/{num}/reviews")
        except Exception as e:
            print(f"\n    ⚠  reviews error: {e}")
            reviews = []

        # Fetch inline comments
        try:
            comments = gh.paginate(f"/repos/{owner}/{repo_name}/pulls/{num}/comments")
            comments = mark_has_reply(comments)
        except Exception as e:
            print(f"\n    ⚠  comments error: {e}")
            comments = []

        # Count review iterations (CHANGES_REQUESTED before approval)
        review_iterations = sum(
            1 for r in reviews if r.get("state") == "CHANGES_REQUESTED")

        # PR metadata to write
        pr_record = {
            "number":       num,
            "title":        pr.get("title", ""),
            "body":         pr.get("body") or "",
            "author": {
                "id":     author.get("node_id", ""),
                "login":  login,
                "name":   author.get("name", login),
                "is_bot": False,
            },
            "createdAt":          pr.get("created_at", ""),
            "mergedAt":           pr.get("merged_at", ""),
            "additions":          pr.get("additions", 0),
            "deletions":          pr.get("deletions", 0),
            "changedFiles":       pr.get("changed_files", 0),
            "description_quality": score_description(pr.get("body") or ""),
            "review_iterations":  review_iterations,
        }

        # Reviews: keep only fields synthesize needs
        review_records = [
            {
                "id":           r.get("id"),
                "state":        r.get("state", ""),
                "user":         {"login": r.get("user", {}).get("login", "unknown")},
                "body":         r.get("body") or "",
                "submitted_at": r.get("submitted_at", ""),
            }
            for r in reviews
            if not is_bot(r.get("user", {}).get("login", ""))
        ]

        # Comments: keep only fields synthesize needs
        comment_records = [
            {
                "id":             c.get("id"),
                "user":           {"login": c.get("user", {}).get("login", "unknown")},
                "path":           c.get("path", ""),
                "body":           c.get("body") or "",
                "created_at":     c.get("created_at", ""),
                "has_reply":      c.get("has_reply", False),
                "in_reply_to_id": c.get("in_reply_to_id"),
            }
            for c in comments
            if not is_bot(c.get("user", {}).get("login", ""))
        ]

        pr_path.write_text(json.dumps(pr_record, indent=2))
        rev_path.write_text(json.dumps(review_records, indent=2))
        com_path.write_text(json.dumps(comment_records, indent=2))

        prs_fetched += 1
        n_rev = len(review_records)
        n_com = len(comment_records)
        dq    = pr_record["description_quality"]["quality"]
        print(f"  {n_rev}rev  {n_com}inline  desc={dq}")

        time.sleep(0.15)  # polite rate-limit headroom

    print()

    # ── compute author tenure ─────────────────────────────────────────────────
    author_tenure = {}
    for login, dates in all_authors.items():
        first = datetime.fromisoformat(dates["first_seen"])
        last  = datetime.fromisoformat(dates["last_seen"])
        cache_days = (last - first).days + 1
        author_tenure[login] = {
            "first_seen": dates["first_seen"],
            "last_seen":  dates["last_seen"],
            "cache_days": cache_days,
        }

    # ── write manifest ────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc).isoformat()

    # Merge with existing manifest (incremental updates)
    if existing_manifest and not args.force:
        existing_tenure = existing_manifest.get("author_tenure", {})
        for login, info in existing_tenure.items():
            if login not in author_tenure:
                author_tenure[login] = info

    # Count all PRs in cache (including previously cached ones)
    pr_count = len(list((cache_dir / "prs").glob("*.json")))
    contributors = sorted(author_tenure.keys())

    manifest = {
        "repo":           args.repo,
        "harvested_at":   now,
        "since":          since_str or "",
        "date_range": {
            "from": oldest_date or (since_str or ""),
            "to":   newest_date or now[:10],
        },
        "pr_count":       pr_count,
        "contributors":   contributors,
        "author_tenure":  author_tenure,
    }

    # Merge date range with existing manifest
    if existing_manifest and not args.force:
        old_from = existing_manifest.get("date_range", {}).get("from", "")
        if old_from and (not manifest["date_range"]["from"] or
                         old_from < manifest["date_range"]["from"]):
            manifest["date_range"]["from"] = old_from

    manifest_path.write_text(json.dumps(manifest, indent=2))

    # ── summary ───────────────────────────────────────────────────────────────
    print(f"  ✓ Harvest complete")
    print()
    print(f"    PRs fetched (new):    {prs_fetched}")
    print(f"    PRs cached (skipped): {prs_cached}")
    print(f"    PRs skipped (bots):   {prs_skipped_bot}")
    print(f"    Total in cache:       {pr_count}")
    print(f"    Contributors:         {len(contributors)}")
    print(f"    Date range:           {manifest['date_range']['from']} → {manifest['date_range']['to']}")
    print(f"    Cache:                {cache_dir}")
    print()
    print(f"  Next:")
    print(f"    python tricorder-cost-probe.py {args.repo}")
    print(f"    python tricorder-synthesize.py {args.repo}")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("repo",
                    help="OWNER/REPO  e.g. cal-itp/data-infra")
    ap.add_argument("--since", default=None,
                    help="Only fetch PRs merged on or after YYYY-MM-DD. "
                         "Defaults to last harvest date (incremental) or no limit.")
    ap.add_argument("--limit", type=int, default=None,
                    help="Stop after fetching N PRs (useful for testing)")
    ap.add_argument("--force", action="store_true",
                    help="Re-fetch PRs that are already cached")
    args = ap.parse_args()

    if "/" not in args.repo:
        ap.error("Repo must be in OWNER/REPO format")

    harvest(args)


if __name__ == "__main__":
    main()
