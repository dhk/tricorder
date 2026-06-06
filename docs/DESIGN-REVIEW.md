# Design Review — Tricorder v2 Brief

This file threads the critical review comments for the updated design brief.

## 1. High — Lens validation gate is still too loose

Section: `BRIEF.md` → "What remains experimental" / "Validation criteria for a lens"

The new validation bar is better than before, but it still reads like a definition that can be satisfied with a single successful run and a subjective judgment call. The brief says a lens is validated if the findings are "legible and actionable to a domain expert" and the taxonomy maps to real patterns, but it does not say who decides that, how much disagreement is acceptable, or what happens when the expert verdict is mixed.

Questions:
- Who is the domain expert responsible for validation, and is that person independent from the doc author?
- What is the rejection criterion if the run is partially legible but still drifts into generic advice?
- Why is one production repository enough to validate a lens that is supposed to generalize across a domain?

## 2. High — V1 to V2 transition is still not operationally defined

Section: `BRIEF.md` → "Migration notes" / "Proposed command aliases"

The brief now says v1 remains the source of truth, but it still does not define how the shipped CLI and artifacts evolve into the v2 surface. The alias table helps, but it is still just a naming map. It does not answer whether v2 replaces v1 commands, layers on top of them, or deprecates them one by one.

Questions:
- When v2 ships, are `harvest` and `synthesize` removed, aliased, or left intact?
- What is the minimum acceptance bar for considering v2 a replacement rather than a sidecar?
- Which user-facing command remains the canonical entry point during migration?

## 3. Medium — "Repository learning system" is broader than the evidence supports

Section: `BRIEF.md` → opening sections and "What tricorder is becoming"

The current evidence supports a dbt/SQL review-analysis tool that can expand into a broader learning framework. It does not yet support the stronger claim that tricorder is already a general-purpose repository learning system. That framing risks overpromising before the non-analytics lenses exist or have been calibrated.

Questions:
- Why not frame v2 as "analytics-engineering first, with later lens expansion" instead of a general learning system?
- What would disprove the claim that the architecture is lens-agnostic?
- How will the doc prevent readers from assuming product/platform/security lenses are already workable?

## 4. Medium — "Incremental trust" is still under-specified

Section: `BRIEF.md` → "What tricorder is becoming" / "What carries forward"

The document uses trust language, but it does not say what permissions, data sources, or user actions actually change across levels. Without that, "incremental trust" is mostly rhetorical. The v1 docs have a concrete access model; the v2 brief needs one too if this concept is meant to matter.

Questions:
- What new access does v2 require that v1 does not?
- What is the explicit trust boundary between discovery, analysis, and interpretation?
- If the permissions do not change, what exactly is being earned incrementally?

## 5. Medium — Lens definition is still ambiguous

Section: `BRIEF.md` → "Proposed progression" and "Lens status"

The brief uses "lens" as if the term were self-evident, but it is not operationally defined. Is a lens a taxonomy, a prompt pack, a standards set, an output template, or a combination of those? Without that, it is hard to tell what is actually experimental and what is just a new label for an existing prompt configuration.

Questions:
- Is a lens configuration data, code, or content?
- Can users author or select lenses, or are they fixed by the tool?
- How many lenses can coexist in one run?

## 6. Medium — The improvement-plan output has no concrete contract

Section: `BRIEF.md` → "Proposed progression" / "Improvement plan"

The brief ends in "Improvement plan," but it never says what that artifact contains or how it is produced. If it is an LLM-generated output, the doc should say so and account for the cost, token budget, and failure mode. If it is post-processing, then that should be explicit too.

Questions:
- Is the improvement plan a new synthesis call or a deterministic ranking of existing findings?
- What are the required fields in that artifact?
- How do you keep it from becoming generic action-item filler?

## 7. Low-Medium — Visibility model may conflict with the main use case

Section: `DESIGN.md` → "Outputs" / visibility model

The design still says team leads and managers are a target user, but the visibility model redacts author profiles in `team` mode. That is a tension worth resolving explicitly because author profiles are exactly the kind of evidence a manager would need for a growth conversation.

Questions:
- Is `team` visibility intended for sharing broadly, or for manager workflows?
- Why are author profiles redacted in the mode that seems most useful for team discussion?
- Should the visibility model be revised to preserve the specific evidence managers need while still protecting privacy?
