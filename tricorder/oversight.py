"""Oversight density: where human review attention lands, and where it does not.

Computed from harvested data alone, no LLM. Inputs are normalized PR records::

    {"number": int, "author": str,
     "reviews": [{"reviewer": str, "state": str, "body": str}],
     "inline_comments": [{"reviewer": str, "path": str, "body": str}],
     "files": [str]}                       # changed file paths, when the harvest recorded them

Outputs, per run:

- per_reviewer: PRs reviewed, approvals, silent approvals (approve with no body and
  no inline comment on that PR), inline comments, comments per PR.
- per_tag: for each lens file tag, PRs that touched it, PRs where a human commented on
  it, and the silent share.
- per_axis: the same rolled up through the lens's axis -> tags mapping, with the
  axes flagged ``phase4_absence_is_finding`` marked high-stakes.
- summary: PRs with no human engagement at all, the overall silent-approval share,
  and the engagement split: inline comments by human reviewers, by PR authors on
  their own PRs, and by bots or AI reviewers; PRs where only a bot commented.
- per_tag / per_axis engagement: of the PRs touching a tag, how many had a human
  reviewer comment there, a bot comment, both, or nobody. This is the delegation
  signal: what the team leaves to the bot, and what it still reads itself.

"Human" excludes bots and AI reviewers by login pattern; the caller may pass extra
logins to exclude. A PR author's comments on their own PR are replies, not review,
and count toward neither humans nor bots.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from tricorder.lenses import Lens

BOT_SUFFIXES = ("[bot]",)
BOT_LOGINS = {"github-actions", "dependabot", "renovate", "tulsi-builder", "codecov",
              "coderabbitai", "copilot", "copilot-pull-request-reviewer", "chatgpt-codex-connector"}
MIN_PRS_FOR_REVIEWER_ROW = 3


def is_human(login: str, extra_bots: Iterable[str] = ()) -> bool:
    if not login:
        return False
    low = login.lower()
    if any(low.endswith(s) for s in BOT_SUFFIXES):
        return False
    if low in BOT_LOGINS or low in {b.lower() for b in extra_bots}:
        return False
    return True


def normalize_legacy(pr: dict, reviews: list[dict], comments: list[dict]) -> dict:
    """Legacy harvest cache (raw GitHub objects) -> normalized record."""
    return {
        "number": pr.get("number"),
        "author": (pr.get("author") or {}).get("login") if isinstance(pr.get("author"), dict) else pr.get("author"),
        "reviews": [{"reviewer": (r.get("user") or {}).get("login", ""), "state": r.get("state", ""),
                     "body": r.get("body") or ""} for r in reviews],
        "inline_comments": [{"reviewer": (c.get("user") or {}).get("login", ""), "path": c.get("path", ""),
                             "body": c.get("body") or ""} for c in comments],
        "files": [f.get("filename") if isinstance(f, dict) else f for f in (pr.get("files") or [])],
    }


def normalize_v2(rec: dict) -> dict:
    """v2 review-observations record -> normalized record (already close to the shape)."""
    return {
        "number": rec.get("number"),
        "author": rec.get("author"),
        "reviews": [{"reviewer": r.get("reviewer", ""), "state": r.get("state", ""), "body": r.get("body") or ""}
                    for r in rec.get("reviews", [])],
        "inline_comments": [{"reviewer": c.get("reviewer", ""), "path": c.get("path", ""), "body": c.get("body") or ""}
                            for c in rec.get("inline_comments", [])],
        "files": [f.get("filename") if isinstance(f, dict) else f for f in (rec.get("files") or [])],
    }


def compute(records: list[dict], lens: Lens, extra_bots: Iterable[str] = ()) -> dict[str, Any]:
    per_rev: dict[str, dict] = defaultdict(lambda: {"prs": set(), "approvals": 0, "silent_approvals": 0,
                                                    "inline_comments": 0, "review_bodies": 0})
    per_tag: dict[str, dict] = defaultdict(lambda: {"prs_touching": set(), "prs_commented": set(),
                                                    "prs_bot_commented": set(),
                                                    "comments": 0, "reviewers": set()})
    n_prs = 0
    n_no_engagement = 0
    n_with_files = 0
    total_approvals = 0
    total_silent = 0
    c_human = c_author = c_bot = 0
    n_bot_commented = 0
    n_bot_only = 0

    for rec in records:
        n = rec.get("number"); n_prs += 1
        author = rec.get("author")
        files = [f for f in (rec.get("files") or []) if f]
        if files:
            n_with_files += 1
        comments_by_user: dict[str, int] = defaultdict(int)
        commented_tags: set[str] = set()
        bot_here = False
        for c in rec.get("inline_comments", []):
            u = c.get("reviewer", "")
            tag = lens.file_tag(c.get("path", ""))
            if u == author:
                c_author += 1
                continue
            if not is_human(u, extra_bots):
                c_bot += 1; bot_here = True
                per_tag[tag]["prs_bot_commented"].add(n)
                continue
            c_human += 1
            comments_by_user[u] += 1
            commented_tags.add(tag)
            d = per_tag[tag]; d["comments"] += 1; d["reviewers"].add(u); d["prs_commented"].add(n)
        engaged = bool(comments_by_user)
        if bot_here:
            n_bot_commented += 1
            if not comments_by_user:
                n_bot_only += 1
        for r in rec.get("reviews", []):
            u = r.get("reviewer", "")
            if not is_human(u, extra_bots) or u == author:
                continue
            d = per_rev[u]; d["prs"].add(n)
            if (r.get("body") or "").strip():
                d["review_bodies"] += 1
            state = r.get("state", "")
            if state == "APPROVED":
                d["approvals"] += 1; total_approvals += 1
                if not (r.get("body") or "").strip() and comments_by_user.get(u, 0) == 0:
                    d["silent_approvals"] += 1; total_silent += 1
                else:
                    engaged = True
            elif state in ("CHANGES_REQUESTED", "COMMENTED") and (r.get("body") or "").strip():
                engaged = True
        for u, k in comments_by_user.items():
            per_rev[u]["inline_comments"] += k; per_rev[u]["prs"].add(n)
        if not engaged:
            n_no_engagement += 1
        for f in files:
            per_tag[lens.file_tag(f)]["prs_touching"].add(n)

    reviewers_out = []
    for u, d in per_rev.items():
        prs = len(d["prs"])
        if prs < MIN_PRS_FOR_REVIEWER_ROW:
            continue
        ap = d["approvals"]
        reviewers_out.append({
            "reviewer": u, "prs": prs, "approvals": ap, "silent_approvals": d["silent_approvals"],
            "silent_share": round(d["silent_approvals"] / ap, 3) if ap else None,
            "inline_comments": d["inline_comments"],
            "comments_per_pr": round(d["inline_comments"] / prs, 2) if prs else 0.0,
        })
    reviewers_out.sort(key=lambda r: (-(r["silent_share"] or 0), -r["prs"]))

    def _engagement(touching: set, human: set, bot: set) -> dict:
        """Of the PRs touching a tag: who commented there."""
        if not touching:
            return {"human_and_bot": 0, "human_only": 0, "bot_only": 0, "nobody": 0}
        both = touching & human & bot
        return {"human_and_bot": len(both),
                "human_only": len((touching & human) - bot),
                "bot_only": len((touching & bot) - human),
                "nobody": len(touching - human - bot)}

    tags_out = {}
    all_tags = {t["tag"] for t in lens.file_tags} | set(per_tag) | {"other"}
    empty = {"prs_touching": set(), "prs_commented": set(), "prs_bot_commented": set(), "comments": 0, "reviewers": set()}
    for tag in sorted(all_tags):
        d = per_tag.get(tag, empty)
        touching = len(d["prs_touching"]); commented = len(d["prs_commented"])
        silent = touching - len(d["prs_touching"] & d["prs_commented"]) if touching else None
        tags_out[tag] = {
            "prs_touching": touching if n_with_files else None,
            "prs_commented": commented, "comments": d["comments"],
            "distinct_reviewers": len(d["reviewers"]),
            "prs_touching_without_comment": silent if n_with_files else None,
            "silent_share": round(silent / touching, 3) if (n_with_files and touching) else None,
            "engagement": _engagement(d["prs_touching"], d["prs_commented"], d["prs_bot_commented"]) if n_with_files else None,
        }

    axes_out = []
    for x in lens.axes:
        tags = list(x.get("tags") or [])
        if not tags:
            axes_out.append({"axis": x["id"], "tags": [], "high_stakes": bool(x.get("phase4_absence_is_finding")),
                             "note": "no file tags mapped; not measurable from paths"})
            continue
        touching: set = set(); commented: set = set(); botted: set = set(); comments = 0; reviewers: set = set()
        for t in tags:
            d = per_tag.get(t)
            if d:
                touching |= d["prs_touching"]; commented |= d["prs_commented"]; botted |= d["prs_bot_commented"]
                comments += d["comments"]; reviewers |= d["reviewers"]
        silent = len(touching - commented) if n_with_files else None
        axes_out.append({
            "axis": x["id"], "tags": tags, "high_stakes": bool(x.get("phase4_absence_is_finding")),
            "prs_touching": len(touching) if n_with_files else None,
            "prs_commented": len(commented), "comments": comments, "distinct_reviewers": len(reviewers),
            "prs_touching_without_comment": silent,
            "silent_share": round(silent / len(touching), 3) if (n_with_files and touching) else None,
            "engagement": _engagement(touching, commented, botted) if n_with_files else None,
        })
    axes_out.sort(key=lambda a: (-(a.get("silent_share") or 0), -(a.get("prs_touching") or 0)))

    return {
        "summary": {
            "prs": n_prs,
            "prs_with_changed_files": n_with_files,
            "prs_without_human_engagement": n_no_engagement,
            "no_engagement_share": round(n_no_engagement / n_prs, 3) if n_prs else None,
            "approvals": total_approvals, "silent_approvals": total_silent,
            "silent_approval_share": round(total_silent / total_approvals, 3) if total_approvals else None,
            "inline_comments_by_human_reviewers": c_human,
            "inline_comments_by_pr_authors": c_author,
            "inline_comments_by_bots": c_bot,
            "prs_with_bot_comments": n_bot_commented,
            "prs_bot_only": n_bot_only,
            "bot_only_share": round(n_bot_only / n_prs, 3) if n_prs else None,
        },
        "per_reviewer": reviewers_out,
        "per_tag": tags_out,
        "per_axis": axes_out,
        "lens": lens.summary(),
    }


def oversight_prompt_block(ov: dict, top: int = 6) -> str:
    """Compact text for the Phase 4 user prompt."""
    s = ov.get("summary", {})
    lines = ["OVERSIGHT DENSITY (computed from the harvested record, not from the model):",
             f"- PRs with no human engagement (approve-only or nothing): {s.get('prs_without_human_engagement')} of {s.get('prs')}",
             f"- Silent approvals (approve with no comment): {s.get('silent_approvals')} of {s.get('approvals')}",
             f"- Inline comments: {s.get('inline_comments_by_human_reviewers')} by human reviewers, "
             f"{s.get('inline_comments_by_bots')} by bots or AI reviewers, {s.get('inline_comments_by_pr_authors')} by PR authors replying on their own PRs",
             f"- PRs where a bot commented and no human reviewer did: {s.get('prs_bot_only')} of {s.get('prs')}"]
    axes = [a for a in ov.get("per_axis", []) if a.get("prs_touching")]
    if axes:
        lines.append("- Axes by share of touching PRs that received no human comment:")
        for a in axes[:top]:
            hs = " [high-stakes]" if a.get("high_stakes") else ""
            e = a.get("engagement") or {}
            lines.append(f"    {a['axis']}{hs}: {a['prs_touching_without_comment']} of {a['prs_touching']} PRs "
                         f"({(a['silent_share'] or 0):.0%}) with no human comment; {a['comments']} comments by {a['distinct_reviewers']} reviewers; "
                         f"bot-only on {e.get('bot_only', 0)}, nobody on {e.get('nobody', 0)}")
    else:
        lines.append("- Changed-file lists are not in this cache, so per-axis touch counts are unavailable; comment counts only:")
        for a in sorted(ov.get("per_axis", []), key=lambda a: a.get("comments", 0))[:top]:
            if a.get("tags"):
                lines.append(f"    {a['axis']}: {a.get('comments', 0)} comments by {a.get('distinct_reviewers', 0)} reviewers")
    lines.append("Treat a high-stakes axis with many touching PRs and no human comments as an oversight gap (gap_type coverage_gap). "
                 "Where the bot commented and humans did not, name it as delegated to AI review; where nobody did, as unreviewed.")
    return "\n".join(lines)
