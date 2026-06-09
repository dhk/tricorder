# tricorder

> *"A room full of data people and you named it tricorder instead of data. Yes, on purpose."*

<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/106d5cca-03eb-47ee-a5fe-281ca98063d2" />

A repository learning system. Reads what your team produces during code review — the comments, the back-and-forth, the patterns that recur — and returns a structured map of what the team knows, what it misses, and what is ready to institutionalize.

---

## Install

```bash
# pip
pip install git+https://github.com/dhk/tricorder.git

# npm (auto-installs via pip postinstall)
npm install dhk/tricorder
```

Requires Python 3.9+.

---

## Quick start

```bash
# From inside any git repository:
tricorder make-it-so
```

That's it. Runs the full pipeline. Skips levels it can't reach (e.g. no GitHub token → skips API fetch). Opens the explorer when done.

---

## The pipeline

Six levels. Each one unlocks more signal. Each one is also useful on its own.

| Command | Level | Needs | Output |
|---------|-------|-------|--------|
| `tricorder discover` | 0 | nothing | repo archetype, tech fingerprint, tooling gaps |
| `tricorder discover --history` | 1 | git | contributors, hotspots, evolution timeline |
| `tricorder analyze` | 2 | GitHub token | PR review data, expertise map |
| `tricorder learn` | 3 | LLM API key | patterns, reviewer fingerprints, author profiles, team gaps |
| `tricorder interpret` | 4 | LLM API key | lens-specific interpretation against domain standards |
| `tricorder improve` | 5 | LLM API key | prioritized improvement roadmap |
| `tricorder build --open` | — | Level 3 | interactive explorer at `localhost:7372` |

Every level writes artifacts to `.tricorder/` in the current repo. Each level reads from the previous one — no re-fetching.

---

## Credentials

```bash
# GitHub (for analyze)
export GITHUB_TOKEN=ghp_...
# or: gh auth login

# LLM (for learn / interpret / improve)
export ANTHROPIC_API_KEY=sk-ant-...
# or:
export GEMINI_API_KEY=...
```

Provider config lives in `~/.learn-from-work/config`. Defaults to Anthropic if both keys are present and no config is set. Override per-run with `--provider`.

---

## Discipline lenses

`discover` auto-detects the repo's archetype from the filesystem and proposes a lens. `interpret` applies it.

| Lens | Domain |
|------|--------|
| `analytics-engineering` | dbt, SQL, BigQuery / Snowflake |
| `agent-engineering` | AI agents, MCP servers, skills, evals |
| `product-engineering` | web apps, APIs, backend services |
| `platform-engineering` | infrastructure, IaC, SRE |
| `security` | appsec, infra security |

Override at any point: `tricorder interpret --lens agent-engineering`

---

## Selected flags

```bash
tricorder make-it-so --open          # full pipeline + open browser
tricorder learn --minority-report    # run Phase 4 with all available LLMs, compare
tricorder improve --forge            # implement skill-shaped recommendations as SKILL.md files
tricorder build --open               # serve explorer at localhost:7372
```

---

## What it isn't

Not a metrics dashboard. Not a performance review tool. Not a replacement for live code review. Those answer questions about activity. Tricorder answers questions about knowledge.

---

## Status

Active development. v2 pipeline complete. First production run: 190 PRs, 15 contributors, `cal-itp/data-infra`. Design doc: `DESIGN.md`. Technical spec: `SKILL.md`.
