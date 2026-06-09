"""
tricorder analyze — Level 2

Fetches merged PRs and review data from GitHub (read-only).
Writes three artifacts to .tricorder/:
  review-observations.json   per-PR metadata + signals
  review-patterns.json       aggregate patterns across all PRs
  expertise-map.json         per-reviewer and per-author activity

Requires: GITHUB_TOKEN env var, or `gh` CLI authenticated, or macOS keychain.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def _get_token() -> str:
    # 1. Env var
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    # 2. gh CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except FileNotFoundError:
        pass  # gh not installed
    except Exception:
        pass

    # 3. macOS keychain
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

    print("No GitHub token found.", file=sys.stderr)
    print("", file=sys.stderr)
    print("Provide one via:", file=sys.stderr)
    print("  export GITHUB_TOKEN=ghp_...", file=sys.stderr)
    print("  gh auth login   (then re-run)", file=sys.stderr)
    print("", file=sys.stderr)
    print("Token needs: public_repo scope (or repo for private repos)", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# GitHub client
# ---------------------------------------------------------------------------

BOT_MARKERS = {"dependabot", "github-actions", "renovate", "[bot]", "app/"}

AI_REVIEWER_MARKERS = {"copilot", "gemini", "coderabbit", "deepsource", "codeclimate", "[bot]"}


def _is_bot(login: str) -> bool:
    low = login.lower()
    return any(m in low for m in BOT_MARKERS)


def _is_ai_reviewer(login: str) -> bool:
    low = login.lower()
    return any(m in low for m in AI_REVIEWER_MARKERS)


def _load_config(out_dir: Path) -> dict:
    """Load .tricorder/config.yml if present."""
    try:
        import yaml  # type: ignore
        config_path = out_dir / "config.yml"
        if config_path.exists():
            return yaml.safe_load(config_path.read_text()) or {}
    except ImportError:
        pass
    return {}


def _build_reviewer_filter(config: dict, cli_deny: list[str], cli_allow: list[str]):
    """Return (deny_set, allow_set) — both lowercase logins. Empty allow_set = no restriction."""
    deny = set(m.lower() for m in (config.get("reviewer_deny", []) or []))
    deny.update(m.lower() for m in cli_deny)
    # Always deny AI reviewers (default deny list)
    for login in list(deny) + []:
        pass
    default_ai = {m for m in AI_REVIEWER_MARKERS}
    # We track AI reviewers separately; the deny set here is for explicit human deny
    allow = set(m.lower() for m in (config.get("reviewer_allow", []) or []))
    allow.update(m.lower() for m in cli_allow)
    return deny, allow


def _reviewer_allowed(login: str, deny: set, allow: set, deny_ai: bool = True) -> bool:
    low = login.lower()
    if deny_ai and _is_ai_reviewer(low):
        return False
    if low in deny:
        return False
    if allow and low not in allow:
        return False
    return True


class GitHub:
    BASE = "https://api.github.com"
    RATE_FLOOR = 50

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def get(self, path: str, params: dict | None = None) -> Any:
        r = self.session.get(f"{self.BASE}{path}", params=params, timeout=20)
        self._check_rate(r)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def paginate(self, path: str, params: dict | None = None) -> list:
        params = dict(params or {})
        params.setdefault("per_page", 100)
        results = []
        url: str | None = f"{self.BASE}{path}"
        page_params = params
        while url:
            r = self.session.get(url, params=page_params, timeout=20)
            self._check_rate(r)
            r.raise_for_status()
            results.extend(r.json())
            url = r.links.get("next", {}).get("url")
            page_params = {}
        return results

    def _check_rate(self, r: requests.Response) -> None:
        remaining = int(r.headers.get("X-RateLimit-Remaining", 9999))
        reset_at = int(r.headers.get("X-RateLimit-Reset", 0))
        if remaining < self.RATE_FLOOR:
            wait = max(0, reset_at - time.time()) + 5
            print(f"\n  Rate limit low ({remaining} remaining). Waiting {wait:.0f}s …")
            time.sleep(wait)


# ---------------------------------------------------------------------------
# Repo context (fetched from GitHub, not local fs)
# ---------------------------------------------------------------------------

def _fetch_file(gh: GitHub, owner: str, repo: str, path: str) -> str | None:
    data = gh.get(f"/repos/{owner}/{repo}/contents/{path}")
    if not data or "content" not in data:
        return None
    try:
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    except Exception:
        return None


def _pr_template_sections(content: str) -> list[str]:
    return [
        line.lstrip("#").strip()
        for line in content.splitlines()
        if line.startswith("## ") or line.startswith("### ")
    ]


def _fetch_repo_context(gh: GitHub, owner: str, repo: str) -> dict:
    print("  Fetching repo context …", end=" ", flush=True)
    dbt = _fetch_file(gh, owner, repo, "dbt_project.yml")
    sf = _fetch_file(gh, owner, repo, ".sqlfluff")
    tpl = (
        _fetch_file(gh, owner, repo, ".github/PULL_REQUEST_TEMPLATE.md")
        or _fetch_file(gh, owner, repo, "PULL_REQUEST_TEMPLATE.md")
        or _fetch_file(gh, owner, repo, ".github/pull_request_template.md")
    )
    found = [name for name, val in [("dbt_project.yml", dbt), (".sqlfluff", sf), ("PR template", tpl)] if val]
    print(f"found: {', '.join(found) or 'none'}")
    return {
        "dbt_project": (dbt or "")[:3000],
        "sqlfluff": (sf or "")[:2000],
        "pr_template": (tpl or "")[:2000],
        "pr_template_sections": _pr_template_sections(tpl or ""),
    }


# ---------------------------------------------------------------------------
# Per-PR signals
# ---------------------------------------------------------------------------

def _score_description(body: str) -> dict:
    if not body:
        return {"quality": "low", "word_count": 0}
    wc = len(body.split())
    has_why = any(w in body.lower() for w in ["why", "because", "motivation", "context", "reason"])
    has_what = any(w in body.lower() for w in ["change", "added", "removed", "updated", "refactor", "fix"])
    has_testing = any(w in body.lower() for w in
                      ["test", "verified", "checked", "validated", "dbt run", "dbt build", "dbt test", "ci"])
    score = sum([wc >= 50, has_why, has_what, has_testing])
    quality = "high" if score >= 3 else "medium" if score >= 2 else "low"
    return {"quality": quality, "word_count": wc}


def _file_type_tags(paths: list[str]) -> list[str]:
    tags = set()
    for p in paths:
        ext = Path(p).suffix.lower()
        if ext == ".sql":
            tags.add("sql")
        elif ext in (".py",):
            tags.add("python")
        elif ext in (".yml", ".yaml"):
            tags.add("yaml")
        elif ext in (".md",):
            tags.add("docs")
        elif ext in (".json",):
            tags.add("json")
        elif ext in (".js", ".ts", ".tsx", ".jsx"):
            tags.add("frontend")
        # directory-based tags
        parts = Path(p).parts
        if parts:
            top = parts[0]
            if top in ("models", "macros", "tests", "seeds", "snapshots", "analyses"):
                tags.add(f"dbt:{top}")
    return sorted(tags)


def _mark_has_reply(comments: list) -> list:
    parent_ids = {c["in_reply_to_id"] for c in comments if c.get("in_reply_to_id")}
    for c in comments:
        c["has_reply"] = c["id"] in parent_ids
    return comments


# ---------------------------------------------------------------------------
# Aggregate artifact builders
# ---------------------------------------------------------------------------

def _build_observations(pr_records: list[dict]) -> dict:
    """Consolidated view of all per-PR observations."""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tricorder_level": 2,
        "pr_count": len(pr_records),
        "observations": pr_records,
    }


def _build_patterns(pr_records: list[dict], repo_ctx: dict) -> dict:
    """Aggregate patterns across all PRs — no LLM, just stats."""
    desc_dist: dict[str, int] = defaultdict(int)
    iter_counts: list[int] = []
    file_tags: dict[str, int] = defaultdict(int)
    has_reply_count = 0
    total_inline = 0
    prs_with_review = 0

    for pr in pr_records:
        desc_dist[pr["description_quality"]["quality"]] += 1
        iters = pr["review_iterations"]
        iter_counts.append(iters)
        if iters > 0:
            prs_with_review += 1
        for tag in pr.get("file_type_tags", []):
            file_tags[tag] += 1
        for c in pr.get("inline_comments", []):
            total_inline += 1
            if c.get("has_reply"):
                has_reply_count += 1

    avg_iters = sum(iter_counts) / len(iter_counts) if iter_counts else 0
    max_iters = max(iter_counts) if iter_counts else 0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tricorder_level": 2,
        "pr_count": len(pr_records),
        "description_quality": dict(desc_dist),
        "review_iterations": {
            "average": round(avg_iters, 2),
            "max": max_iters,
            "prs_with_changes_requested": prs_with_review,
        },
        "inline_comments": {
            "total": total_inline,
            "with_reply": has_reply_count,
            "reply_rate": round(has_reply_count / total_inline, 2) if total_inline else 0,
        },
        "file_type_distribution": dict(sorted(file_tags.items(), key=lambda x: x[1], reverse=True)),
        "repo_context": {
            "has_dbt_project": bool(repo_ctx.get("dbt_project")),
            "has_sqlfluff": bool(repo_ctx.get("sqlfluff")),
            "pr_template_sections": repo_ctx.get("pr_template_sections", []),
        },
    }


def _build_expertise_map(pr_records: list[dict]) -> dict:
    """Per-reviewer and per-author activity."""
    reviewers: dict[str, dict] = {}
    authors: dict[str, dict] = {}

    for pr in pr_records:
        author = pr["author"]
        if author not in authors:
            authors[author] = {"pr_count": 0, "total_inline_received": 0,
                               "review_iterations": [], "file_types": defaultdict(int)}
        authors[author]["pr_count"] += 1
        authors[author]["review_iterations"].append(pr["review_iterations"])

        for c in pr.get("inline_comments", []):
            reviewer = c["reviewer"]
            if reviewer == author:
                continue
            authors[author]["total_inline_received"] += 1
            for tag in pr.get("file_type_tags", []):
                authors[author]["file_types"][tag] += 1

            if reviewer not in reviewers:
                reviewers[reviewer] = {
                    "comment_count": 0, "prs_reviewed": set(),
                    "authors_reviewed": set(), "file_types": defaultdict(int),
                    "reply_rate": {"with_reply": 0, "total": 0},
                }
            reviewers[reviewer]["comment_count"] += 1
            reviewers[reviewer]["prs_reviewed"].add(pr["number"])
            reviewers[reviewer]["authors_reviewed"].add(author)
            reviewers[reviewer]["reply_rate"]["total"] += 1
            if c.get("has_reply"):
                reviewers[reviewer]["reply_rate"]["with_reply"] += 1
            for tag in pr.get("file_type_tags", []):
                reviewers[reviewer]["file_types"][tag] += 1

        for r in pr.get("reviews", []):
            reviewer = r["reviewer"]
            if reviewer == author:
                continue
            if reviewer not in reviewers:
                reviewers[reviewer] = {
                    "comment_count": 0, "prs_reviewed": set(),
                    "authors_reviewed": set(), "file_types": defaultdict(int),
                    "reply_rate": {"with_reply": 0, "total": 0},
                }
            reviewers[reviewer]["prs_reviewed"].add(pr["number"])
            reviewers[reviewer]["authors_reviewed"].add(author)

    # Serialize
    reviewer_list = []
    for login, rv in sorted(reviewers.items(), key=lambda x: x[1]["comment_count"], reverse=True):
        rr = rv["reply_rate"]
        reviewer_list.append({
            "login": login,
            "comment_count": rv["comment_count"],
            "prs_reviewed": len(rv["prs_reviewed"]),
            "authors_reviewed": len(rv["authors_reviewed"]),
            "reply_rate": round(rr["with_reply"] / rr["total"], 2) if rr["total"] else 0,
            "top_file_types": dict(sorted(rv["file_types"].items(), key=lambda x: x[1], reverse=True)[:5]),
        })

    author_list = []
    for login, av in sorted(authors.items(), key=lambda x: x[1]["pr_count"], reverse=True):
        iters = av["review_iterations"]
        author_list.append({
            "login": login,
            "pr_count": av["pr_count"],
            "avg_review_iterations": round(sum(iters) / len(iters), 2) if iters else 0,
            "total_inline_received": av["total_inline_received"],
            "top_file_types": dict(sorted(av["file_types"].items(), key=lambda x: x[1], reverse=True)[:5]),
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tricorder_level": 2,
        "reviewer_count": len(reviewer_list),
        "author_count": len(author_list),
        "reviewers": reviewer_list,
        "authors": author_list,
    }


# ---------------------------------------------------------------------------
# Status block
# ---------------------------------------------------------------------------

def _print_status(repo: str, out_dir: Path, observations: dict, patterns: dict, expertise: dict) -> None:
    n_prs = observations["pr_count"]
    desc = patterns["description_quality"]
    inline = patterns["inline_comments"]
    n_reviewers = expertise["reviewer_count"]

    print()
    print("Tricorder — Review Analysis")
    print()
    print("Access used")
    print(f"  ✓ Pull requests (read)    github.com/{repo}")
    print( "  ✓ Review comments (read)")
    print( "  — No write operations performed")
    print( "  — Repository contents remain local")
    print()
    print("Completed")
    print(f"  ✓ Review Observations  → {out_dir}/review-observations.json")
    print(f"  ✓ Review Patterns      → {out_dir}/review-patterns.json")
    print(f"  ✓ Expertise Map        → {out_dir}/expertise-map.json")
    print()
    print("Findings")
    print(f"  PRs analyzed:      {n_prs}")
    print(f"  Reviewers active:  {n_reviewers}")
    print(f"  Description quality:  high={desc.get('high',0)}  medium={desc.get('medium',0)}  low={desc.get('low',0)}")
    print(f"  Inline comments:   {inline['total']}  ({inline['reply_rate']*100:.0f}% received replies)")
    print(f"  Avg review iters:  {patterns['review_iterations']['average']}")
    print()
    print("Not yet unlocked")
    print("  ○ Organizational Learnings  →  tricorder learn")
    print("  ○ Interpretation            →  tricorder interpret")
    print("  ○ Improvement Plan          →  tricorder improve")
    print()
    print("Next")
    print(f"  tricorder learn {repo}  # requires LLM API key")
    print()


# ---------------------------------------------------------------------------
# Repo inference
# ---------------------------------------------------------------------------

def _infer_repo_from_remote() -> str | None:
    """Parse OWNER/REPO from the git remote URL of the current directory."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        # SSH:   git@github.com:owner/repo.git
        # HTTPS: https://github.com/owner/repo.git
        for prefix in ("git@github.com:", "https://github.com/", "http://github.com/"):
            if url.startswith(prefix):
                slug = url[len(prefix):].removesuffix(".git")
                if "/" in slug:
                    return slug
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(args: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="tricorder analyze",
        description="Level 2: fetch PR review data from GitHub. Requires GITHUB_TOKEN or gh CLI auth.",
    )
    parser.add_argument("repo", nargs="?", default=None,
                        help="OWNER/REPO  e.g. cal-itp/data-infra (default: inferred from git remote)")
    parser.add_argument("--since", default=None, metavar="YYYY-MM-DD",
                        help="Only fetch PRs merged on or after this date. Defaults to last run (incremental).")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="Stop after N PRs (useful for testing)")
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch all PRs, ignoring cache")
    parser.add_argument("--out", default=None, metavar="DIR",
                        help="Write artifacts to DIR (default: .tricorder/ in current directory)")
    parser.add_argument("--deny", default=None, metavar="LOGIN,...",
                        help="Comma-separated reviewer logins to exclude (merged with config.yml deny list). "
                             "AI reviewers (copilot, coderabbit, etc.) are always excluded by default.")
    parser.add_argument("--allow", default=None, metavar="LOGIN,...",
                        help="Comma-separated reviewer logins to include exclusively.")

    parsed = parser.parse_args(args)

    repo_slug = parsed.repo
    if not repo_slug:
        repo_slug = _infer_repo_from_remote()
        if not repo_slug:
            print("Could not infer repository from git remote.", file=sys.stderr)
            print("Run from inside a GitHub repository, or pass OWNER/REPO explicitly.", file=sys.stderr)
            return 1
        try:
            answer = input(f"Analyze {repo_slug}? [Y/n] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if answer and answer not in ("y", "yes"):
            print("Aborted.")
            return 0

    if "/" not in repo_slug:
        print("Repo must be in OWNER/REPO format, e.g. cal-itp/data-infra", file=sys.stderr)
        return 1

    owner, repo_name = repo_slug.split("/", 1)

    # Resolve output dir — per-repo subdir inside .tricorder/
    from tricorder.config import load_config as _load_tri_config, repo_dir as _repo_dir, get as _cfg_get
    tri_base = Path.cwd() / ".tricorder"
    if parsed.out:
        out_dir = Path(parsed.out).expanduser().resolve()
    else:
        out_dir = _repo_dir(tri_base, repo_slug)
    raw_dir = out_dir / ".raw"  # internal cache for per-PR files
    for d in (raw_dir / "prs", raw_dir / "reviews", raw_dir / "comments"):
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"Cannot create output directory {d}: {e}", file=sys.stderr)
            return 1

    # Load config and build reviewer filter
    tri_config = _load_tri_config(tri_base)
    config = _load_config(out_dir)
    # Merge top-level reviewer_deny/allow from tricorder config
    if not config.get("reviewer_deny") and tri_config.get("reviewer_deny"):
        config["reviewer_deny"] = tri_config["reviewer_deny"]
    if not config.get("reviewer_allow") and tri_config.get("reviewer_allow"):
        config["reviewer_allow"] = tri_config["reviewer_allow"]
    cli_deny = [s.strip() for s in (parsed.deny or "").split(",") if s.strip()]
    cli_allow = [s.strip() for s in (parsed.allow or "").split(",") if s.strip()]
    deny_set, allow_set = _build_reviewer_filter(config, cli_deny, cli_allow)

    token = _get_token()
    gh = GitHub(token)

    print(f"\ntricorder analyze — {repo_slug}")
    print(f"  Output:  {out_dir}")

    # Determine since date (incremental)
    manifest_path = raw_dir / "manifest.json"
    existing_manifest: dict = {}
    if manifest_path.exists() and not parsed.force:
        existing_manifest = json.loads(manifest_path.read_text())

    since_str = parsed.since
    if not since_str and existing_manifest and not parsed.force:
        since_str = existing_manifest.get("harvested_at", "")[:10]
        if since_str:
            print(f"  Mode:    incremental (since {since_str})")
    if parsed.force:
        print(f"  Mode:    force re-fetch")
    elif not since_str:
        print(f"  Mode:    full fetch (no --since)")
    if since_str:
        print(f"  Since:   {since_str}")
    if parsed.limit:
        print(f"  Limit:   {parsed.limit} PRs")
    if deny_set:
        print(f"  Deny:    {', '.join(sorted(deny_set))}")
    if allow_set:
        print(f"  Allow:   {', '.join(sorted(allow_set))}")
    print("  AI reviewers: excluded by default (copilot, coderabbit, gemini, deepsource, codeclimate)")
    print()

    since_dt = None
    if since_str:
        since_dt = datetime.fromisoformat(since_str).replace(tzinfo=timezone.utc)

    # Repo context
    ctx_path = raw_dir / "repo-context.json"
    if not ctx_path.exists() or parsed.force:
        repo_ctx = _fetch_repo_context(gh, owner, repo_name)
        ctx_path.write_text(json.dumps(repo_ctx, indent=2))
    else:
        print("  Repo context: (cached)")
        repo_ctx = json.loads(ctx_path.read_text())

    # Fetch PRs
    print("  Fetching merged PRs …", flush=True)
    params = {"state": "closed", "sort": "updated", "direction": "desc", "per_page": 100}
    url: str | None = f"/repos/{owner}/{repo_name}/pulls"
    page_params = dict(params)
    all_pr_data: list[tuple[dict, datetime]] = []
    seen: set[int] = set()
    done = False

    while url and not done:
        full = f"{gh.BASE}{url}" if url.startswith("/") else url
        r = gh.session.get(full, params=page_params, timeout=20)
        gh._check_rate(r)
        r.raise_for_status()
        batch = r.json()

        for pr in batch:
            if not pr.get("merged_at"):
                continue
            merged_dt = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
            if since_dt and merged_dt < since_dt:
                done = True
                break
            if pr["number"] in seen:
                continue
            seen.add(pr["number"])
            all_pr_data.append((pr, merged_dt))
            if parsed.limit and len(all_pr_data) >= parsed.limit:
                done = True
                break

        url = r.links.get("next", {}).get("url")
        page_params = {}

    print(f"  Found {len(all_pr_data)} merged PRs in window.")
    print()

    # Per-PR fetch
    total = len(all_pr_data)
    fetched = 0
    cached = 0
    skipped_bot = 0
    author_dates: dict[str, dict] = {}

    for i, (pr, merged_dt) in enumerate(sorted(all_pr_data, key=lambda x: x[1]), 1):
        num = pr["number"]
        author_info = pr.get("user", {})
        login = author_info.get("login", "unknown")

        if _is_bot(login) or author_info.get("type") == "Bot":
            skipped_bot += 1
            print(f"  [{i:03d}/{total}] #{num:5d}  {login:<20}  [bot — skipped]")
            continue

        merged_str = merged_dt.date().isoformat()
        if login not in author_dates:
            author_dates[login] = {"first_seen": merged_str, "last_seen": merged_str}
        else:
            if merged_str < author_dates[login]["first_seen"]:
                author_dates[login]["first_seen"] = merged_str
            if merged_str > author_dates[login]["last_seen"]:
                author_dates[login]["last_seen"] = merged_str

        pr_path = raw_dir / "prs" / f"{num}.json"
        rev_path = raw_dir / "reviews" / f"{num}.json"
        com_path = raw_dir / "comments" / f"{num}.json"

        if pr_path.exists() and rev_path.exists() and com_path.exists() and not parsed.force:
            cached += 1
            print(f"  [{i:03d}/{total}] #{num:5d}  {login:<20}  (cached)")
            continue

        print(f"  [{i:03d}/{total}] #{num:5d}  {login:<20}  {pr.get('title','')[:45]:<45}", end="", flush=True)

        try:
            reviews_raw = gh.paginate(f"/repos/{owner}/{repo_name}/pulls/{num}/reviews")
        except Exception as e:
            print(f"\n    warning: reviews error: {e}")
            reviews_raw = []

        try:
            comments_raw = gh.paginate(f"/repos/{owner}/{repo_name}/pulls/{num}/comments")
            comments_raw = _mark_has_reply(comments_raw)
        except Exception as e:
            print(f"\n    warning: comments error: {e}")
            comments_raw = []

        review_iterations = sum(1 for r in reviews_raw if r.get("state") == "CHANGES_REQUESTED")

        # File paths touched (from comments)
        touched_paths = list({c["path"] for c in comments_raw if c.get("path")})

        pr_record = {
            "number": num,
            "title": pr.get("title", ""),
            "body": pr.get("body") or "",
            "author": login,
            "merged_at": pr.get("merged_at", ""),
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
            "changed_files": pr.get("changed_files", 0),
            "description_quality": _score_description(pr.get("body") or ""),
            "review_iterations": review_iterations,
            "file_type_tags": _file_type_tags(touched_paths),
            "reviews": [
                {
                    "reviewer": r.get("user", {}).get("login", "unknown"),
                    "state": r.get("state", ""),
                    "body": (r.get("body") or "")[:500],
                    "submitted_at": r.get("submitted_at", ""),
                    "is_ai": _is_ai_reviewer(r.get("user", {}).get("login", "")),
                }
                for r in reviews_raw
                if not _is_bot(r.get("user", {}).get("login", ""))
                and _reviewer_allowed(r.get("user", {}).get("login", ""), deny_set, allow_set)
            ],
            "inline_comments": [
                {
                    "id": c.get("id"),
                    "reviewer": c.get("user", {}).get("login", "unknown"),
                    "path": c.get("path", ""),
                    "body": (c.get("body") or "")[:500],
                    "has_reply": c.get("has_reply", False),
                    "created_at": c.get("created_at", ""),
                    "is_ai": _is_ai_reviewer(c.get("user", {}).get("login", "")),
                }
                for c in comments_raw
                if not _is_bot(c.get("user", {}).get("login", ""))
                and _reviewer_allowed(c.get("user", {}).get("login", ""), deny_set, allow_set)
            ],
        }

        pr_path.write_text(json.dumps(pr_record, indent=2))
        rev_path.write_text(json.dumps(pr_record["reviews"], indent=2))
        com_path.write_text(json.dumps(pr_record["inline_comments"], indent=2))

        fetched += 1
        dq = pr_record["description_quality"]["quality"]
        n_rev = len(pr_record["reviews"])
        n_com = len(pr_record["inline_comments"])
        print(f"  {n_rev}rev {n_com:3d}inline desc={dq}")
        time.sleep(0.1)

    print()

    # Compute author tenure
    if existing_manifest and not parsed.force:
        for login, info in existing_manifest.get("author_tenure", {}).items():
            if login not in author_dates:
                author_dates[login] = info

    author_tenure = {}
    for login, dates in author_dates.items():
        first = datetime.fromisoformat(dates["first_seen"])
        last = datetime.fromisoformat(dates["last_seen"])
        author_tenure[login] = {
            "first_seen": dates["first_seen"],
            "last_seen": dates["last_seen"],
            "cache_days": (last - first).days + 1,
        }

    # Update manifest
    pr_count = len(list((raw_dir / "prs").glob("*.json")))
    manifest_path.write_text(json.dumps({
        "repo": repo_slug,
        "harvested_at": datetime.now(timezone.utc).isoformat(),
        "pr_count": pr_count,
        "author_tenure": author_tenure,
        "reviewer_deny": sorted(deny_set),
        "reviewer_allow": sorted(allow_set),
    }, indent=2))

    # Load all cached PR records for artifact building
    all_records = []
    for p in sorted((raw_dir / "prs").glob("*.json")):
        try:
            all_records.append(json.loads(p.read_text()))
        except Exception:
            pass

    # Build and write artifacts
    observations = _build_observations(all_records)
    patterns = _build_patterns(all_records, repo_ctx)
    expertise = _build_expertise_map(all_records)

    (out_dir / "review-observations.json").write_text(json.dumps(observations, indent=2))
    (out_dir / "review-patterns.json").write_text(json.dumps(patterns, indent=2))
    (out_dir / "expertise-map.json").write_text(json.dumps(expertise, indent=2))

    print(f"  PRs fetched (new):   {fetched}")
    print(f"  PRs cached:          {cached}")
    print(f"  PRs skipped (bots):  {skipped_bot}")
    print(f"  Total in cache:      {pr_count}")

    _print_status(repo_slug, out_dir, observations, patterns, expertise)
    return 0
