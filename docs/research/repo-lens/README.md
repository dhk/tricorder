# Research: repository lenses (`repo-lens`)

Opened 2026-09-02. Motivated by the known limitation recorded in [SKILL.md](../../../SKILL.md): the legacy synthesis prompts hardwire a dbt/SQL lens, so non-data repositories get off-domain findings. Test case: `block/berd`.

## Read in this order

1. [brief.md](brief.md) — the research questions, each traced to the code or design decision it is meant to fix.
2. [findings/](findings/) — one file per independent source, named `<source-slug>-findings.md`, all following [findings/TEMPLATE.md](findings/TEMPLATE.md). Lens YAML files from a source go in `findings/<source-slug>-lenses/`.
3. [handoff-prompt.md](handoff-prompt.md) — the brief, the Tricorder contract, the `block/berd` fingerprint, and the output format bundled into one self-contained prompt for a tool or person with no repository access. Copy it into Perplexity as-is.
4. `synthesis.md` — written only after two or more findings files exist. Per question: where sources agree, where they conflict and which is more credible, what only one source caught, and what remains unanswered.

## Why findings stay independent until synthesis

Each source answers the same brief without seeing the others' work. If a second source reads the first's findings before writing its own, it anchors on that framing and the second pass stops being an independent check. Synthesis is the first point at which the findings meet.

## Status

| Stage | State |
|-------|-------|
| Brief | written |
| Scaffold | written |
| Handoff prompt | written, not yet sent |
| Findings: Perplexity | pending |
| Findings: Claude | not started |
| Synthesis | blocked on two or more findings |
