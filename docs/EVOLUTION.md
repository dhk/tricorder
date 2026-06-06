# Tricorder — Design Evolution

> How a dbt/SQL analysis tool became a repository learning system.

---

## Where it started

Tricorder v1 was a focused tool with a specific job: read the merged PR history of a dbt/SQL analytics repository and return a map of what the team knows, what it misses, and what is ready to institutionalize.

It ran in five steps: `ready` → `probe` → `harvest` → `synthesize` → `render`.

The pipeline was validated on cal-itp/data-infra in June 2026 — a public dbt/BigQuery analytics team with 172 harvested PRs spanning three months. The synthesis returned four analyses: per-PR pattern extraction, reviewer fingerprints, author growth profiles, and a team gap analysis. The output was a Markdown report and an interactive HTML explorer deployed to GitHub Pages.

The design was intentionally narrow. Broad scope produces vague output. Calibrating the category taxonomy and standard citations to a specific domain — dbt, SQL, Kimball, SQLFluff — made findings specific enough to act on.

---

## What the first run revealed

The cal-itp run produced results that were immediately legible to anyone who had worked with the team: review quality concentrated in one high-signal reviewer, the broader team defaulting to low-signal approvals, and a pattern of substantive SQL issues appearing only in PR discussions — never in CI.

This was the validation: the synthesis was reading real signal, not producing plausible-sounding noise. The composite radar chart made the concentration visible at a glance.

But the run also surfaced a harder question. Once you have a map of what the team knows and what it misses, what do you do with it?

The answer requires something the v1 tool did not have: an interpretation layer. A list of recurring review comments tells you *what* the team discusses. It does not tell you *why it matters*, *how serious it is*, or *what to do first*. That requires a framework — a set of standards specific to the domain — and a way to apply it consistently across different repository types.

The second question was scope. The v1 pipeline was explicitly scoped to dbt/SQL. The category taxonomy, the standard citations, the prompt design — all calibrated for analytics engineering. Output on any other repository type would degrade immediately.

But the underlying problem — teams continuously generating and then discarding organizational knowledge — is not specific to dbt. It is present in every repository with an active review practice. The question was whether to stay narrow or address the general case.

---

## The design discussion

