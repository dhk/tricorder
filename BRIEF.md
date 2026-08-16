# Tricorder — product brief

This file is a compatibility summary for readers and older links. It is not the product authority.

The governing hierarchy is:

1. [CONSTITUTION.md](CONSTITUTION.md) — enduring principles and boundaries.
2. [PRODUCT_VISION.md](PRODUCT_VISION.md) — what Tricorder is trying to become and why.
3. [PRODUCT_STRATEGY.md](PRODUCT_STRATEGY.md) — how the vision is measured and tested.
4. [ROADMAP.md](ROADMAP.md) — the current manifestation of intent.
5. Issues and pull requests — implementation of that intent.

Implementation architecture remains documented in [DESIGN.md](DESIGN.md). Operational behavior is defined by [README.md](README.md), [HOWTO.md](HOWTO.md), and command `--help` output.

## Current product summary

Tricorder is a repository learning and team-capability system. It progressively reads local repository evidence, git history, GitHub review records, and generated interpretations to make recurring standards, quality signals, expertise concentration, and repeated correction inspectable and actionable.

The authoritative v2 interface is:

```text
discover → analyze → learn → interpret → improve → build
```

The access model is progressive: local files and git require no credentials; `analyze` adds GitHub read access; `learn`, `interpret`, and `improve` transmit selected artifacts to a configured LLM provider; `build` creates a portable explorer data file. See [docs/PRIVACY.md](docs/PRIVACY.md) before using private repository data or publishing output.

Generated analysis and discipline lenses remain experimental and require human review. Tricorder is not a performance-review system, a developer ranking system, or a substitute for live code review.

## Historical compatibility

Tricorder v1 was calibrated for dbt/SQL review analysis and used `ready`, `probe`, `harvest`, `synthesize`, `render`, and `demo`. Those commands remain available through legacy dispatch. New documentation and integrations should use v2.

The cache-first workflow, human-readable reports, maturity path, reviewer fingerprints, author profiles, team gaps, and static explorer carried forward.

[docs/EVOLUTION.md](docs/EVOLUTION.md) records the design history; it is not the source of truth for current product intent or command behavior.
