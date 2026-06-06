---
name: tricorder
version: 1.1.0
description: >
  Analyzes GitHub pull request review history for a repository over a time window to extract
  learning signals: patterns ready for institutionalization, reviewer focus fingerprints,
  per-author strength/gap profiles, and team-level coverage gaps. Outputs a Markdown report
  committed to the analysis repo and an interactive React artifact for exploration. Scoped to
  dbt/SQL analytics repos. Two-phase: harvest (GitHub API → local cache) then synthesize
  (cache → provider-selected LLM analysis → outputs). Cache is persistent across sessions at
  ~/.learn-from-work/cache/. Trigger on: "tricorder", "scan PRs", "analyze PRs", "learn from PRs", "review signal",
  "what are we learning from code review", "PR patterns", or any request to extract learning
  from pull request history.
visibility: private
depends_on:
  - gh CLI (authenticated)
  - one provider key: ANTHROPIC_API_KEY or GEMINI_API_KEY
cache_dir: ~/.learn-from-work/cache/
output_dir: adventures-in-ai/tricorder/
---

# tricorder

> *"A room full of data people and you named it tricorder instead of data. Yes, on purpose."*

> *Scans the ambient signal your team generates every day and returns a structured map of what they actually know — and what they don't.*

Extracts durable learning from GitHub PR review history. Not a metrics dashboard — a signal extractor.
Two phases. Cache everything. Build understanding that compounds across sessions.

---

## Core Philosophy

Code review comments are the team's living knowledge base — more honest than wikis, more current than
runbooks. This skill reads that record and asks four questions:

1. **What patterns recur enough to institutionalize?** (Convention candidates)
2. **What does each reviewer care about most?** (Focus fingerprints)
3. **Where does each author excel, and where do they struggle?** (Growth profiles)
4. **Where is the team collectively blind?** (Coverage gaps)

Answers are grounded in dbt Labs style guides, SQLFluff rule sets, Kimball principles, and the
dbt-project-evaluator check catalog. Where a pattern maps to a named standard, it is cited by name.

**The maturation path** (inherited from learn-from-work):
`judgment → guidance → convention → rule → deterministic enforcement`

Every identified pattern is tagged with a maturity level. That tag is the signal for what to do next:
- `judgment` — too context-dependent to codify yet; document the heuristic
- `guidance` — ready for a team norm doc entry
- `convention` — ready for a PR checklist or template
- `rule` — ready for SQLFluff or dbt-project-evaluator enforcement
- `deterministic` — ready for CI gate

---

## Architecture

```
Phase 1: HARVEST
  gh CLI → GitHub API → raw JSON cache (~/.learn-from-work/cache/<repo>/<date>/)
  Incremental: only pull PRs newer than last cache timestamp

Phase 2: SYNTHESIZE
  Cache → provider-selected LLM analysis → signal extraction → outputs
  Outputs: Markdown report (repo) + React artifact (exploration)
```

Cache is persistent. Harvest and synthesize can run independently.
Re-synthesis is cheap — no API calls needed after a full harvest.

---

## Setup & Config

### First-run config check

On first invocation, check for `~/.learn-from-work/config`:

```bash
cat ~/.learn-from-work/config 2>/dev/null || echo "MISSING"
```

If missing, create it interactively:

```
# ~/.learn-from-work/config  (shared across tricorder + other skills)
default_repo=OWNER/REPO          # e.g. dhk/analytics
default_window_days=90           # how many days back to pull by default
cache_dir=~/.learn-from-work/cache/
output_repo=~/path/to/adventures-in-ai
provider=anthropic               # or gemini
model=claude-sonnet-4-6          # or gemini-2.0-flash
api_key_env=ANTHROPIC_API_KEY
keychain_service=anthropic_api_key
```

Ask:
> "Two quick setup questions. What's your default repo (owner/repo)? And how many days back should
> I look by default? (90 is a good start — you can override per run.)"

### Keychain credential retrieval

Retrieve GitHub token (never ask user to paste):
```bash
security find-generic-password -a "dhk" -s "github-fossil-pat" -w
```

Retrieve Anthropic key:
```bash
security find-generic-password -a "$USER" -s "anthropic_api_key" -w
```

