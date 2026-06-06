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

**Review decision owner:** dhk owns final review decisions and acceptance/rejection outcomes.

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

**Status: Resolved — response and protocol added.**

Resolution: BRIEF now defines a concrete validation protocol (minimum evidence, scoring threshold, failure conditions, decision outcomes, and status recording requirements).

### Finding 2 — High: V1→V2 transition not operationally defined

The alias table is a naming map, not a lifecycle plan. Doesn't answer: are v1 commands removed, aliased, or left intact when v2 ships? What is the minimum bar for v2 being a replacement rather than a sidecar? Which command is the canonical entry point during migration?

**Status: Resolved — explicit cutover policy added.**

Resolution: BRIEF and DESIGN now describe an in-session weekend cutover target (v2 command surface primary, v1 retired after cutover validation) and include explicit cutover-commit recording language.

### Finding 3 — Medium: "Repository learning system" broader than evidence supports

The current evidence supports a dbt/SQL tool that can expand. It doesn't yet support the claim that tricorder is a general-purpose repository learning system. Risks overpromising before non-analytics lenses exist.

**Status: Resolved — narrowed by lens status and wording.**

Resolution: Analytics lens is now marked `Experimental` with strong evidence; validation remains required before full generalized claims.

### Finding 4 — Medium: "Incremental trust" under-specified

Trust language used throughout but no concrete definition of what permissions or data access changes across levels. The v1 docs have an explicit access model; the v2 brief needs one.

**Status: Resolved — trust model operationalized.**

Resolution: DESIGN now includes a per-level access contract table with data sources, network access, credentials, writes, and failure behavior.

### Finding 5 — Medium: Lens definition ambiguous

"Lens" is used as if self-evident but never operationally defined. Is it a taxonomy, a prompt pack, a standards set, an output template, or a combination? Without a definition it's hard to tell what's experimental vs an existing prompt configuration with a new name.

**Status: Resolved — lens definition added.**

Resolution: BRIEF now defines lens as taxonomy + prompt calibration + authority set, with explicit validation expectations.

### Finding 6 — Medium: Improvement-plan output has no concrete contract

The brief ends at "Improvement plan" but never says what the artifact contains or how it's produced. If LLM-generated, cost and failure mode should be stated. If post-processing, that should be explicit.

**Status: Resolved — output contract specified.**

Resolution: DESIGN defines improvement outputs as `.tricorder/improvement-plan.md` and `.tricorder/roadmap.json`, including command context and prerequisites.

### Finding 7 — Low-Medium: Visibility model conflicts with main use case

DESIGN.md names team leads and managers as a target user, but the visibility model redacts author profiles in `team` mode. Author profiles are exactly what a manager needs for a growth conversation. Tension not resolved.

**Status: Deferred — accepted tradeoff for v2 cutover.**

Resolution note: Current visibility model retained for this cutover window; revisit after v2 command-surface stabilization.

---

## Round 4

**Reviewer:** Copilot-reviewer  
**Date:** 2026-06-06  
**Commit reviewed:** `e4fb890`  
**Focus:** Cross-document contract consistency (BRIEF.md, DESIGN.md, docs/EVOLUTION.md vs shipped interface)

### Finding 1 — High: DESIGN.md now presents v2 CLI as current contract while BRIEF.md still frames v2 as proposed

**Section reference:** `DESIGN.md` (Version/Status header, CLI section) vs `BRIEF.md` (Status and boundary callouts)

**Problem:**
`DESIGN.md` states "design decisions finalized, implementation pending" but then defines the v2 CLI (`discover/analyze/learn/interpret/improve/build`) as if it were the active interface. `BRIEF.md` still says v2 is proposed and v1 CLI is the shipped surface. These two docs currently disagree on what "current contract" means.

**Questions:**
- Which document is normative for the user-visible CLI right now?
- Should `DESIGN.md` mark the CLI block as "target interface" until implementation lands?
- Do you want a single source-of-truth paragraph copied into both docs to prevent future drift?

**Proposed rewrite (for DESIGN.md CLI preface):**

```md
## CLI

Target v2 interface (design target; not yet implemented).  
Current shipped interface remains the v1 commands in `tricorder/cli.py`.
```

