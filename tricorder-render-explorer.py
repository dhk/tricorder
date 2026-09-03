#!/usr/bin/env python3
"""
tricorder-render-explorer.py — generate explorer/data.js from synthesis cache

Reads the synthesis cache produced by tricorder-synthesize.py and writes a
fresh data.js for the interactive explorer. Applies a name map if one exists.

Usage:
    python tricorder-render-explorer.py OWNER/REPO
    python tricorder-render-explorer.py OWNER/REPO --name-map PATH
    python tricorder-render-explorer.py OWNER/REPO --out PATH/data.js
    python tricorder-render-explorer.py OWNER/REPO --no-anonymize

Defaults:
    --name-map   ~/.tricorder/<owner>__<repo>-name-map.json  (auto-detected)
    --out        explorer/data.js  (relative to this script)
"""

import argparse
import json
import os
import glob
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# ── Config ────────────────────────────────────────────────────────────────────

CACHE_BASE  = Path.home() / ".learn-from-work" / "cache"
SCRIPT_DIR  = Path(__file__).parent
DEFAULT_OUT = SCRIPT_DIR / "explorer" / "data.js"

CATEGORIES = ["grain", "naming", "testing", "documentation", "style",
              "performance", "modeling", "schema", "business-logic"]

CATEGORY_GROUP = {
    "grain": "data", "naming": "pattern", "testing": "tool",
    "documentation": "pattern", "style": "pattern", "performance": "data",
    "modeling": "data", "schema": "data", "business-logic": "pattern",
}

# Keyword → category mapping for inferring radar chart values from free-text focus areas
CATEGORY_KEYWORDS = {
    "grain":          ["grain", "dedup", "deduplic", "fan-out", "fanout", "row count",
                       "fact table grain", "partition key", "granularity"],
    "naming":         ["naming", "convention", "snake_case", "prefix", "is_", "has_",
                       "stg_", "fct_", "dim_", "int_", "name convention"],
    "testing":        ["test", "fixture", "uniqueness", "not_null", "referential",
                       "primary key", "schema test", "singular test", "generic test",
                       "test coverage", "test pyramid"],
    "documentation":  ["documentation", "docs", "description", "readme", "runbook",
                       "schema.yml", "comment", "docstring", "pr description",
                       "external table", "prerequisite"],
    "style":          ["style", "cte", "qualify", "readability", "formatting",
                       "alias", "trailing comma", "blank line", "select *"],
    "performance":    ["performance", "cost", "scan", "partition pruning", "clustering",
                       "query cost", "expensive", "full table scan", "unbounded"],
    "modeling":       ["incremental", "microbatch", "materialization", "model layer",
                       "staging", "mart", "intermediate", "source_record_id", "scd type",
                       "scd2", "slowly changing", "on_schema_change", "unique_key",
                       "ranged", "exposure", "publish", "layering"],
    "schema":         ["source freshness", "schema change", "breaking change", "exposure",
                       "schema contract", "freshness", "source definition", "yml"],
    "business-logic": ["spec", "business logic", "gtfs", "spec-conformance",
                       "derived field", "domain", "conditional logic", "schedule_relationship"],
}

FREQ_MAP = {"always": 90, "often": 70, "sometimes": 45, "rarely": 22, "never": 5}
BASELINE  = 8  # floor for categories not mentioned at all

# Categories that map to multiple CATEGORY_KEYWORDS buckets
# (a focus area mentioning "exposure" counts for both modeling + schema)
OVERLAP = {
    "exposure": ["modeling", "schema"],
    "publish":  ["modeling", "schema"],
}


# ── Name map ──────────────────────────────────────────────────────────────────

def load_name_map(repo_slug: str, explicit_path: str | None) -> dict:
    """
    Load a real→alias name map. Returns {} if none found (no anonymization).
    Map file format: {"mapping": {"real-login": "Alias", ...}}
    """
    if explicit_path:
        p = Path(explicit_path)
        if not p.exists():
            print(f"  ⚠  name-map not found: {p}", file=sys.stderr)
            return {}
        data = json.loads(p.read_text())
        return data.get("mapping", data)

    # Auto-detect at default location
    default = Path.home() / ".tricorder" / f"{repo_slug}-name-map.json"
    if default.exists():
        data = json.loads(default.read_text())
        print(f"  Name map: {default}")
        return data.get("mapping", data)

    return {}


