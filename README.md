# tricorder

> *"A room full of data people and you named it tricorder instead of data. Yes, on purpose."*

<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/106d5cca-03eb-47ee-a5fe-281ca98063d2" />


Software repositories contain two kinds of content. Code is the obvious one. Everything else — the pull request reviews, the inline comments, the back-and-forth before a merge — is the other kind. That second kind is largely untapped as signal.

Tricorder reads it. Returns a structured map of what the team actually knows, what it misses, and what is ready to institutionalize. The output is a document, not a dashboard.

---

## What it does

Four questions, one report:

1. **What patterns recur enough to institutionalize?** Convention candidates, tagged by maturity level.
2. **What does each reviewer actually care about?** Focus fingerprints across the full review record.
3. **Where does each author excel, and where do they consistently struggle?** Growth profiles backed by specific evidence.
4. **Where is the team collectively blind?** Coverage gaps against named dbt and SQL standards.

---

## What it isn't

Not a metrics dashboard. Not a performance review tool. Not a replacement for live code review. Not a GitHub Analytics competitor. Those tools answer questions about activity. Tricorder answers questions about knowledge.

---

## How it works

Two phases. They run independently.

**Harvest** pulls merged PRs from the GitHub API via the `gh` CLI and writes structured JSON to a local cache at `~/.learn-from-work/cache/`. Incremental: re-running harvest only fetches PRs newer than the last run. The cache persists across sessions.

**Synthesize** loads the cache and runs four LLM calls: one per PR for pattern extraction, one per reviewer for focus fingerprints, one per author for growth profiles, and one team-level gap analysis. The active provider comes from `~/.learn-from-work/config` or a CLI override, so you can use Anthropic at home and Gemini at work without changing code. Output is a Markdown report committed to your analysis repo plus an interactive React artifact for exploration.

---

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/dhk/tricorder.git && cd tricorder
pip install -e .

# 2. Set credentials and pick a provider
export GITHUB_TOKEN=ghp_your_token

# Example: Anthropic at home
cat > ~/.learn-from-work/config <<'EOF'
provider=anthropic
model=claude-sonnet-4-6
api_key_env=ANTHROPIC_API_KEY
EOF
export ANTHROPIC_API_KEY=sk-ant-...

# Example: Gemini at work
# provider=gemini
# model=gemini-2.0-flash
# api_key_env=GEMINI_API_KEY
# export GEMINI_API_KEY=...

# 3. Cost probe — no API spend until you decide to go
tricorder probe OWNER/REPO --limit 20

# 4. Harvest
tricorder harvest OWNER/REPO --since 2026-01-01

# 5. Synthesize
tricorder synthesize OWNER/REPO

# Or override for one run
# tricorder synthesize OWNER/REPO --provider gemini --model gemini-2.0-flash --api-key-env GEMINI_API_KEY

# 6. Explore
tricorder render OWNER/REPO && open explorer/index.html
```

---

## Cost probe

Run `tricorder-cost-probe.py` before any full harvest if you're using Anthropic. It pulls real PRs, assembles the exact prompts, counts tokens, and prints a cost table with extrapolations. Gemini runs use the same prompts but a different billing model, so the probe is only a rough planning tool there.

```bash
python tricorder-cost-probe.py cal-itp/data-infra --limit 20
```

Expected: roughly $0.02 per PR. A 60-PR run lands around $1.50.

---

## Standards

Patterns are grounded against named standards, not vibes. Where a review comment maps to a documented convention, tricorder cites it by name.

- [dbt Labs style guide](https://docs.getdbt.com/best-practices/how-we-style/0-how-we-style-our-dbt-projects)
- [dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator)
- [SQLFluff rule catalog](https://docs.sqlfluff.com/en/stable/rules.html)
- [Kimball dimensional modeling techniques](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- [Google Engineering Practices: code review](https://google.github.io/eng-practices/review/)
- [Smart Bear: 11 proven practices for peer review](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/)

---

## Status

Early and experimental. First synthesis run complete against a public dbt/BigQuery analytics team — 190 PRs, 15 contributors, March–May 2026. Output: 5 institutionalization candidates, 14 reviewer fingerprints, 15 author growth profiles, 11 team gaps. Report in `adventures-in-ai`.

`SKILL.md` is the full technical specification: harvest schema, synthesis prompts, visibility model, and the maturity path taxonomy. `DESIGN.md` is the design document: thesis, architecture decisions, limitations, and roadmap.

---

## Part of

The DHK skill ecosystem. Adjacent skills: `learn-from-work` (shared maturity taxonomy), `captains-log` (logs synthesis runs as observations), `fossil-record` (tracks artifact evolution). Analysis outputs live in the `adventures-in-ai` repo.