The v2 design discussion (issue #22) arrived at five key decisions.

### 1. Progressive trust, not a credential gate

The v1 pipeline required two credentials before it produced anything: a GitHub token and an LLM API key. Users invested trust before seeing value.

V2 inverts this. `tricorder discover` runs on the local filesystem with no credentials. It reads the repository to understand what it is — archetype, technology fingerprint, contributor count, tooling gaps. This is the trust funnel: something interesting before any investment.

GitHub access is earned at Level 2. LLM API access is earned at Level 3. Each level must produce something worth seeing before the next is unlocked.

### 2. Lens detection, not user configuration

The domain-specificity that made v1 findings actionable is preserved in v2 through discipline lenses. A lens provides the interpretive framework: which standards apply, which authorities to cite, how to read the patterns for this type of repository.

Rather than asking users to select a lens, tricorder detects the likely archetype from the repository fingerprint and proposes it. `dbt_project.yml` detected → analytics-engineering lens proposed. Users can override; they do not need to configure from scratch.

The `analytics-engineering` lens is the validated lens. It is where the category taxonomy, standard citations, and prompt design from v1 live. Other lenses ship as corresponding repository types are validated.

### 3. The artifact contract

V1 produced outputs — a Markdown report, a `data.js` file for the explorer. These were designed for humans.

V2 writes structured artifacts at each level that subsequent levels read. The artifact contract makes every analysis stage the foundation for the next:

```
repository-profile.yml
    ↓
contributors.json + hotspots.json
    ↓
review-patterns.json + expertise-map.json
    ↓
learnings.json + standards-candidates.json
    ↓
interpretations.json
    ↓
improvement-plan.md + roadmap.json
```

Artifacts are human-readable (YAML/JSON/Markdown), written to `.tricorder/` in the repository being analyzed, and reusable by external tools. The future MCP integration — exposing artifacts as resources consumable by AI agents — depends on this contract.

### 4. Command renames

The v1 command names described the pipeline's internal mechanics: harvest, synthesize, render. V2 renames the vocabulary to describe what users experience.

| v1 | v2 | What changed |
|----|-----|--------------|
| `ready` | — | Absorbed into `discover` output |
| `probe` | `probe` | Kept — cost planning is still useful |
| `harvest` | `analyze` | Describes the user-visible action (analyze the review history) |
| `synthesize` | `learn` | Describes the output (organizational learnings) |
| `render` | `build` (TBD) | Still under discussion |
| — | `discover` | New — local filesystem + git, no credentials |
| — | `interpret` | New — lens application (Level 4) |
| — | `improve` | New — improvement planning (Level 5) |

The v1 commands remain functional during the transition. The rename is not a breaking change.

### 5. Principled evolution, not a rewrite

The v1 synthesis internals are preserved. The per-PR extraction, reviewer fingerprints, author growth profiles, and team gap analysis from v1 become the `learn` phase (Level 3) of v2. They are still the analytics-engineering lens.

The v2 architecture wraps them: `discover` (new front-end), `analyze` (harvest renamed), `learn` (synthesize renamed with artifact contract), `interpret` (new lens layer), `improve` (new planning phase).

Separating `learn` and `interpret` into distinct phases is the right long-term architecture. In practice, both currently require LLM calls and both produce outputs specific to the analytics-engineering domain. They will be separated in implementation once a second repository type is validated — when the lens layer needs to actually vary.

---

## What v2 is

A repository learning system that:

- starts with no credentials and produces something interesting immediately
- earns access progressively, producing visible value at each step
- detects the repository type and applies the corresponding discipline lens
- writes structured artifacts that accumulate into a knowledge model
- makes the underlying evidence visible at every stage

The broader thesis: a team's review history contains the implicit standards that govern their codebase. Making those standards explicit is the first step toward encoding them anywhere useful — as documentation, as tooling, as CI gates, or as inputs to AI agents assisting the work.

---

## What stays the same

- The maturity path: `judgment → guidance → convention → rule → deterministic`
- The core outputs: reviewer fingerprints, author growth profiles, team gap analysis
- The analytics-engineering lens: same taxonomy, same standard citations, same prompt design
- The local cache: append-only, incremental, resumable
- The static HTML explorer

---

## What changed

- The entry point: `discover` before `analyze`, no credentials required to start
- The trust model: explicit levels with access transparency at each step
- The artifact contract: structured outputs designed to be consumed, not just read
- The scope: analytics-engineering becomes one lens among several, not the only target
- The vocabulary: command names describe user outcomes, not pipeline internals
- The status block: every command ends with a summary of access used, completed work, and next action

---

## What's deferred

- Separate `learn` and `interpret` into distinct phases — deferred until a second repository type validates that the lens layer needs to vary
- Implement non-analytics-engineering lenses — deferred until the second repo run
- MCP integration — deferred until the artifact contract is stable across two validated runs

---

## Open questions

These were noted during the design discussion and not resolved:

- **`render` → `build`?** Whether to rename `render` to `build` or something else is still open. The v1 name describes the HTML output; v2 may produce multiple artifact formats from the same step.
- **Artifact storage config UX** — what does `tricorder discover` output when `.tricorder/` cannot be written to the current directory? What does the config error look like?
- **Second lens validation** — which repository type gets the second lens? Python data pipelines and infrastructure-as-code are the candidates from issue #18.

---

## Issue tracking

| # | Title | Status |
|---|-------|--------|
| #22 | Update and evolve the design and product scope | Active — this branch |
| #15 | Second repo run — validate generalizability | Blocked on lens design stabilizing |
| #16 | Trend detection across synthesis runs | Open |
| #18 | Switchable persona by repo type | Renamed "discipline lenses" — part of v2 spec |
