# Tricorder Constitution

This document governs what Tricorder is allowed to become.

It is the durable whole of the project: the principles, boundaries, evidence standards, and agency model that should survive individual features, roadmaps, and implementation choices.

The product hierarchy is:

**Constitution → Product Vision → Product Strategy → Roadmap → Issues and PRs**

When lower-level intent conflicts with this document, the lower-level intent changes.

## 1. Tricorder is about team capability

Wingman is centered on the person. Work Ledger is centered on the work. Tricorder is centered on the team's capability to build well together.

Tricorder asks:

> Given that this team is trying to build something together, how well is it building, where is capability fragile, and what would raise the standard?

It does not decide whether the team chose the right product strategy. That requires business, market, product, and organizational context outside Tricorder's current evidence boundary.

## 2. Building well is multidimensional

No single metric defines team capability.

Tricorder may examine evidence about code quality, repository quality, standards and conventions, review quality, process quality, distribution of expertise and accountability, repeated friction and correction, workflow consistency, technical leverage, and whether capability is improving over time.

Activity is not quality. Velocity is not quality. Review volume is not quality. A team is not reducible to a score.

## 3. Show → Tell → Do

Tricorder follows an evidence-to-action progression.

### Show

Make the current system inspectable. Show how work is built, reviewed, corrected, accepted, and maintained. Show recurring patterns, standards, gaps, concentrations of expertise, repository conditions, and process characteristics.

Show must distinguish observation from interpretation.

### Tell

Propose what appears likely to improve capability. Recommendations may include skills, education, workflow hooks, templates, checklists, clearer accountability, documentation, repository changes, deterministic checks, automation, or review-process changes.

A recommendation is a hypothesis until later evidence supports it.

### Do

Where appropriate, encode an improvement into the team's operating system.

Do must remain proportionate, inspectable, and reversible. Changes that alter shared state, enforcement, permissions, or organizational behavior require explicit human approval.

## 4. Move knowledge upstream deliberately

Repeated human correction is evidence that the system may be asking people to remember what the system itself could carry.

Tricorder should help move useful knowledge upstream, but not every judgment should become a rule.

A useful maturity path is:

**notice → explain → teach → guide → standardize → automate**

Different problems should stop at different points. Tricorder should prefer the least restrictive mechanism that reliably improves the work.

## 5. Strengthen capability without manufacturing conformity

The purpose of team analysis is not to make everyone work identically.

Strong teams contain differentiated expertise, judgment, and working styles. Tricorder should identify where those differences create value, where they create fragility, and what is genuinely transferable.

A practice does not become good merely because it is common. A practice does not become irrelevant merely because only one person currently demonstrates it.

Human judgment remains necessary when deciding what should become shared practice.

## 6. Study the system, not the worth of the people

Tricorder may identify reviewer expertise, author trajectories, recurring feedback, or concentration of knowledge because these are signals about team capability.

It must not become a performance-review, employee-ranking, productivity-scoring, or surveillance system.

A repeated issue associated with one person may reflect unclear guidance, missing tooling, poor onboarding, architectural traps, ambiguous ownership, inadequate review, or an individual learning need. Tricorder must not silently collapse these possibilities into a judgment about that person's worth or performance.

Likewise, a highly effective reviewer may indicate valuable expertise and also institutional fragility if important standards exist only in that person's head.

The question is:

> What does this evidence tell us about the capability of the team and the system around it?

## 7. Capability should become increasingly independent of heroics

Expertise matters. Hero dependency is fragile.

Where the same person must repeatedly remember, detect, explain, or repair the same class of problem, Tricorder should consider whether some of that capability can become durable through education, standards, workflow, tooling, repository structure, or automation.

The goal is not to remove experts. It is to let expert knowledge raise the team's baseline.

## 8. Evidence before assertion

Every consequential claim should be traceable to inspectable evidence.

Tricorder should distinguish:

- **Observed** — directly supported by repository, history, review, or other source evidence;
- **Inferred** — a synthesis or interpretation from observed evidence;
- **Proposed** — a recommended intervention;
- **Validated** — an intervention or interpretation supported by subsequent evidence and human review.

Generated judgments must never be presented as ground truth merely because an LLM produced them.

## 9. Trajectory matters

A repository, team, reviewer, author, standard, or process is not a snapshot.

Tricorder should look for direction of change where the evidence permits it: recurring problems becoming less frequent, standards becoming explicit, review burden moving upstream, repository quality improving, expertise becoming less concentrated, and interventions reducing repeated correction.

The purpose is improvement, not diagnosis frozen in time.

## 10. Repository and review data are evidence, not the whole world

Repositories and review histories are unusually valuable records of how teams build and judge work. They are not complete representations of team capability.

Tricorder should be explicit about what its evidence can and cannot support. It should not infer business impact, product-market correctness, interpersonal dynamics, or organizational intent when those signals are absent.

Future evidence sources may broaden the product, but each must earn its place by materially improving the quality of capability assessment.

## 11. Trust expands with access

Tricorder earns access progressively.

Every increase in access must unlock a visibly better class of insight. The product must state what it reads, what leaves the local environment, what credentials are used, what artifacts are written, and what may be publishable.

Private repository data, review text, identities, and generated profiles are sensitive. Publication and external transmission must be deliberate and inspectable.

## 12. Reversibility governs intervention

The more an action changes shared state or constrains future behavior, the more human control is required.

Additive local artifacts may be generated freely. Recommendations should be reviewable before adoption. Changes to shared workflows, CI, configuration, permissions, or enforcement require explicit approval.

## 13. Improvement must close the loop

A proposed improvement is not success.

Where possible, Tricorder should return to the evidence after an intervention and ask whether the team actually improved.

Did repeated review cost fall? Did the same defect class disappear? Did standards become more consistent? Did knowledge concentration decrease? Did a workflow change improve quality without creating new friction?

The product should learn from consequences, not merely produce recommendations.

## 14. Unknowns remain unknown

Tricorder will frequently operate where evidence is incomplete and causal attribution is weak.

The project should record uncertainty explicitly rather than filling gaps with generic best practices or confident language.

A product that knows the limits of its evidence is more useful than one that pretends to know more than it does.

## Governance

Changes to this constitution should be rare and explicit.

`PRODUCT_VISION.md` describes what Tricorder is trying to become. `PRODUCT_STRATEGY.md` describes how we test whether that vision is working. `ROADMAP.md` records current intent. Issues and pull requests implement that intent.
