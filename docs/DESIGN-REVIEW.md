# Tricorder v2 — Design Review Log

**Branch:** feat/design-evolution-22  
**PR:** [#23](https://github.com/dhk/tricorder/pull/23)  
**Documents under review:** BRIEF.md, DESIGN.md, docs/EVOLUTION.md  
**Period:** 2026-06-06

This document is a running record of the design debate on the v2 evolution. Each round captures the findings, the response, and the resolution. Unresolved questions are tracked at the bottom.

**Roles:**
- **dhk** — product owner
- **Claude-author** — document author, responds to findings
- **Copilot-reviewer** — independent reviewer, raises findings

---

## Round 1

**Reviewer:** dhk  
**Role:** dhk (author)  
**Date:** 2026-06-06 ~14:10 PDT  
**Commit reviewed:** `82bc9fe` (BRIEF.md first draft)  
**Focus:** Overall framing of BRIEF.md

### Findings

**1. Present-tense problem**  
The brief read like a product contract describing current behavior, not a design evolution document. The scope jump from v1 (dbt/SQL tool) to v2 (progressive discovery system) felt larger than an evolution because there was no explicit boundary between what is shipped and what is proposed.

**2. Missing callouts**  
No clear separation for: current CLI vs proposed command set, existing artifact formats vs new ones, validated vs planned lenses, whether README/DESIGN remain the v1 source of truth during the transition.

**3. Structural question**  
Why not frame it explicitly as "v1 today / v2 next / migration path"?

### Response

Accepted in full.

Rewrote BRIEF.md as three explicit parts:
- **Part 1** — v1 current state: CLI, outputs, scope, all described as shipped
- **Part 2** — v2 proposed design: every section labeled "not yet implemented"
- **Part 3** — Migration path: command alias table, what carries forward, source-of-truth callout

Added Status column to the lens table (Validated vs Planned).

---

## Round 2

**Reviewer:** Copilot-reviewer  
**Date:** 2026-06-06 ~14:20 PDT  
**Commit reviewed:** `09e4bf5` (BRIEF.md restructured)  
**Focus:** Whether the v1/v2 boundary was actually hard, and whether the scope expansion was defensible

### Finding 1 — High: Boundary still soft

The restructured brief still read like an implemented product contract. Despite the "not yet implemented" labels, the visual weight wasn't strong enough.

**Response: Partially rejected.**

The three-part restructure from Round 1 already addressed the substance of this finding. The labels existed. What was missing was visual prominence, not structure.

Fixed by adding blockquote callouts at two points: the document top and immediately before Part 2, both stating explicitly that nothing below is implemented and the v1 CLI remains the current surface.

### Finding 2 — High: No migration path for new commands and artifacts

Commands like discover/analyze/learn/interpret/improve and .tricorder storage were described without a migration path.

**Response: Rejected.**

Part 3 was already an explicit migration path with a command alias table, a "what carries forward" list, and a source-of-truth callout. Finding did not account for Part 3. No change made.

### Finding 3 — Medium: Scope expansion without a validation bar

The lens table used "Validated" vs "Planned" but never defined what validated means. Without a definition, the distinction is decorative.

**Response: Accepted.**

Added explicit lens validation criteria:
1. A full synthesis run completes on a real production repository of that type
2. Findings are legible and actionable to a domain expert
3. Category taxonomy and standard citations map to real patterns — findings are specific, not generic

Named cal-itp/data-infra (172 PRs, June 2026) as the evidence that met this bar.

Demoted non-analytics lenses from "Planned" to "Experimental — named, not designed."

### Questions from Round 2

**Q1:** Should the brief be framed as a migration document with three sections: what exists now, what changes next, what remains experimental? — Already done in Round 1.

**Q2:** Should the brief explicitly preserve v1 as the current source of truth until code catches up? — Already done in Round 1, reinforced in Round 2.

**Q3:** What is the acceptance criterion for calling a new lens "validated"? — Accepted as a genuine gap. Answered with three explicit criteria in BRIEF.md.

---

## Round 3

**Reviewer:** Copilot-reviewer  
**Author response:** Claude-author  
**Date:** 2026-06-06 ~21:33 PDT  
**Commit:** `3095c44` (rewrote BRIEF.md, added review findings)  
**Focus:** Operational gaps remaining after Round 2; new BRIEF.md rewrite proposed alongside findings

*Note: This round included a rewritten BRIEF.md submitted by Copilot-reviewer alongside the findings. The rewrite was accepted by Claude-author and cherry-picked onto the branch as the new canonical version.*

### Finding 1 — High: Lens validation gate still too loose

The validation bar reads like it can be satisfied with a single run and a subjective judgment call. No definition of who decides, how much disagreement is acceptable, or what the rejection criterion is for a mixed verdict. One production run may not be enough to claim a lens generalizes across a domain.

**Status: Open — needs response.**

### Finding 2 — High: V1→V2 transition not operationally defined

The alias table is a naming map, not a lifecycle plan. Doesn't answer: are v1 commands removed, aliased, or left intact when v2 ships? What is the minimum bar for v2 being a replacement rather than a sidecar? Which command is the canonical entry point during migration?

**Status: Open — needs response.**

### Finding 3 — Medium: "Repository learning system" broader than evidence supports

The current evidence supports a dbt/SQL tool that can expand. It doesn't yet support the claim that tricorder is a general-purpose repository learning system. Risks overpromising before non-analytics lenses exist.

**Status: Open — needs response.**

### Finding 4 — Medium: "Incremental trust" under-specified

Trust language used throughout but no concrete definition of what permissions or data access changes across levels. The v1 docs have an explicit access model; the v2 brief needs one.

**Status: Open — needs response.**

### Finding 5 — Medium: Lens definition ambiguous

"Lens" is used as if self-evident but never operationally defined. Is it a taxonomy, a prompt pack, a standards set, an output template, or a combination? Without a definition it's hard to tell what's experimental vs an existing prompt configuration with a new name.

**Status: Open — needs response.**

### Finding 6 — Medium: Improvement-plan output has no concrete contract

The brief ends at "Improvement plan" but never says what the artifact contains or how it's produced. If LLM-generated, cost and failure mode should be stated. If post-processing, that should be explicit.

**Status: Open — needs response.**

### Finding 7 — Low-Medium: Visibility model conflicts with main use case

DESIGN.md names team leads and managers as a target user, but the visibility model redacts author profiles in `team` mode. Author profiles are exactly what a manager needs for a growth conversation. Tension not resolved.

**Status: Open — needs response.**

---

## Open questions

| Question | Raised in | Status |
|----------|-----------|--------|
| `render` → `build` — is the name final? | Design discussion | Open — deferred |
| Artifact storage config UX — what does `discover` output if `.tricorder/` is not writable? | Design discussion | Open — deferred |
| Which repository type gets the second validated lens? | Issue #18 | Open |
| Should `learn` and `interpret` be separated now, or deferred until a second lens requires it? | Design discussion | Deferred |

---

## Resolution status

| Document | Round 1 | Round 2 | Round 3 | Final state |
|----------|---------|---------|---------|-------------|
| BRIEF.md | Restructured (v1/v2/migration) | Boundary hardened + lens criteria added | Rewritten by dhk, accepted | Pending Round 3 responses |
| DESIGN.md | Rewritten for v2 architecture | — | Finding 7 open | Pending Round 3 responses |
| docs/EVOLUTION.md | Written — design narrative | — | — | Ready for review |
