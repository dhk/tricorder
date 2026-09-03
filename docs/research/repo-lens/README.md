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
| Handoff prompt | sent to Perplexity 2026-09-02 |
| Findings: Perplexity | received 2026-09-02: `findings/perplexity-findings.md` + `findings/perplexity-lenses/product-engineering-desktop.yaml`. Referenced `platform-engineering.yaml` and `detection-rubric.yaml` were not delivered (tracked as tricorder-8t5.10) |
| Findings: Claude | not started (tricorder-8t5.11) |
| Synthesis | blocked on the Claude findings pass (tricorder-8t5.11) |

## Tracking

Work is tracked in beads under epic `tricorder-8t5` (label `repo-lens`). Run `bd list -l repo-lens` for the tree and `bd ready` for what is unblocked.

## Implementation

The lens contract from the handoff prompt is implemented in `tricorder/lenses/` (loader, validator, detection, verification, prompt assembly) with the six lens files under `tricorder/lenses/data/`. Detection results on 2026-09-02: `block/berd` selects `product-engineering-desktop` (score 32, margin 28, both checks pass); `cal-itp/data-infra` is `mixed` with `analytics-engineering` 26 ahead of `platform-engineering` 23; `block/buzz` selects the parent `product-engineering` (11 vs 7) pending a mobile sub-profile.
