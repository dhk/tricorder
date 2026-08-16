# Tricorder Product Strategy

Product strategy describes how Tricorder tests whether the product vision is becoming true.

The vision is durable. The strategy is falsifiable. It should change when evidence says our current bets are wrong.

## Strategic objective

Help teams build better by making capability visible, identifying where it is fragile, and proposing interventions that raise the standard.

## Core product bet

A repository and its review history contain enough evidence to reveal meaningful aspects of team capability.

If that is true, Tricorder should be able to help a team see not just activity, but recurring standards, repeated correction, concentrations of expertise, process weaknesses, repository-quality concerns, and opportunities to move knowledge upstream.

The current repository/review corpus is the first evidence source, not necessarily the final boundary of the product.

## Adoption wedge

The first useful experience should answer:

> What does this repository reveal about how this team builds, where it is strong, and what it repeatedly pays to correct?

A useful first run should surface findings recognizable enough that experienced team members say, "yes, that is us," while preserving enough evidence that they can challenge a bad interpretation.

Trust in the diagnosis earns the right to propose interventions.

## Show → Tell → Do as product strategy

### Show: capability becomes inspectable

Measure whether Tricorder can reliably surface evidence-backed observations across:

- recurring review patterns;
- standards and convention candidates;
- code and repository-quality signals;
- review coverage and concentration of expertise;
- repeated friction and correction;
- author/reviewer trajectories where evidence supports them;
- process and workflow characteristics observable in repository evidence.

Success is not the number of findings. It is whether findings are recognizable, specific, evidenced, and useful.

### Tell: recommendations fit the observed gap

Recommendations should classify the likely intervention rather than default to automation.

Candidate intervention classes include:

- education or coaching;
- skills/playbooks;
- documentation;
- workflow hooks and templates;
- distribution of accountability;
- repository or architecture improvement;
- deterministic checks and CI;
- automation;
- continued human judgment where codification would be harmful.

We should measure whether knowledgeable users judge recommendations as relevant, actionable, proportional, and grounded in the evidence.

### Do: appropriate improvements become durable

Tricorder should eventually help encode approved improvements into the team's working system.

Success is not "automation shipped." Success is evidence that the chosen intervention reduced repeated cost or improved capability without introducing disproportionate friction.

## Capability dimensions

Tricorder should resist collapsing capability into one score. We should instead maintain a multidimensional model that can include:

### Code quality

Evidence that produced code is correct, maintainable, understandable, testable, and consistent with relevant standards.

### Repository quality

Evidence that the repository makes good work easier: structure, documentation, testing, conventions, tooling, ownership, and maintainability.

### Standards and up-leveling

Evidence that useful expectations are becoming explicit, teachable, consistently understood, and increasingly encoded where appropriate.

### Process quality

Evidence that proposal, implementation, review, validation, and merge processes reliably help work converge toward good outcomes without unnecessary repeated cost.

### Capability distribution

Evidence about where important knowledge and judgment are concentrated, shared, missing, or fragile.

### Technical leverage

Evidence that an intervention improves downstream work: repeated review disappears, a defect class is prevented, onboarding becomes easier, a reusable standard spreads, or a manual check becomes reliably encoded.

Business impact is outside the current measurement boundary unless Tricorder gains trustworthy product/business evidence.

## The upstream maturity hypothesis

One strategic hypothesis is that recurring human correction can often be moved upstream through a maturity progression:

**notice → explain → teach → guide → standardize → automate**

This is not a mandatory ladder. The product should learn which mechanisms fit which kinds of knowledge.

Important questions include:

- Which findings deserve education rather than enforcement?
- When should a convention become a workflow hook?
- When is a deterministic check better than an LLM instruction?
- When does automation destroy useful judgment?
- How much recurrence is enough evidence to recommend institutionalization?
- How do we recognize innovative practice that appears first in only one person or one repository?

These remain research questions until evidence supports stronger rules.

## Team improvement requires trajectory

A static report can diagnose. A capability system should return later and ask what changed.

The strategy should increasingly support before/after or period-over-period questions:

- Did recurring review themes decrease?
- Did a new standard change review behavior?
- Did expertise become less concentrated?
- Did CI or automation remove a repeated human check?
- Did repository improvements reduce friction?
- Did an intervention create new failure modes?

This feedback loop is essential to distinguish recommendations that sound plausible from interventions that actually help.

## Human judgment is part of the system

Tricorder should not attempt to mechanically decide which individual behaviors become team standards.

Evidence can show prevalence, variation, recurrence, concentration, and outcomes. Human reviewers decide whether a practice is appropriate, transportable, and worth adopting.

This is especially important where the corpus is small, the practice is novel, or causal attribution is weak.

## Measures of strategic progress

We should prefer measures tied to product value over generic usage metrics.

Useful measures include:

1. **Recognition** — knowledgeable users agree that surfaced patterns accurately describe their repository/team context.
2. **Evidence quality** — findings can be traced to sufficient, relevant source evidence.
3. **Recommendation acceptance** — users judge proposed interventions worth considering or adopting.
4. **Intervention diversity** — recommendations appropriately span education, process, standards, tooling, and automation rather than collapsing into one mechanism.
5. **Repeated-cost reduction** — recurring review or quality problems decrease after an intervention.
6. **Capability distribution** — important team knowledge becomes less dependent on isolated heroics where that is desirable.
7. **Trajectory visibility** — users can see whether capability is improving, stable, or changing in meaningful ways.
8. **Trust** — teams are willing to grant deeper evidence access because earlier levels produced inspectable value.

## Explicit non-measures

The following should not become success metrics for Tricorder:

- developer rankings;
- commits per person;
- PRs per person;
- lines of code;
- review comments per person as a productivity proxy;
- a universal engineering-quality score;
- business impact inferred without business evidence.

## Current strategic bets

### Bet 1: review history contains high-value tacit standards

This is the most mature bet and the foundation of the current product.

### Bet 2: repository context materially improves interpretation

Review patterns without repository structure and existing enforcement can produce redundant or incorrect recommendations. The progressive repository-learning architecture should improve signal.

### Bet 3: capability gaps can be mapped to different intervention types

Tricorder should become good at recognizing whether a gap looks like education, workflow, ownership, repository quality, deterministic tooling, or automation.

### Bet 4: showing repeated organizational cost creates urgency

"We keep paying for this in review" is more actionable than a generic best-practice recommendation.

### Bet 5: longitudinal evidence can validate improvement

The product becomes substantially more valuable when it can show that a chosen intervention changed how the team builds.

## Unknowns

We do not yet know:

- the right measurement model for overall team capability;
- how far beyond repository/review evidence Tricorder should expand;
- how to infer process quality robustly from partial repository signals;
- which intervention taxonomy will survive real use;
- how much evidence is sufficient to call a pattern durable;
- how well findings generalize across repository types and engineering disciplines;
- how to validate longitudinal improvement without confusing correlation with causation;
- where Work Ledger evidence should eventually join Tricorder evidence.

These are strategy questions, not reasons to invent certainty.
