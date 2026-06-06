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

Tricorder v2 expands the current tool into a repository learning system.

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

### Proposed command aliases

| v2 concept | Suggested alias | Relationship to v1 |
|---|---|---|
| Repository discovery | `discover` | Replaces the front-end role of `ready` |
| History analysis | `discover --history` | Extends discovery with git-history inspection |
| Review analysis | `analyze` | Evolves the `harvest` + `synthesize` path |
| Learning extraction | `learn` | More explicit name for synthesis output |
| Interpretation | `interpret` | Applies a discipline lens to learning artifacts |
| Improvement planning | `improve` | Produces a prioritized roadmap |

### What carries forward

- The cache-first workflow
- Structured artifacts on disk
- A human-readable report as a primary output
- Incremental trust: users should get useful output before granting deeper access

---

## What remains experimental

The lens layer is the main experimental surface in v2.

### Validation criteria for a lens

A lens is validated only if all three are true:

1. A full synthesis run was completed against a real production repository of that type.
2. The resulting findings were legible and actionable to a domain expert.
3. The category taxonomy and standard citations mapped to real patterns instead of generic advice.

The analytics-engineering lens is validated by the cal-itp/data-infra run from June 2026.

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

## Migration notes

This brief is intentionally a bridge between versions.

- v1 remains the source of truth for shipped behavior until code changes land.
- v2 should be read as the next design target, not as a claim about the current CLI.
- Any implementation work should preserve the existing v1 user path until the v2 surface is ready to replace it.

---

## Why this change exists

The current tool already demonstrates that review history contains reusable signal.

The v2 proposal extends that insight from one validated domain into a broader learning system, but only where the evidence is strong enough to justify it.

The practical goal is the same in both versions: move learning upstream so the team pays the same cost less often.