Retrieve Gemini key:
```bash
echo "$GEMINI_API_KEY"
```

---

## Phase 1: Harvest

### Invocation

```
tricorder harvest [OWNER/REPO] [--days N] [--since YYYY-MM-DD] [--force]
```

- `--days N`: override default window (default: from config)
- `--since YYYY-MM-DD`: explicit start date (overrides --days)
- `--force`: ignore cache, re-pull everything

### Cache structure

```
~/.learn-from-work/cache/
  <owner>__<repo>/
    harvest-manifest.json          # last run timestamp, PR count, date range
    repo-context.json              # dbt_project.yml summary, SQLFluff rules, PR template — read at synthesis
    prs/
      <pr-number>.json             # full PR metadata + description + description_quality score
    reviews/
      <pr-number>-reviews.json     # all review threads for that PR, with iteration count
    comments/
      <pr-number>-comments.json    # inline diff comments, with resolution status
```

### Harvest steps

**Step 1 — Check manifest for incremental window**

```bash
cat ~/.learn-from-work/cache/<owner>__<repo>/harvest-manifest.json 2>/dev/null
```

If manifest exists and `--force` is not set: only fetch PRs with `updated_at` newer than
`manifest.last_harvest`. Report: `"Cache found — fetching PRs since [date]. Use --force to
re-pull all."`

**Step 2 — Pull merged PRs**

```bash
gh pr list \
  --repo OWNER/REPO \
  --state merged \
  --limit 500 \
  --json number,title,author,createdAt,mergedAt,body,additions,deletions,changedFiles \
  > /tmp/lfp-pr-list.json
```

Filter to date window in Python. Write individual `<number>.json` files to cache.

**Step 3 — Pull reviews for each PR, compute iteration count**

```bash
gh api repos/OWNER/REPO/pulls/NUMBER/reviews \
  --paginate \
  --jq '[.[] | {id,user:.user.login,state,body,submitted_at}]' \
  > ~/.learn-from-work/cache/<owner>__<repo>/reviews/NUMBER-reviews.json
```

After writing, compute `review_iterations`: count of `CHANGES_REQUESTED` states before final
`APPROVED`. Append to the PR's `.json` as `"review_iterations": N`. PRs with
`review_iterations >= 2` get flagged as higher-signal for pattern extraction.

**Step 4 — Pull inline review comments, flag replied threads**

```bash
gh api repos/OWNER/REPO/pulls/NUMBER/comments \
  --paginate \
  --jq '[.[] | {id,user:.user.login,path,line,body,created_at,in_reply_to_id}]' \
  > ~/.learn-from-work/cache/<owner>__<repo>/comments/NUMBER-comments.json
```

Post-process: any root comment that has at least one sibling with a matching `in_reply_to_id`
gets `has_reply: true`. This is a proxy for engagement — a comment that got a reply was
substantive enough to warrant discussion.

**Step 5 — Harvest repo context (once per repo, refresh weekly)**

Check if `repo-context.json` exists and is less than 7 days old. If stale or missing:

```bash
# Shallow clone to /tmp — discard after harvest
gh repo clone OWNER/REPO /tmp/lfp-repo-clone -- --depth 1 2>/dev/null

# Read the three files we care about
cat /tmp/lfp-repo-clone/dbt_project.yml 2>/dev/null
cat /tmp/lfp-repo-clone/.sqlfluff 2>/dev/null || cat /tmp/lfp-repo-clone/setup.cfg 2>/dev/null
cat /tmp/lfp-repo-clone/.github/pull_request_template.md 2>/dev/null

rm -rf /tmp/lfp-repo-clone
```

Write to `repo-context.json`:
```json
{
  "harvested_at": "ISO-8601",
  "dbt_project_name": "str",
  "model_paths": ["models/"],
  "sqlfluff_rules_enforced": ["L010", "L014"],
  "pr_template_present": true,
  "pr_template_sections": ["Why", "What changed", "Testing approach"]
}
```

Synthesis uses this three ways: (a) skip recommending SQLFluff rules already enforced as CI
gates, (b) treat comments that catch things the PR template should have covered as stronger
signal — the template is failing, not just the author, (c) use `model_paths` to improve
file-type tagging accuracy.