def apply_map(obj, name_map: dict):
    """Recursively replace real logins with aliases in any JSON-serialisable obj."""
    if not name_map:
        return obj
    if isinstance(obj, str):
        for real, alias in name_map.items():
            obj = obj.replace(real, alias)
        return obj
    if isinstance(obj, list):
        return [apply_map(x, name_map) for x in obj]
    if isinstance(obj, dict):
        return {k: apply_map(v, name_map) for k, v in obj.items()}
    return obj


# ── Category frequency inference ──────────────────────────────────────────────

def load_taxonomy(cache_dir: Path) -> dict:
    """Categories, groups, radar axes, and keywords for this run.

    Lens-driven when synthesize recorded a lens in synthesis/lens.json;
    the legacy dbt set otherwise (runs that predate lens tracking).
    """
    from tricorder.lenses.cache import current_dir
    synth = current_dir(cache_dir / "synthesis")
    lens_file = (synth / "lens.json") if synth else None
    info = json.loads(lens_file.read_text()) if lens_file and lens_file.exists() else {}
    if info.get("name"):
        try:
            from tricorder.lenses import load_lens
            from tricorder.commands.build import taxonomy_from_lens
            tax = taxonomy_from_lens(load_lens(info["name"]))
            tax["lens"] = {**tax["lens"], "source": info.get("source"),
                           "smoke_check_hits": info.get("smoke_check_hits") or {}}
            return tax
        except Exception as e:
            print(f"  ⚠  lens {info['name']!r} not loadable ({e}); using the legacy category set")
    return {"categories": CATEGORIES, "groups": CATEGORY_GROUP,
            "radar": CATEGORIES, "keywords": CATEGORY_KEYWORDS, "lens": info or None}


def infer_category_freq(primary_focus_areas: list, taxonomy: dict | None = None) -> dict:
    """
    Convert a reviewer's primary_focus_areas (area text + frequency word)
    into a {category: 0-100} dict for the radar chart.
    """
    cats = (taxonomy or {}).get("categories") or CATEGORIES
    keyword_map = (taxonomy or {}).get("keywords") or CATEGORY_KEYWORDS
    scores = {cat: BASELINE for cat in cats}

    for entry in primary_focus_areas:
        area_lower = (entry.get("area", "") + " " + (entry.get("category") or "")).lower()
        freq_val   = FREQ_MAP.get(entry.get("frequency", ""), BASELINE)

        if entry.get("category") in scores:
            scores[entry["category"]] = max(scores[entry["category"]], freq_val)
        for cat, keywords in keyword_map.items():
            if cat in scores and any(kw in area_lower for kw in keywords):
                scores[cat] = max(scores[cat], freq_val)

    return scores


# ── Pattern aggregation from Phase 1 ─────────────────────────────────────────

