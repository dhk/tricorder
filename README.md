# tricorder

> *"A room full of data people and you named it tricorder instead of data. Yes, on purpose."*

Scans the ambient signal your team generates every day. Returns a structured map of what they actually know, and what they don't.

Code review is your team's most honest knowledge base. More current than runbooks, less curated than wikis. The problem is it's buried in threads. Tricorder reads those threads and extracts the signal.

---

## What it does

Four questions, one report:

1. **What patterns recur enough to institutionalize?** Convention candidates, tagged by maturity level.
2. **What does each reviewer actually care about?** Focus fingerprints across the full review record.
3. **Where does each author excel, and where do they consistently struggle?** Growth profiles backed by specific evidence.
4. **Where is the team collectively blind?** Coverage gaps against named dbt and SQL standards.

---

## How it works

Two phases. They run independently.

**Harvest** pulls merged PRs from the GitHub API via the `gh` CLI and writes structured JSON to a local cache at `~/.learn-from-work/cache/`. Incremental: re-running harvest only fetches PRs newer than the last run. The cache persists across sessions.

**Synthesize** loads the cache and runs four Claude API calls: one per PR for pattern extraction, one per reviewer for focus fingerprints, one per author for growth profiles, and one team-level gap analysis. Output is a Markdown report committed to your analysis repo plus an interactive React artifact for exploration.

---

## Quick start

```bash
# 1. Set your GitHub token (classic PAT, public_repo scope)
export GITHUB_TOKEN=ghp_your_token

# 2. Install the one dependency
pip install requests

# 3. Run the cost probe first — no Claude API spend until you decide to go
python tricorder-cost-probe.py OWNER/REPO --limit 20

# 4. Harvest
tricorder harvest OWNER/REPO --since 2026-01-01

# 5. Synthesize
tricorder synthesize OWNER/REPO
```

---

## Cost probe

Run `tricorder-cost-probe.py` before any full harvest. It pulls real PRs, assembles the exact prompts, counts tokens, and prints a cost table with extrapolations. No Claude API spend until you decide to go.

```bash
python tricorder-cost-probe.py cal-itp/data-infra --limit 20
```

Expected: roughly $0.02 per PR. A 60-PR run lands around $1.50.

---

## Standards

Where a pattern maps to a named standard, tricorder cites it by name.

- [dbt Labs style guide](https://docs.getdbt.com/best-practices/how-we-style/0-how-we-style-our-dbt-projects)
- [dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator)
- [SQLFluff rule catalog](https://docs.sqlfluff.com/en/stable/rules.html)
- [Kimball dimensional modeling techniques](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- [Google Engineering Practices: code review](https://google.github.io/eng-practices/review/)
- [Smart Bear: 11 proven practices for peer review](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/)

---

## Status

Early and experimental. Architecture and prompts are complete. Validation in progress against `cal-itp/data-infra`.

`SKILL.md` in this repo is the full specification: harvest schema, synthesis prompts, visibility model, and the maturity path taxonomy.

---

## Part of

The DHK skill ecosystem. Adjacent skills: `learn-from-work` (shared maturity taxonomy), `captains-log` (logs synthesis runs as observations), `fossil-record` (tracks artifact evolution). Analysis outputs live in the `adventures-in-ai` repo.