**Status: Resolved.**

Resolution: BRIEF and DESIGN now include explicit shipped-v1 vs target-v2 interface lines and cutover-commit switch language.

### Finding 2 — High: Command alias claim in DESIGN.md conflicts with shipped code

**Section reference:** `DESIGN.md` "v1 command aliases (still functional)" vs `tricorder/cli.py`

**Problem:**
`DESIGN.md` claims aliases (`harvest -> analyze`, `synthesize -> learn`, `render -> build`) are still functional, but the live CLI exposes only v1 commands. This is a hard factual mismatch, not just roadmap language.

**Questions:**
- Is alias functionality already implemented on this branch but not yet merged, or is it still planned?
- If planned, should the alias block move to a "Migration plan" subsection with explicit "not implemented" labeling?
- Do you want a CI doc-check to catch contract statements that contradict `tricorder/cli.py`?

**Status: Resolved.**

Resolution: Alias section now says "Planned aliases (not yet implemented)" and no longer claims active alias support.

### Finding 3 — Medium: Data baseline is inconsistent across docs (172/154 vs 190/184)

**Section reference:** `DESIGN.md` Status section vs `README.md` Status section and prior v1 docs

**Problem:**
The updated `DESIGN.md` now cites 172 harvested PRs / 154 with review activity, while `README.md` still cites 190 PRs and different totals. A core validation dataset should not vary across top-level documents without explanation.

**Questions:**
- Which run is canonical for v1 validation right now?
- Are these two different windows or two revisions of the same run?
- Should one paragraph be added to document why the baseline changed?

**Status: Resolved.**

Resolution: DESIGN and EVOLUTION now use `~172` and include an active-repository variability note.

### Finding 4 — Medium: EVOLUTION.md says v1 command rename is non-breaking, but DESIGN.md reads as if rename already happened

**Section reference:** `docs/EVOLUTION.md` "Command renames" vs `DESIGN.md` CLI section

**Problem:**
`docs/EVOLUTION.md` clearly frames renames as transition-era and non-breaking. `DESIGN.md` presents the renamed command set as the primary surface without equivalent transition framing. Same topic, two different implementation implications.

**Questions:**
- Should `DESIGN.md` mirror `docs/EVOLUTION.md` phrasing: "renames planned; v1 names remain functional until cutover"?
- What is the explicit cutover event for command vocabulary?

**Status: Resolved.**

Resolution: DESIGN now frames alias mappings as planned/not-yet-implemented and states explicit cutover conditions.

### Finding 5 — Medium: "Incremental trust" still lacks explicit permission matrix despite being central to v2 thesis

**Section reference:** `DESIGN.md` Trust model and status blocks

**Problem:**
The trust model is conceptually strong, but it still does not define the exact data/permission boundaries per level in a compact matrix. The text is narrative; the control model is implicit.

**Questions:**
- Can you add a one-table access matrix (`level`, `data sources`, `network`, `credentials required`, `writes`) to make trust boundaries auditable?
- What is the failure behavior when a level's required permission is absent?

**Status: Resolved.**

Resolution: Access matrix added under trust model with explicit failure behavior per level.

---

## Open questions

| Question | Raised in | Status |
|----------|-----------|--------|
| `render` → `build` — is the name final? | Design discussion | Resolved — final name is `build` |
| Artifact storage config UX — what does `discover` output if `.tricorder/` is not writable? | Design discussion | Resolved — ask for a folder location |
| Which repository type gets the second validated lens? | Issue #18 | Deferred — TBD; will determine and update |
| Should `learn` and `interpret` be separated now, or deferred until a second lens requires it? | Design discussion | Resolved — separate now |

---

## Resolution status

| Document | Round 1 | Round 2 | Round 3 | Final state |
|----------|---------|---------|---------|-------------|
| BRIEF.md | Restructured (v1/v2/migration) | Boundary hardened + lens criteria added | Findings reconciled | Updated in-session for weekend v2 cutover; review statuses reconciled |
| DESIGN.md | Rewritten for v2 architecture | — | Findings reconciled | Updated in-session for trust matrix, cutover framing, and alias status |
| docs/EVOLUTION.md | Written — design narrative | — | — | Ready for review |
