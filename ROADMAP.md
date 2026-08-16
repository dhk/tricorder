# Tricorder Roadmap

The roadmap is the current manifestation of product intent.

It should be read beneath the [Constitution](CONSTITUTION.md), [Product Vision](PRODUCT_VISION.md), and [Product Strategy](PRODUCT_STRATEGY.md). Issues and pull requests should trace to roadmap intent, and roadmap intent should trace upward to strategy and vision.

This document describes what we currently intend to improve, not every idea Tricorder may someday pursue.

## Current state

The v2 command surface is shipped:

**discover → analyze → learn → interpret → improve → build**

The current product already provides progressive access, repository profiling, git-history analysis, review-pattern extraction, expertise mapping, organizational learnings, discipline interpretation, improvement plans, and an explorer.

Generated judgments and discipline lenses remain experimental and require human review.

## Now — strengthen Show

### Make capability evidence more legible

Improve the way Tricorder presents:

- recurring review costs;
- standards candidates;
- repository-quality concerns;
- code-quality themes;
- expertise concentration;
- review coverage and gaps;
- trajectories over time where evidence is sufficient.

The goal is not more findings. It is more recognizable, inspectable, and actionable findings.

### Preserve provenance

Every important conclusion should remain traceable to the evidence that produced it, with clear separation between observation and inference.

### Improve lens validation

Continue validating discipline lenses against real repositories and external domain judgment before promoting them from experimental status.

## Next — strengthen Tell

### Intervention classification

Move from generic recommendations toward explicit intervention classes:

- education/coaching;
- skill/playbook;
- documentation;
- workflow hook/template;
- accountability/ownership change;
- repository improvement;
- deterministic check/CI;
- automation;
- retain human judgment.

### Proportional recommendations

Recommendations should explain why a particular mechanism fits the evidence and why a more restrictive mechanism is or is not justified.

### Repeated-cost framing

Make the cost of recurring human correction visible enough that teams can prioritize what is worth moving upstream.

## Later — close the capability loop

### Longitudinal comparison

Show whether repository, review, and process patterns change after an intervention.

### Intervention validation

Support questions such as:

- Did a repeated review theme disappear?
- Did a new check eliminate human correction?
- Did a workflow change reduce friction?
- Did knowledge become less concentrated?
- Did an intervention create new failure modes?

### Deliberate Do

Only after Tell is sufficiently trustworthy, support approved implementation of bounded improvements such as skills, workflow hooks, templates, deterministic checks, or other repository-local changes.

Shared-state or enforcement changes must remain explicit and reviewable.

## Research horizon

These belong in research until evidence earns roadmap commitment:

- a broader team-capability model beyond repository/review evidence;
- reliable process-quality inference from additional sources;
- integration with Work Ledger evidence;
- cross-repository or organization-wide capability synthesis;
- generalized promotion rules from observed practice to shared convention;
- business/product impact assessment.

## Not now

Tricorder should not become:

- an employee performance or ranking system;
- a developer productivity scoreboard;
- a generic engineering metrics dashboard;
- an autonomous live code reviewer;
- a system that infers business success without business evidence;
- a machine that standardizes every repeated behavior.
