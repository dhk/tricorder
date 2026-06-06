# Tricorder v2 — Design Review Log

**Branch:** feat/design-evolution-22  
**PR:** [#23](https://github.com/dhk/tricorder/pull/23)  
**Documents under review:** BRIEF.md, DESIGN.md, docs/EVOLUTION.md  
**Period:** 2026-06-06

This document is a running record of the design debate on the v2 evolution. Each round captures the findings, the response, and the resolution. Unresolved questions are tracked at the bottom.

---

## Round 1

**Reviewer:** dhk  
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

**Reviewer:** External second-pass audit  
**Date:** 2026-06-06 ~14:20 PDT  
**Commit reviewed:** `09e4bf5` (BRIEF.md restructured)  
**Focus:** Whether the v1/v2 boundary was actually hard, and whether the scope expansion was defensible

### Finding 1 — High: Boundary still soft

The restructured brief still read like an implemented product contract. Despite the "not yet implemented" labels, the visual weight wasn't strong enough.

**Response: Partially rejected.**

The three-part restructure from Round 1 already addressed the substance of this finding. The labels existed. What was missing was visual prominence, not structure.

Fixed by adding blockquote callouts at two points: the document top (stating this is a design brief, Part 1 is shipped, Part 2 is not implemented) and immediately before Part 2 (stating explicitly that the codebase still exposes the v1 CLI and none of the commands or artifacts below exist yet).

### Finding 2 — High: No migration path for new commands and artifacts

Commands like discover/analyze/learn/interpret/improve and .tricorder storage were described without a migration path. Easy to read as a committed implementation plan.

**Response: Rejected.**

Part 3 was already an explicit migration path with a command alias table, a "what carries forward" list, and a source-of-truth callout. The finding was either based on an older version or didn't account for Part 3. No change made for this finding.

### Finding 3 — Medium: Scope expansion without a validation bar

The lens table used "Validated" vs "Planned" but never defined what validated means. Without a definition, the distinction is decorative — it doesn't prevent non-analytics lenses from devolving into generic AI commentary.

**Response: Accepted.**

This was a genuine gap. Added explicit lens validation criteria:

1. A full synthesis run completes on a real production repository of that type
2. Findings are legible and actionable to a domain expert in that field
3. The category taxonomy and standard citations map accurately to real patterns — findings are specific, not generic

Named cal-itp/data-infra (172 PRs, June 2026) as the evidence that met this bar for `analytics-engineering`.

Demoted non-analytics lenses from "Planned" to "Experimental — named, not designed" with an explicit warning that they will produce generic output if invoked. Noted that implementing a new lens requires: category taxonomy design, authority selection, prompt calibration, and a validation run.

### Questions from Round 2

**Q1: Should the brief be framed as a migration document with three sections: what exists now, what changes next, what remains experimental?**

Already done in Round 1. The "what remains experimental" tier was the one genuinely new thing from this question — addressed by the lens demotion and the "Experimental — named, not designed" status.

**Q2: Should the brief explicitly preserve v1 as the current source of truth until code catches up?**

Already done in Round 1 (source-of-truth section in Part 3, README callout). Reinforced in Round 2 by the boundary blockquote.

**Q3: What is the acceptance criterion for calling a new lens "validated" rather than "proposed"?**

Accepted as a genuine gap. Answered in BRIEF.md with three explicit criteria, one validated example, and a warning about what experimental lenses produce if invoked.

---

## Open questions

These were raised during the review process and are not yet resolved:

| Question | Raised in | Status |
|----------|-----------|--------|
| `render` → `build` — is the name final? | Design discussion | Open — deferred |
| Artifact storage config UX — what does `discover` output if `.tricorder/` is not writable? | Design discussion | Open — deferred |
| Which repository type gets the second validated lens? Python data pipelines and IaC are candidates. | Issue #18 | Open |
| Should `learn` and `interpret` be separated into distinct commands now, or deferred until a second lens requires it? | Design discussion | Deferred — will be separated when second lens is implemented |

---

## Resolution status

| Document | Round 1 | Round 2 | Final state |
|----------|---------|---------|-------------|
| BRIEF.md | Restructured (v1/v2/migration) | Boundary hardened + lens criteria added | Ready for review |
| DESIGN.md | Rewritten for v2 architecture | — | Ready for review |
| docs/EVOLUTION.md | Written — design narrative | — | Ready for review |