If the repo is not locally cloneable, log a warning and proceed without repo context — synthesis
degrades gracefully, just without the "already enforced" filter.

**Step 6 — Score PR description quality**

For each PR, append `description_quality` to its `.json`:

```python
def score_description(body):
    if not body:
        return {"word_count": 0, "quality": "low", "low_confidence": True}
    wc = len(body.split())
    has_why     = any(w in body.lower() for w in ["why", "because", "motivation", "context"])
    has_what    = any(w in body.lower() for w in ["change", "added", "removed", "updated", "refactor"])
    has_testing = any(w in body.lower() for w in ["test", "verified", "checked", "validated", "dbt run"])
    score = sum([wc >= 50, has_why, has_what, has_testing])
    quality = "high" if score >= 3 else "medium" if score >= 2 else "low"
    return {"word_count": wc, "quality": quality, "low_confidence": quality == "low"}
```

Synthesis prompts receive `low_confidence: true` on the PR payload when description quality is
low. The model is instructed to flag those pattern extractions as tentative.

**Step 7 — Capture author tenure signal**

For each distinct author in the cache, find their earliest `merged_at` across all cached PRs
(not just the current window). Append to manifest:

```json
"author_tenure": {
  "login": { "first_pr_in_cache": "YYYY-MM-DD", "cache_days": N }
}
```

Synthesis uses this to calibrate gap findings: the same gap carries different weight for
someone with 3 months of cache history vs. 18 months.

**Step 8 — Update manifest**

```json
{
  "repo": "OWNER/REPO",
  "last_harvest": "ISO-8601 timestamp",
  "pr_count": N,
  "date_range": { "from": "YYYY-MM-DD", "to": "YYYY-MM-DD" },
  "contributors": ["login1", "login2", ...]
}
```

**Step 6 — Report harvest summary**

```
Harvest complete.
  Repo:        OWNER/REPO
  Window:      YYYY-MM-DD → YYYY-MM-DD
  PRs pulled:  N
  Contributors: [list]
  Cache at:    ~/.learn-from-work/cache/OWNER__REPO/  (tricorder family)

Ready to synthesize. Run: tricorder synthesize
```

### Rate limit handling

- Use `gh api` with `--paginate` — respects GitHub's rate headers automatically
- Between PR review fetches, check remaining rate: `gh api rate_limit --jq '.rate.remaining'`
- If remaining < 100: pause and report `"Rate limit low — pausing harvest. Resume with same
  command; cache is safe."` Do not exit with error.
- Primary REST API limit: 5,000 req/hr for authenticated users. 500 PRs × 2 calls = 1,000 calls
  typical; well within limits.

---

## Phase 2: Synthesize

### Invocation

```
tricorder synthesize [OWNER/REPO] [--window YYYY-MM-DD:YYYY-MM-DD]
```

If no repo specified, uses default from config. Window defaults to full cache contents.

### Synthesis pipeline

Synthesis runs with the active LLM provider (headless or interactive). It:
1. Loads all cached JSON for the target window
2. Assembles a structured analysis payload per PR
3. Calls the configured provider and model for signal extraction (batched by contributor, then team-level)
4. Aggregates outputs into report sections
5. Writes Markdown to output repo
6. Renders React artifact for exploration

### PR payload assembly

For each PR, build a normalized record:

```python
{
  "pr_number": int,
  "title": str,
  "author": str,
  "description": str,          # PR body — key context signal
  "files_changed": int,
  "additions": int,
  "deletions": int,
  "merged_at": str,
  "reviews": [
    {
      "reviewer": str,
      "state": "APPROVED|CHANGES_REQUESTED|COMMENTED",
      "body": str,             # top-level review comment
      "inline_comments": [
        {
          "path": str,         # file path — use to detect model type
          "body": str,         # the actual comment
          "line": int
        }
      ]
    }
  ]
}
```

### Model/file type detection

Inspect `path` field to tag each inline comment with context:

| Pattern | Tag |
|---------|-----|
| `models/` + `.sql` | `dbt-model` |
| `macros/` + `.sql` | `dbt-macro` |
| `tests/` | `dbt-test` |
| `*.yml` in `models/` | `dbt-schema` |
| `*.py` | `python` |
| `dbt_project.yml` | `dbt-config` |
| `*.md` | `documentation` |

