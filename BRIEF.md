# Tricorder — Product Brief

**Version:** 2.0 — shipped  
**Status:** Historical migration record. Written during the v2 design phase (June 2026,
reviewed across 4 rounds in [docs/DESIGN-REVIEW.md](docs/DESIGN-REVIEW.md)) to describe
the planned v1 → v2 cutover as a still-pending proposal. **The cutover has since
happened** — read the rest of this document as design history, not current status.  
**Source of truth for shipped behavior:** [README.md](README.md) and [tricorder/cli.py](tricorder/cli.py) — not this document.

**Current shipped interface:** the v2 command set (`discover`/`analyze`/`learn`/`interpret`/`improve`/`build`), documented in [README.md](README.md).
v1 commands (`ready`/`harvest`/`synthesize`/`render`/`probe`/`demo`) remain available only
as legacy dispatch — see `_LEGACY_SCRIPTS` in [tricorder/cli.py](tricorder/cli.py).

> **Note:** Part 2 below describes what was, at the time, a next-version proposal.
> Everything in it has since shipped; treat "not yet implemented" language in Part 2
> as a historical snapshot of intent, not a current gap.

---

## What tricorder was at v1 (superseded — see [README.md](README.md) for the current CLI)

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

The immediate intent is to cut over to the v2 interface this weekend while preserving the current analysis pipeline and widening the kinds of repository evidence tricorder can interpret.

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

A lens is validated only if it passes the protocol below.

1. Minimum evidence
- At least 2 production repositories in the target archetype
- At least 1 external domain reviewer (not the lens author)

2. Scoring threshold
- Clarity score >= 4/5 from at least 2 domain reviewers
- Actionability score >= 4/5 with >= 70% reviewer agreement

3. Failure conditions
- Generic recommendation rate > 30%
- Standards-citation mismatch rate > 20%

4. Decision rule
- Allowed outcomes: `Validated`, `Experimental`, `Rejected`
- A validation decision records the date and commit hash that granted the status

The analytics-engineering lens is currently marked `Experimental` with strong evidence from the cal-itp/data-infra run (June 2026) and is expected to move to `Validated` after a second successful production-repo evaluation.

### Lens status

| Lens | Status | Notes |
|---|---|---|
| analytics-engineering | Experimental | Strong evidence from cal-itp/data-infra; pending second production-repo evaluation |
| product-engineering | Experimental — named, not designed | Likely to produce generic output until calibrated |
| platform-engineering | Experimental — named, not designed | Likely to produce generic output until calibrated |
| security | Experimental — named, not designed | Likely to produce generic output until calibrated |

### Experimental warning

If a non-analytics lens is invoked before validation, the output should be treated as exploratory. It may be directionally useful, but it is not evidence that the lens works.

---

## Migration notes

This brief is intentionally a bridge between versions.

- v1 remains the source of truth for shipped behavior until the cutover commit lands.
- v2 is the active target for this session and weekend cutover.
- This project currently has a single maintainer, so migration can be fast and does not require a long deprecation window.
- The cutover target is: v2 command surface becomes primary; v1 command surface is retired after cutover validation in this session.

### Weekend cutover checklist

1. Implement the v2 command surface in CLI code.
2. Update README and HOWTO to document v2 commands as the primary interface.
3. Keep a short compatibility note for prior v1 command names only if needed during the transition.
4. Mark the cutover commit hash in this brief and in `docs/DESIGN-REVIEW.md`.

---

## Why this change exists

The current tool already demonstrates that review history contains reusable signal.

The v2 proposal extends that insight from one validated domain into a broader learning system, but only where the evidence is strong enough to justify it.

The practical goal is the same in both versions: move learning upstream so the team pays the same cost less often.
