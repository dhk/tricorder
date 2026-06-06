# Tricorder — Product Brief

**Current shipped version:** 1.0.1.2  
**Repo:** [dhk/tricorder](https://github.com/dhk/tricorder)

---

> **This is a design brief, not a description of current behavior.**
>
> Part 1 describes what is shipped today. Part 2 describes what is proposed — none of it is implemented. Part 3 is the migration plan.
>
> Source of truth for what works right now: [README.md](README.md) and [DESIGN.md](DESIGN.md) (v1 sections).

---

## Part 1 — v1: What exists today

### What tricorder is (v1)

A CLI tool that analyzes the merged pull request history of a dbt/SQL analytics repository and returns a structured map of what the team knows, what it misses, and what is ready to institutionalize.

Validated on one production team: cal-itp/data-infra, 172 PRs, March–May 2026.

### Current CLI (v1 — shipped)

```
tricorder ready      OWNER/REPO [--days N]
tricorder probe      OWNER/REPO [--limit N] [--since YYYY-MM-DD]
tricorder harvest    OWNER/REPO [--since YYYY-MM-DD] [--limit N] [--force]
tricorder synthesize OWNER/REPO [--visibility private|team|public] [--out DIR]
                                [--provider anthropic|gemini] [--model NAME]
tricorder render     OWNER/REPO [--out PATH] [--name-map PATH]
tricorder demo       [--fast] [--no-pause]
tricorder --version
```

### Current pipeline (v1 — shipped)

| Step | Command | Access required | What it does |
|------|---------|----------------|--------------|
| 1 | `ready` | GitHub read | Pre-flight: is this repo a good candidate? |
| 2 | `probe` | GitHub read | Cost estimate before LLM spend |
| 3 | `harvest` | GitHub read | Pull PR data to local cache |
| 4 | `synthesize` | LLM API | Four LLM analyses → Markdown report |
| 5 | `render` | None (reads cache) | Generate static HTML explorer |

Credentials required to do anything: `GITHUB_TOKEN` + LLM API key.

### Current outputs (v1 — shipped)

- Markdown report (four sections: patterns, reviewer fingerprints, author profiles, team gaps)
- `explorer/data.js` — data layer for the static HTML explorer on GitHub Pages
- Local cache at `~/.learn-from-work/cache/<owner>__<repo>/` — raw PR JSON, synthesis JSON

No structured artifact files. No `.tricorder/` directory. Cache is internal, not designed for external consumption.

### Current scope (v1 — shipped)

Scoped to dbt/SQL analytics repositories only. Category taxonomy, standard citations, and prompt design are calibrated for analytics engineering. Output on other repository types degrades.

---

> **Everything below this line is proposed, not implemented.**
> The codebase still exposes the v1 CLI. None of the commands, artifacts, or behaviors described in Part 2 exist yet.

---

## Part 2 — v2: What is proposed

### The problem v2 solves

Three gaps identified after the first synthesis run:

1. **Credential gate before value.** v1 requires GitHub token + LLM API key before producing anything. Users invest trust without seeing whether the tool is worth it.

2. **No interpretation layer.** Findings describe what the team discusses. They do not explain why it matters or what to do first. That requires domain-specific framework — currently baked into prompts, not explicit.

3. **Outputs not reusable.** The cache and report are designed for humans. Nothing downstream (other tools, AI agents) can consume findings without re-running the pipeline.

### v2 thesis

> Every recurring review comment is evidence that the organization is paying the same cost repeatedly. Tricorder discovers those costs and recommends where to move learning upstream.

The change: from a five-step batch pipeline to a progressive system that earns access incrementally, accumulates structured artifacts, and applies domain-specific interpretation.

### Proposed trust model

Access is earned by demonstrating value. No level requires trust it hasn't justified.

| Level | Command | Access | Value delivered |
|-------|---------|--------|----------------|
| 0 | `discover` | Local filesystem only | Repository profile + archetype |
| 1 | `discover --history` | Local git only | Evolution timeline, hotspots |
| 2 | `analyze` | GitHub read | Review patterns, expertise map |
| 3 | `learn` | LLM API | Organizational learnings |
| 4 | `interpret` | LLM API + lens | Domain-specific recommendations |
| 5 | `improve` | LLM API | Improvement roadmap |

`tricorder discover` requires no credentials at all.

### Proposed CLI (v2 — not yet implemented)

```
tricorder discover    OWNER/REPO [--lens NAME]
tricorder discover    OWNER/REPO --history
tricorder probe       OWNER/REPO [--limit N] [--since YYYY-MM-DD]
tricorder analyze     OWNER/REPO [--since YYYY-MM-DD] [--limit N] [--force]
tricorder learn       OWNER/REPO [--visibility private|team|public] [--out DIR]
                                 [--provider anthropic|gemini] [--model NAME]
tricorder interpret   OWNER/REPO [--lens NAME]
tricorder improve     OWNER/REPO [--out DIR]
tricorder build       OWNER/REPO [--out PATH] [--name-map PATH]
tricorder demo        [--fast] [--no-pause]
tricorder --version
```

### Proposed artifact contract (v2 — not yet implemented)

Each level writes structured artifacts that subsequent levels read. Currently there are no `.tricorder/` artifacts — this is new.

```
.tricorder/
├── config.yml                    # storage location, lens, last run
├── repository-profile.yml        # Level 0 output
├── repository-fingerprint.json   # Level 0 output
├── contributors.json             # Level 1 output
├── hotspots.json                 # Level 1 output
├── repository-timeline.json      # Level 1 output
├── review-observations.json      # Level 2 output
├── review-patterns.json          # Level 2 output
├── expertise-map.json            # Level 2 output
├── learnings.json                # Level 3 output
├── standards-candidates.json     # Level 3 output
├── interpretations.json          # Level 4 output
├── improvement-plan.md           # Level 5 output
└── roadmap.json                  # Level 5 output
```

Default location: `.tricorder/` inside the repository being analyzed. Configurable via `~/.learn-from-work/config`.

### Proposed discipline lenses (v2 — not yet implemented)

A lens provides domain-specific interpretation for Level 4. Tricorder detects the likely lens from the repository fingerprint and proposes it.

#### What "validated" means

A lens is validated when:
1. A full synthesis run completes on a real production repository of that type
2. The findings are legible and actionable to someone who knows that domain
3. The category taxonomy and standard citations map accurately to real patterns in the output — findings are specific, not generic

The `analytics-engineering` lens met this bar on the cal-itp/data-infra run (172 PRs, June 2026). A key test: the composite radar matched informal prior knowledge about the team, confirming the synthesis was reading real signal rather than producing plausible-sounding noise.

No other lens has been through this process.

#### Lens status

| Lens | Status | Domain | Authorities |
|------|--------|--------|-------------|
| `analytics-engineering` | **Validated** — 1 production run | dbt, SQL, BigQuery/Snowflake | dbt Labs, Kimball, SQLFluff, dbt-project-evaluator |
| `product-engineering` | **Experimental** — named, not designed | Product software | — |
| `platform-engineering` | **Experimental** — named, not designed | Infrastructure, SRE | — |
| `security` | **Experimental** — named, not designed | Security engineering | — |

Experimental lenses have names and candidate authority lists but no taxonomy, no prompt design, and no validation run. They exist to reserve the namespace and signal intent. They will produce generic output if invoked. Implementing a new lens requires: category taxonomy design, authority selection, prompt calibration, and a validation run against a real repository of that type.

### Proposed status blocks (v2 — not yet implemented)

Every command ends with a block stating access used, completed work, and next action:

```
Tricorder — Review Analysis

Access used
  ✓ Pull requests (read)
  ✓ Review comments (read)
  No write operations performed.

Completed
  ✓ Repository Profile
  ✓ Review Patterns

Not yet unlocked
  ○ Organizational Learnings   →  tricorder learn

Next
  tricorder learn
```

---

## Part 3 — Migration path

### Command renames

v1 commands remain functional as aliases. No breaking changes.

| v1 (current) | v2 (proposed) | Notes |
|---|---|---|
| `ready` | absorbed into `discover` output | `discover` replaces the pre-flight check |
| `probe` | `probe` | Unchanged |
| `harvest` | `analyze` | Rename only — same behavior |
| `synthesize` | `learn` | Rename + artifact contract added |
| `render` | `build` | Rename — may gain additional output formats |
| — | `discover` | New command |
| — | `interpret` | New command |
| — | `improve` | New command |

### What carries forward unchanged

- The four synthesis analyses (per-PR extraction, reviewer fingerprints, author profiles, team gaps)
- The maturity path (`judgment → guidance → convention → rule → deterministic`)
- The Markdown report format
- The static HTML explorer
- The local cache at `~/.learn-from-work/cache/`
- The LLM provider layer (Anthropic + Gemini, config-driven)
- The cost probe

### What is new in v2

- `discover` command (no credentials required)
- `.tricorder/` artifact directory with structured outputs
- Lens detection and `interpret` command
- `improve` command
- Status blocks on every command
- Artifact storage config

### Source of truth during transition

Until v2 implementation lands:
- **[DESIGN.md](DESIGN.md)** describes both v1 behavior and v2 architecture decisions
- **[README.md](README.md)** describes only v1 (what works today)
- **[docs/EVOLUTION.md](docs/EVOLUTION.md)** narrates the design arc and records key decisions

README should not be updated to reference v2 commands until they are implemented.

---

## Deferred decisions

These were noted in the design discussion and not resolved:

- **`render` → `build`** — name not final
- **Artifact storage config UX** — what does `discover` output if `.tricorder/` is not writable?
- **Second lens** — which repository type gets the second validated lens? Python data pipelines and infrastructure-as-code are the candidates (issue #18)
- **Separating `learn` and `interpret`** — currently both use LLM and both are analytics-engineering-specific; will be separated when a second lens requires the distinction

---

## Open issues

| # | Title | Status |
|---|-------|--------|
| #22 | Update and evolve the design and product scope | Active — this branch |
| #15 | Second repo run — validate generalizability | Open |
| #16 | Trend detection across synthesis runs | Open |
| #18 | Switchable discipline lenses | Part of v2 spec |