def aggregate_patterns(pr_dir: Path, name_map: dict, top_n: int = 20) -> list:
    """
    Load all Phase 1 PR extraction files, de-duplicate patterns by signal text,
    then select the top top_n // 5 most-recurring patterns from EACH maturity
    level so all five pipeline columns are populated.

    Sorting by raw recurrence count across all levels caused only rule/deterministic
    patterns to be selected (they repeat most exactly), starving judgment/guidance/convention.
    """
    signal_groups: dict[str, dict] = {}  # signal_key → best pattern record

    for f in sorted(pr_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except Exception:
            continue
        if data.get("_error"):
            continue

        for pat in data.get("patterns", []):
            signal = pat.get("signal", "").strip()
            if not signal or len(signal) < 10:
                continue

            # Normalise key: lowercase, strip punctuation edge-chars
            key = signal.lower().rstrip(".").strip()[:120]

            if key not in signal_groups:
                signal_groups[key] = {
                    "signal":            signal,
                    "category":          pat.get("category", "modeling"),
                    "maturity":          pat.get("maturity", "guidance"),
                    "standard_citation": pat.get("standard_citation"),
                    "reviewer":          pat.get("reviewer", ""),
                    "author":            pat.get("author", "") or data.get("_author", ""),
                    "count":             0,
                    "evidence":          [],
                }

            entry = signal_groups[key]
            entry["count"] += 1

            # Collect evidence: prefer entries with real quotes
            for quote in pat.get("comment_evidence", []):
                if len(quote) > 20 and len(entry["evidence"]) < 2:
                    pr_num = f.stem
                    # Pull mergedAt from the PR cache file if available
                    pr_meta_path = f.parent.parent.parent / "prs" / f"{pr_num}.json"
                    date = ""
                    if pr_meta_path.exists():
                        try:
                            pr_meta = json.loads(pr_meta_path.read_text())
                            date = pr_meta.get("mergedAt", "")[:10]
                        except Exception:
                            pass
                    entry["evidence"].append({
                        "pr":     f"#{pr_num}",
                        "date":   date,
                        "author": entry["author"],
                        "quote":  quote[:300],
                    })

    # Grid-based selection: balances BOTH maturity (pipeline tab) and reviewer
    # (coverage grid).
    #
    # For each (maturity × reviewer) pair, keep the best pattern by count.
    # Then score each grid cell by count and greedily select up to top_n patterns,
    # capping each maturity at max_per_maturity and each reviewer at max_per_reviewer.

    maturity_levels = ["judgment", "guidance", "convention", "rule", "deterministic"]
    max_per_maturity = max(2, (top_n + len(maturity_levels) - 1) // len(maturity_levels))  # ceil(top_n/5) = 4
    max_per_reviewer = 3

    def alias(login: str) -> str:
        login = login or ""
        return (name_map.get(login, login) if name_map else login) or ""

    # Build (maturity, reviewer_alias) → best pattern
    grid: dict[tuple, dict] = {}
    for p in signal_groups.values():
        rev = alias(p.get("reviewer", ""))
        key = (p["maturity"], rev)
        if key not in grid or p["count"] > grid[key]["count"]:
            grid[key] = p

    # Sort grid cells by count descending and select greedily
    maturity_quota: dict[str, int] = {m: 0 for m in maturity_levels}
    reviewer_quota: dict[str, int] = {}
    selected = []
    seen_signals = set()

    for p in sorted(grid.values(), key=lambda x: x["count"], reverse=True):
        if len(selected) >= top_n:
            break
        m = p["maturity"]
        rev = alias(p.get("reviewer", ""))
        if maturity_quota.get(m, 0) >= max_per_maturity:
            continue
        if reviewer_quota.get(rev, 0) >= max_per_reviewer:
            continue
        if p["signal"] in seen_signals:
            continue
        selected.append(p)
        seen_signals.add(p["signal"])
        maturity_quota[m] = maturity_quota.get(m, 0) + 1
        reviewer_quota[rev] = reviewer_quota.get(rev, 0) + 1

    # Fill any remaining slots (quota full but top_n not reached) with
    # highest-count unseen patterns, ignoring reviewer cap but respecting maturity cap
    if len(selected) < top_n:
        for p in sorted(signal_groups.values(), key=lambda x: x["count"], reverse=True):
            if len(selected) >= top_n:
                break
            if p["signal"] in seen_signals:
                continue
            if maturity_quota.get(p["maturity"], 0) >= max_per_maturity:
                continue
            selected.append(p)
            seen_signals.add(p["signal"])
            maturity_quota[p["maturity"]] = maturity_quota.get(p["maturity"], 0) + 1

    # Strip internal count field; apply name map
    for p in selected:
        del p["count"]

    return apply_map(selected, name_map)


# ── Reviewer profiles ─────────────────────────────────────────────────────────

def load_reviewers(reviewer_dir: Path, name_map: dict, taxonomy: dict | None = None) -> list:
    reviewers = []
    for f in sorted(reviewer_dir.glob("*.json")):
        try:
            raw = json.loads(f.read_text())
        except Exception:
            continue
        if raw.get("_error"):
            continue

        login = apply_map(f.stem, name_map)
        focus = raw.get("primary_focus_areas", [])
        blind = raw.get("apparent_blind_spots", [])

        reviewers.append({
            "login":               login,
            "review_style":        raw.get("review_style", "advisory"),
            "signal_quality":      raw.get("signal_quality", "low"),
            "primary_focus_areas": apply_map(
                [{"area": a.get("area",""), "frequency": a.get("frequency","sometimes")}
                 for a in focus],
                name_map,
            ),
            "apparent_blind_spots": apply_map(
                [{"area": b.get("area",""), "basis": b.get("basis","")}
                 for b in blind],
                name_map,
            ),
            "category_freq": infer_category_freq(focus, taxonomy),
        })

    # Sort: high signal first, then alpha
    sig_rank = {"high": 0, "medium": 1, "low": 2}
    reviewers.sort(key=lambda r: (sig_rank.get(r["signal_quality"], 9), r["login"]))
    return reviewers


# ── Author profiles ───────────────────────────────────────────────────────────

def load_authors(author_dir: Path, name_map: dict) -> list:
    authors = []
    for f in sorted(author_dir.glob("*.json")):
        try:
            raw = json.loads(f.read_text())
        except Exception:
            continue
        if raw.get("_error"):
            continue

        login = apply_map(f.stem, name_map)
        authors.append({
            "login":       login,
            "trajectory":  raw.get("trajectory", "insufficient-data"),
            "strengths":   apply_map(
                [{"area": s.get("area",""), "persistence": s.get("persistence","consistent")}
                 for s in raw.get("strengths", [])],
                name_map,
            ),
            "growth_areas": apply_map(
                [{"area": g.get("area",""),
                  "persistence": g.get("persistence","consistent"),
                  "support_recommendation": g.get("support_recommendation","")}
                 for g in raw.get("growth_areas", [])],
                name_map,
            ),
        })

    # Sort: improving first, then stable, then insufficient-data, then alpha
    traj_rank = {"improving": 0, "stable": 1, "regressing": 2, "insufficient-data": 3}
    authors.sort(key=lambda a: (traj_rank.get(a["trajectory"], 9), a["login"]))
    return authors


# ── Team gaps ─────────────────────────────────────────────────────────────────

def load_gaps(team_gaps_file: Path, name_map: dict) -> list:
    raw = json.loads(team_gaps_file.read_text())
    if raw.get("_error"):
        print(f"  ⚠  team-gaps.json has an error — skipping gaps section", file=sys.stderr)
        return []

    gaps = raw.get("gaps", [])
    # Assign criticality: coverage_gap=1, blind_spot=2, knowledge_gap=3 (just a display sort)
    crit_map = {"coverage_gap": 1, "blind_spot": 2, "knowledge_gap": 3}

    result = []
    for i, g in enumerate(gaps):
        result.append({
            "area":             g.get("area", ""),
            "gap_type":         g.get("gap_type", "coverage_gap"),
            "criticality":      crit_map.get(g.get("gap_type",""), 2),
            "standard_citation": g.get("standard_citation"),
            "recommendation":   g.get("recommendation", ""),
        })

    return apply_map(result, name_map)


# ── Manifest ──────────────────────────────────────────────────────────────────

def load_manifest(cache_dir: Path) -> dict:
    mf = cache_dir / "harvest-manifest.json"
    if mf.exists():
        return json.loads(mf.read_text())
    return {}


# ── Render data.js ────────────────────────────────────────────────────────────

JS_TEMPLATE = """\
// tricorder — explorer data
// Generated by tricorder-render-explorer.py on {generated}
// Version: {version}  |  Repo: {repo}  |  Window: {window}
// Names anonymized: {anonymized}
window.TRICORDER_DATA = (function () {{

  const CATEGORIES = {categories};
  const RADAR_CATEGORIES = {radar_categories};
  const CATEGORY_GROUP = {category_group};
  const lens = {lens_js};

  const patterns = {patterns};

  const reviewers = {reviewers};

  const authors = {authors};

  const gaps = {gaps};

  return {{
    repo:            {repo_js},
    window:          {window_js},
    pr_count:        {pr_count},
    prs_with_reviews: {prs_with_reviews},
    contributors:    {contributors},
    visibility:      {visibility_js},
    version:         {version_js},
    lens,
    CATEGORIES,
    RADAR_CATEGORIES,
    CATEGORY_GROUP,
    patterns,
    reviewers,
    authors,
    gaps,
  }};
}})();
"""


def read_version(script_dir: Path) -> str:
    """Read version from VERSION file next to this script. Falls back to 'dev'."""
    vf = script_dir / "VERSION"
    if vf.exists():
        return vf.read_text().strip()
    return "dev"


def render(repo: str, cache_dir: Path, name_map: dict, out_path: Path, anonymized: bool):
    from tricorder.lenses.cache import current_dir
    manifest    = load_manifest(cache_dir)
    synth       = current_dir(cache_dir / "synthesis") or (cache_dir / "synthesis")
    print(f"  Synthesis: {synth}")
    pr_dir      = synth / "pr"
    reviewer_dir = synth / "reviewers"
    author_dir  = synth / "authors"
    gaps_file   = synth / "team-gaps.json"

    for required in (pr_dir, reviewer_dir, author_dir, gaps_file):
        if not required.exists():
            print(f"  ✗  Not found: {required}", file=sys.stderr)
            print("     Run tricorder-synthesize.py first.", file=sys.stderr)
            sys.exit(1)

    taxonomy = load_taxonomy(cache_dir)
    if taxonomy.get("lens"):
        print(f"  Lens: {taxonomy['lens'].get('name')} ({len(taxonomy['categories'])} categories)")

    print("  Loading Phase 1 PR patterns...")
    patterns = aggregate_patterns(pr_dir, name_map)
    print(f"    → {len(patterns)} patterns selected")

    print("  Loading Phase 2 reviewer profiles...")
    reviewers = load_reviewers(reviewer_dir, name_map, taxonomy)
    print(f"    → {len(reviewers)} reviewers")

    print("  Loading Phase 3 author profiles...")
    authors = load_authors(author_dir, name_map)
    print(f"    → {len(authors)} authors")

    print("  Loading Phase 4 team gaps...")
    gaps = load_gaps(gaps_file, name_map)
    print(f"    → {len(gaps)} gaps")

    dr          = manifest.get("date_range", {})
    window_str  = f"{dr.get('from','')} → {dr.get('to','')}"
    pr_count    = manifest.get("pr_count", 0)
    prs_rev     = pr_count - len([f for f in pr_dir.glob("*.json") if not json.loads(f.read_text()).get("_error")])
    # prs_with_reviews = pr_count - skipped_count (approximate)
    # More accurately: count valid synthesis files
    valid_pr_count = sum(
        1 for f in pr_dir.glob("*.json")
        if not json.loads(f.read_text()).get("_error")
    )
    contributors = manifest.get("contributors", [])
    if name_map:
        contributors = [name_map.get(c, c) for c in contributors]

    version = read_version(SCRIPT_DIR)

    js = JS_TEMPLATE.format(
        generated        = datetime.now().strftime("%Y-%m-%d %H:%M"),
        version          = version,
        repo             = repo,
        window           = window_str,
        anonymized       = "yes" if anonymized else "no",
        categories       = json.dumps(taxonomy["categories"]),
        radar_categories = json.dumps(taxonomy["radar"]),
        category_group   = json.dumps(taxonomy["groups"]),
        lens_js          = json.dumps(taxonomy.get("lens")),
        patterns         = json.dumps(patterns, indent=2),
        reviewers        = json.dumps(reviewers, indent=2),
        authors          = json.dumps(authors, indent=2),
        gaps             = json.dumps(gaps, indent=2),
        repo_js          = json.dumps(repo),
        window_js        = json.dumps(window_str),
        pr_count         = pr_count,
        prs_with_reviews = valid_pr_count,
        contributors     = json.dumps(contributors),
        visibility_js    = json.dumps("demo" if anonymized else "private"),
        version_js       = json.dumps(version),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(js)
    print(f"\n  ✓  Written to: {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo",         help="OWNER/REPO  e.g. cal-itp/data-infra")
    ap.add_argument("--name-map",   help="Path to JSON name map (auto-detected if omitted)")
    ap.add_argument("--out",        help="Output path for data.js (default: explorer/data.js next to this script)")
    ap.add_argument("--no-anonymize", action="store_true", help="Skip name map even if one is found")
    args = ap.parse_args()

    repo_slug = args.repo.replace("/", "__")
    cache_dir = CACHE_BASE / repo_slug

    if not cache_dir.exists():
        print(f"Cache not found: {cache_dir}", file=sys.stderr)
        print("Run:  tricorder harvest {args.repo}", file=sys.stderr)
        sys.exit(1)

    out_path = Path(args.out) if args.out else DEFAULT_OUT

    print(f"\ntricorder-render-explorer")
    print(f"  Repo:  {args.repo}")
    print(f"  Cache: {cache_dir}")
    print(f"  Out:   {out_path}\n")

    if args.no_anonymize:
        name_map = {}
        anonymized = False
    else:
        name_map = load_name_map(repo_slug, args.name_map)
        anonymized = bool(name_map)
        if not name_map:
            print("  No name map found — real contributor names will appear in data.js")
            print("  To anonymize: create ~/.tricorder/{slug}-name-map.json")
            print('  Format: {"mapping": {"real-login": "Alias", ...}}\n')

    render(args.repo, cache_dir, name_map, out_path, anonymized)

    print(f"\n  Next: commit explorer/data.js → GitHub Pages updates automatically.")
    print(f"  Explorer: https://dhk.github.io/tricorder/explorer/\n")


if __name__ == "__main__":
    main()
