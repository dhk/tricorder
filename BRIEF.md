# Tricorder — product brief

**Version:** v2 command surface shipped

**Status:** Current product summary; migration details below are historical.

**Operational authority:** [README.md](README.md), [HOWTO.md](HOWTO.md), and
command `--help` output.

Tricorder is a repository learning system. It progressively reads local repository
evidence, git history, GitHub review records, and LLM-generated interpretations to
make recurring team knowledge inspectable and actionable.

## Current product boundary

The authoritative interface is:

```text
discover → analyze → learn → interpret → improve → build
```

The access model is progressive: local files and git require no credentials;
`analyze` adds GitHub read access; `learn`, `interpret`, and `improve` transmit
selected artifacts to a configured LLM provider; `build` creates a portable explorer
data file. See [docs/PRIVACY.md](docs/PRIVACY.md) before using private repository data
or publishing output.

The six-level implementation and artifact chain are shipped. Generated analysis and
discipline lenses remain experimental and require human review. Tricorder is not a
performance evaluation system or a substitute for live code review.

## v1 compatibility (historical reference)

Tricorder v1 was calibrated for dbt/SQL review analysis and used `ready`, `probe`,
`harvest`, `synthesize`, `render`, and `demo`. Those commands remain available via
legacy script dispatch so existing callers continue to work. New docs and
integrations should use v2.

| v1 workflow | v2 authority |
|---|---|
| readiness | `discover` |
| harvest | `analyze` |
| synthesis | `learn` |
| rendering | `build` |

The cache-first workflow, human-readable reports, maturity path, reviewer
fingerprints, author profiles, team gaps, and static explorer carried forward.

## Experimental lens criteria

A lens should be called validated only after evidence from at least two production
repositories and review by an external domain expert, with recorded clarity,
actionability, and error-rate results. Until such a record exists, lens output is
experimental. The analytics-engineering lens has production evidence from the
original cal-itp/data-infra run but remains marked experimental pending the complete
validation protocol; other lenses are less calibrated.

## Historical migration decision

The v2 design broadened Tricorder from a dbt/SQL-specific pipeline into progressive
repository learning while preserving the proven synthesis internals. The migration
chose one repository and retained legacy dispatch rather than splitting the product
or breaking compatibility. [docs/EVOLUTION.md](docs/EVOLUTION.md) records the design
history; it is not the source of truth for current command behavior.

The practical goal is unchanged: identify repeated review costs and help teams move
the resulting knowledge upstream into guidance, tooling, and automation.