---

## Signal Extraction: Claude Prompts

### Prompt 1 — Per-PR pattern extraction

Called once per PR. Returns structured JSON.

```
SYSTEM:
You are a senior analytics engineering reviewer analyzing a GitHub pull request.
Your job is to extract review signals — patterns, feedback themes, and learning
moments — from the PR description and review comments.

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
      "comment_evidence": ["quoted snippet 1", "quoted snippet 2"],
      "author": "login",
      "reviewer": "login"
    }
  ],
  "author_strengths": ["..."],
  "author_gaps": ["..."],
  "reviewer_focus_signals": {
    "<reviewer_login>": ["signal 1", "signal 2"]
  }
}

USER:
PR #[number]: [title]
Author: [login] (cache tenure: [N] days)
Review iterations before approval: [N]
Description quality: [high|medium|low]{% if low_confidence %} ⚠ LOW CONFIDENCE — description thin, treat pattern extractions as tentative{% endif %}

Description:
[PR body]

Repo context:
- SQLFluff rules already enforced as CI gates: [list or "none detected"]
- PR template sections expected: [list or "no template"]
- Model paths: [list]

Reviews:
[formatted review threads — include review state and whether comments have replies]
```

### Prompt 2 — Reviewer focus fingerprint

Called once per reviewer across all their PRs. Returns profile.

```
SYSTEM:
You are analyzing a code reviewer's review history across multiple PRs in a dbt/SQL
analytics repository. Your job is to build a focus fingerprint — what does this
reviewer consistently care about, and what do they appear to overlook or underweight?

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
      "example_comments": ["snippet 1", "snippet 2"]
    }
  ],
  "apparent_blind_spots": [
    {
      "area": "description — what they rarely or never comment on despite it being relevant",
      "basis": "why you infer this is a blind spot"
    }
  ],
  "review_style": "blocking | advisory | conversational | terse | thorough",
  "signal_quality": "high | medium | low",
  "signal_quality_rationale": "one sentence"
}

USER:
Reviewer: [login]
PRs reviewed: [count]

Review history (structured):
[all review comments and bodies for this reviewer, across all PRs]
```

### Prompt 3 — Author growth profile

Called once per author across all their PRs.

```
SYSTEM:
You are analyzing a code author's pull request history in a dbt/SQL analytics
repository. Your job is to build a growth profile — where do they consistently do
well, and where do they consistently need support?

Look for persistence: if the same gap appears in 3+ PRs, it is a growth area, not
a one-off. If the same strength appears in 3+ PRs, it is a genuine asset.

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
}

USER:
Author: [login]
PRs in window: [count]

PR history (chronological):
[structured PR + review data for this author]
```

### Prompt 4 — Team gap analysis

Called once across the full dataset.

```
SYSTEM:
You are analyzing the complete PR review history of an analytics engineering team
working in a dbt/SQL repository. Your job is to identify where the team is strong
collectively and where it has review gaps.

Use the following gap taxonomy:
- coverage_gap: nobody ever reviews for this dimension
- knowledge_gap: reviewers raise this topic but comments are shallow or inconsistent
- blind_spot: this is a named best practice that never appears in any review

Reference the dbt Labs style guide, dbt-project-evaluator check catalog, SQLFluff
rules, and Kimball principles explicitly. If a known best practice is absent from
the review record, name it.

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
}

USER:
Team: [list of contributors]
Window: [date range]
PR count: [N]

Aggregated pattern signals:
[JSON array of all patterns extracted in Prompt 1, across all PRs]

Reviewer fingerprints:
[JSON array of all reviewer profiles from Prompt 2]
```

---

## Output: Markdown Report

Written to: `adventures-in-ai/tricorder/YYYY-MM-DD-<repo-slug>.md`

