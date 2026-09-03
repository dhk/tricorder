# Tricorder documentation

## Current reference

- [README](../README.md) — concise product overview, install, and v2 command surface
- [HOWTO](../HOWTO.md) — authoritative v2 operating guide
- [Privacy and data flow](PRIVACY.md) — trust boundary, storage, sharing, and deletion
- [Contributing](../CONTRIBUTING.md) — development, tests, fixtures, and review-data safety
- [Security](../SECURITY.md) — supported versions and private vulnerability reporting
- [DESIGN](../DESIGN.md) — v2 architecture and product decisions
- [SKILL](../SKILL.md) — agent-oriented technical specification
- [Explorer README](../explorer/README.md) — explorer data shape and local serving
- [Synthetic review audit](case-studies/synthetic-review-audit/README.md) — key-free before/audit/after case study with explicit evidence boundaries
- [Research passes](research/README.md) — briefs, handoff prompts, and independent findings that de-risk design decisions; currently `repo-lens` (per-archetype lenses, test case `block/berd`)

## Historical design and reference

These documents preserve decisions and proposals. They are not the authority for
the shipped CLI when they conflict with current reference or command `--help` output.

- [BRIEF](../BRIEF.md) — v1-to-v2 migration brief
- [EVOLUTION](EVOLUTION.md) — product history and v2 rationale
- [DESIGN-REVIEW](DESIGN-REVIEW.md) — historical design-review record
- [EQUIP-DESIGN](EQUIP-DESIGN.md) — unshipped/future product design
- [DEMO](../DEMO.md) — historical demo material

The legacy top-level Python scripts remain executable for compatibility. New docs,
examples, and integrations should use the v2 package commands.
