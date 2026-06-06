# Tricorder — Product Brief

**Version:** 2.0 (in design)  
**Status:** Migration brief — v1 is current, v2 is proposed  
**Source of truth for shipped behavior:** [README.md](README.md) and [tricorder/cli.py](tricorder/cli.py)

> **Important:** Part 2 describes the next version only. Nothing in Part 2 is implemented yet.
>
> The current shipped surface remains the six-command v1 CLI in [tricorder/cli.py](tricorder/cli.py#L17-L37).

---

## What tricorder is today

Tricorder v1 is a dbt/SQL review analysis tool.

It reads merged pull request history, review activity, and repo context, then produces a structured report about recurring review patterns, reviewer focus, author growth, and team gaps.

The shipped surface is still the current six-command CLI:

- `ready`
- `probe`
- `harvest`
- `synthesize`
- `render`
- `demo`

The current architecture is still the existing two-phase flow: harvest to cache, then synthesize to report.

---

## What tricorder is becoming

> **Boundary:** the rest of this document is a v2 proposal, not a description of shipped behavior.
>
> If a section below says "planned", "experimental", or "proposed", read it as future state only.

Tricorder v2 expands the current tool into a repository learning system — starting with analytics engineering, where the evidence is already strong, and extending to other domains as each lens is validated.

The intent is not to replace v1 on day one. The intent is to preserve the current analysis pipeline while widening the kinds of repository evidence tricorder can interpret.

### Proposed progression

```
Local filesystem          -> Repository profile
Local git history         -> Evolution timeline
GitHub read access        -> Review patterns
LLM analysis              -> Organizational learnings
Lens interpretation       -> Recommendations
Full synthesis            -> Improvement plan
```

### Proposed command set

v2 replaces v1 commands. v1 commands will be removed when v2 ships — there is not enough usage to warrant maintaining both surfaces.

| v2 command | Replaces | What changes |
|---|---|---|
| `discover` | `ready` | Local-only, no credentials required |
| `discover --history` | — | New — git history analysis |
| `analyze` | `harvest` + `synthesize` | Renamed; artifact contract added |
| `learn` | `synthesize` (learning phase) | Renamed; explicit output artifacts |
| `interpret` | — | New — lens application |
| `improve` | — | New — improvement planning |
| `build` | `render` | Renamed |
| `probe` | `probe` | Unchanged |

### What carries forward

- The cache-first workflow
- Structured artifacts on disk
- A human-readable report as a primary output
- Incremental trust: users should get useful output before granting deeper access

---

## What remains experimental

The lens layer is the main experimental surface in v2.

### What a lens is

A lens is a combination of three things: a **category taxonomy** (the named dimensions used to classify review patterns for a domain), a **prompt calibration** (the instructions that tell the LLM how to interpret evidence in that domain), and an **authority set** (the named standards used to ground recommendations — e.g. dbt Labs style guide, Kimball, SQLFluff). All three must be designed and validated together. A lens is not just a prompt swap — changing the taxonomy changes what the output measures.

### Validation criteria for a lens

A lens is validated only if all three are true:

1. A full synthesis run was completed against a real production repository of that type.
2. The resulting findings were legible and actionable to a domain expert.
3. The category taxonomy and standard citations mapped to real patterns instead of generic advice.

The analytics-engineering lens is validated by the cal-itp/data-infra run from June 2026.

Meeting this bar confirms the lens works for that repository. It does not guarantee the lens generalizes to all repositories of that type. Generalizability requires additional runs.

### Lens status

| Lens | Status | Notes |
|---|---|---|
| analytics-engineering | Validated | Backed by the cal-itp/data-infra synthesis run |
| product-engineering | Experimental — named, not designed | Likely to produce generic output until calibrated |
| platform-engineering | Experimental — named, not designed | Likely to produce generic output until calibrated |
| security | Experimental — named, not designed | Likely to produce generic output until calibrated |

### Experimental warning

If a non-analytics lens is invoked before validation, the output should be treated as exploratory. It may be directionally useful, but it is not evidence that the lens works.

---

## Improvement plan

The improvement plan (Level 5, `tricorder improve`) is an LLM call that reads all prior artifacts and produces a prioritized roadmap. Cost is roughly equivalent to one synthesis run (~$0.015–0.02 per prior artifact consumed, total typically under $0.50 for a standard run).

The output has three required sections: prioritized findings (drawn from learnings and interpretations, ranked by leverage type), recommended next actions (tooling, documentation, process, architecture — with a maturity path target for each), and what not to do (explicit deprioritization with reasoning). The third section is the quality gate — a plan without explicit deprioritization is generic. If the output contains only positive recommendations, treat it as a failed run.

## Visibility model

Three visibility tiers control what is included in output:

| Tier | Author profiles | Reviewer fingerprints | Patterns + gaps | Intended use |
|------|----------------|----------------------|----------------|--------------|
| `private` | Full | Full | Full | Personal analysis, local only |
| `team` | Redacted | Full | Full | Broad sharing with the team — author profiles removed to avoid naming individuals publicly |
| `public` | Removed | Anonymized | Anonymized | External sharing, demos |

`team` mode is for broad sharing, not manager workflows. For growth conversations, use `private` mode and share selectively. The distinction is intentional: author profiles contain findings about specific individuals and should not be distributed to the full team without the subject's knowledge.

---

## Migration notes

This brief is intentionally a bridge between versions.

- v1 remains the source of truth for shipped behavior until v2 implementation lands.
- v2 should be read as the next design target, not as a claim about the current CLI.
- v1 commands will be replaced, not aliased — there is not enough usage to warrant maintaining both surfaces.
- **Cutover definition:** v2 is considered a replacement when `discover`, `analyze`, `learn`, and `build` are all implemented and the full pipeline completes successfully on at least one repository.

---

## Why this change exists

The current tool already demonstrates that review history contains reusable signal.

The v2 proposal extends that insight from one validated domain into a broader learning system, but only where the evidence is strong enough to justify it.

The practical goal is the same in both versions: move learning upstream so the team pays the same cost less often.