```markdown
---
date: YYYY-MM-DD
repo: OWNER/REPO
window: YYYY-MM-DD → YYYY-MM-DD
pr_count: N
contributors: [list]
visibility: private
generated_by: tricorder v1.1.0
---

# PR Review Analysis — <repo> — <date>

> Window: YYYY-MM-DD → YYYY-MM-DD | N PRs | N contributors

---

## 1. Patterns Ready to Institutionalize

Recurring signals strong enough to advance up the maturity path.

| Pattern | Category | Current Maturity | Next Step | Standard |
|---------|----------|-----------------|-----------|----------|
| ... | ... | convention | Add to PR template | dbt style guide §3.2 |

### Notes
[2-3 sentences on the most important institutionalization opportunity]

---

## 2. Reviewer Focus Fingerprints

### [Reviewer Login]
**Style:** [blocking/advisory/conversational] | **Signal quality:** [high/medium/low]

**Primary focus areas:**
- [area] ([frequency]) — *[standard citation if applicable]*

**Apparent blind spots:**
- [area] — [basis]

[Repeat per reviewer]

---

## 3. Author Growth Profiles

> Note: This section is private. Audience: team lead / manager only.

### [Author Login]
**Trajectory:** [improving/stable/regressing] — [one-sentence rationale]

**Strengths:**
- [area] ([persistence]) — *[standard citation]*

**Growth areas:**
- [area] ([persistence]) — *[standard citation]*
  → **Support:** [specific recommendation]

[Repeat per author]

---

## 4. Team Gap Analysis

### Where the team is strong
| Area | Evidence | Standard |
|------|----------|----------|
| ... | ... | ... |

### Gaps and blind spots
| Area | Gap Type | Missing Standard | Recommendation |
|------|----------|-----------------|----------------|
| ... | coverage_gap | dbt-project-evaluator: fct_model_has_primary_key_tests | Add to CI |

### Institutionalization pipeline
| Pattern | Current Maturity | Target | Next Step |
|---------|-----------------|--------|-----------|
| ... | guidance | rule | SQLFluff custom rule |

### Review culture
[2-3 sentences from Prompt 4 review_culture_observations]

---

## Methodology & Caveats

- **Window:** [date range] | **PRs analyzed:** N | **PRs skipped (no reviews):** N
- **Description quality:** N high / N medium / N low — low-quality descriptions reduce extraction confidence for those PRs
- **Repo context:** SQLFluff config [found/not found] | PR template [found/not found] | dbt_project.yml [found/not found]
- **Author tenure range:** [shortest] – [longest] months of cache history
- **What this analysis cannot see:** verbal review culture (Slack), reviewer availability constraints, domain ownership, or PRs merged without review. Findings should be read alongside those factors, not in place of them.

---

## Appendix: Reference Standards

- **dbt Labs style guide**: https://docs.getdbt.com/best-practices/how-we-style/0-how-we-style-our-dbt-projects
- **dbt-project-evaluator**: https://github.com/dbt-labs/dbt-project-evaluator
- **SQLFluff rule catalog**: https://docs.sqlfluff.com/en/stable/rules.html
- **Kimball Group — dimensional modeling techniques**: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/
- **Google Engineering Practices — code review**: https://google.github.io/eng-practices/review/
- **Smart Bear — 11 proven practices for peer review**: https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/
```

Commit to repo:
```bash
cd ~/path/to/adventures-in-ai
git add tricorder/YYYY-MM-DD-<repo-slug>.md
git commit -m "tricorder: analysis for <repo> window <date-range>"
git push
```

---

## Output: React Artifact

An interactive exploration tool rendered in Claude Chat. Built with Recharts + Tailwind.

### Sections / tabs

**Tab 1 — Pattern Heatmap**
- X-axis: category (grain, naming, testing, documentation, style, performance, modeling, schema, business-logic)
- Y-axis: reviewer
- Cell color: frequency (white → amber → gold)
- Click cell: drill into specific comments

**Tab 2 — Maturity Pipeline**
- Kanban-style columns: judgment | guidance | convention | rule | deterministic
- Each card: pattern name, category badge, citation pill
- Drag-to-promote UI (visual only — actual promotion requires manual action)

**Tab 3 — Author Profiles**
- Card per author
- Strength/gap bars by category
- Trajectory indicator (↑ ↓ →)
- Expandable: specific comments as evidence

**Tab 4 — Team Gaps**
- Three-panel: coverage gaps | knowledge gaps | blind spots
- Each item: gap name, gap type badge, standard citation, recommendation
- Sort by severity (blind spots first)

**Tab 5 — Reviewer Fingerprints**
- Radar chart per reviewer (categories on axes, frequency as fill)
- Table below: focus areas + blind spots

### Design tokens

Reference: `dhk-design-spec.md` — the canonical DHK visual system.

- Background: `#f9f8f6` (`--bg`) — light canvas, never dark
- Elevated surfaces / cards: `#f2f1ee` (`--bg2`), hover: `#eae9e5` (`--bg3`)
- Default text: `#0a0a09` (`--text`)
- Metadata / captions: `#5a5850` (`--text-dim`)
- Headings: Barlow Condensed (600–700) — never Barlow sans for headings
- Body: Barlow (300–400), `line-height: 1.75`
- Tags / labels / code: DM Mono — `font-size: 9–11px`, uppercase, `letter-spacing: 0.1em`
- Accent (brand green): `#16a34a` — borders, links, hover states; used sparingly
- Content type tints for tricorder:
  - Patterns / institutionalization: green `rgba(22,163,74,0.10)` / `#15803d`
  - Tools / skills: purple `rgba(124,92,224,0.10)` / `#7c5ce0`
  - Data / analysis: blue `rgba(41,112,214,0.10)` / `#2970d6`
  - Team / project / gaps: orange `rgba(217,79,42,0.10)` / `#d94f2a`
- Border radius: `4px` — no pill shapes, no sharp corners
- No gold, no amber, no navy backgrounds, no serif fonts

---

## Incremental / Multi-Session Operation

This skill is designed for ongoing use, not one-off runs.

**Recommended cadence:** Run harvest weekly (or after sprint close). Run synthesize monthly or
after significant PR volume accumulates.

**Incremental harvest:** Manifest tracks last harvest timestamp. Re-running harvest only pulls
new PRs. Cache entries are immutable once written — a PR's review history is not re-fetched
unless `--force` is used.

**Trend detection (future):** When multiple synthesis runs exist for the same repo, the skill
will diff pattern maturity across runs and flag promotions (`guidance` → `convention`) and
regressions (a convention that stopped appearing in reviews).

---

## Visibility Model

Output files carry a `visibility` frontmatter field:

| Value | Meaning | Sections included |
|-------|---------|-------------------|
| `private` | Author only (or team lead) | All sections including author profiles |
| `team` | Shared with team | Reviewer fingerprints + gap analysis only; author profiles redacted |
| `public` | Open | Anonymized patterns + team gaps only |

Default: `private`. Override at synthesis time:
```
tricorder synthesize --visibility team
```

When `team` visibility is set, author profile section is replaced with:
> *"Individual author profiles omitted in team-visibility reports. Run with --visibility private
> to include."*

---

## Error Handling

| Condition | Behavior |
|-----------|----------|
| `gh` not authenticated | `"gh CLI not authenticated. Run: gh auth login"` |
| Repo not found | Abort harvest, report repo name + suggestion to check OWNER/REPO format |
| Cache dir missing | Create it: `mkdir -p ~/.learn-from-work/cache/` |
| PR has no reviews | Include in harvest, skip in synthesis (log count of review-less PRs) |
| LLM API timeout | Retry once with 10s backoff. If second attempt fails, write partial results and note which PRs were skipped |
| Rate limit hit | Pause, write manifest with current progress, report resume instruction |

---

## Example Invocations

```bash
# First run — harvest 90 days for default repo
tricorder harvest

# Harvest a specific repo, specific window
tricorder harvest dhk/analytics --since 2026-01-01

# Re-pull everything (ignore cache)
tricorder harvest dhk/analytics --force

# Synthesize using cached data
tricorder synthesize

# Synthesize with team visibility (redacts author profiles)
tricorder synthesize --visibility team

# Full run (harvest + synthesize in one shot)
tricorder run dhk/analytics --days 60
```

---

## Connections to Adjacent Skills

| Skill | Connection |
|-------|-----------|
| `learn-from-work` | Shares signal taxonomy and maturity path. Patterns extracted here can be promoted into the `learn-from-work` signal registry |
| `captains-log` | Log synthesis runs as `observation` entries — what changed since last run, what's maturing |
| `fossil-record` | Complementary — fossil-record tracks artifact evolution over time, tricorder tracks human knowledge embedded in review threads |
| `weekly-reset` | Surface top institutionalization candidate in weekly reset summary |
