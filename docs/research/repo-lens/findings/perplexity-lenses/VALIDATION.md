# Validation: product-engineering-desktop on block/berd

**Date:** 2026-09-03 · **Lens:** product-engineering-desktop v1 · **Cache:** 159 merged PRs, 2026-08-12 to 2026-09-02, 146 with review activity · **Cost:** about $3 at the probed $0.019 per PR · **Runner:** `tricorder-synthesize.py block/berd` with the lens auto-detected from the GitHub tree and recorded in `lens-detection.json`.

The previous synthesis of the same cache, produced under the dbt prompts on 2026-09-02, was set aside as `synthesis-dbt-lens-2026-09-02/` and is compared below. No LLM output was reused between the two runs; see bead tricorder-8t5.17 for why that had to be done by hand.

## Result: pass on every criterion in DESIGN.md

| Criterion | Bar | Measured |
|---|---|---|
| Detection selects the lens with margin | score ≥ min_score 10, margin ≥ 5 | score 32, margin 28 |
| composition_check | pass | pass |
| review_path_check | ≥ 70% of inline comments on tagged paths | 94% (444 of 471) |
| Phase 1 `other` share | ≤ 15% | 4.0% (41 of 1031 patterns) |
| Smoke checks across all four phases | zero hits | zero |
| Phase 1 errors | zero | zero |

## What the lens found that the dbt lens could not

Phase 4 reported ten gaps, one per axis, every one with a primary-source citation from the lens. Four are the axes the research singled out as the ones a service or data lens would miss:

- **dependency-supply-chain, blind spot.** No advisory or license auditing for either npm or crates. Confirmed against the repo on 2026-09-02: `renovate.json` exists, `deny.toml` does not.
- **capability-minimality, knowledge gap.** Per-window permission scoping and deny-by-default are raised but not consistently. The repo has three capability files.
- **webview-csp, blind spot.** Nobody reviews `tauri.conf.json` CSP for unsafe-inline or remote sources.
- **unsafe-discipline, blind spot.** No SAFETY justification review and no watch on unsafe growth in the dependency tree.

The tooling-gate rule worked. The dbt-lens run reported "TypeScript strict-mode and type safety review" as a blind spot. The desktop run does not list it as a gap, because `tsc` is a present gate and Phase 4 was told to treat that dimension as institutionalized; its output uses that word.

## Comparison with the dbt-lens run on the same cache

| | dbt lens (2026-09-02) | desktop lens (2026-09-03) |
|---|---|---|
| Gaps | 7 | 10 |
| Gaps mapped to a lens axis | 0 (no axes) | 10 of 10 |
| Citations | TypeScript strict mode, Testing pyramid, WCAG 2.1, Google's code review guide, Conventional Commits, The Checklist Manifesto, one `None` | Playwright best practices, Rustonomicon, cargo-deny, Tauri CSP, Tauri capabilities, Rules of Hooks, WCAG 2.2, TELEMETRY.md, Tauri config, Tauri signing |
| Tauri-specific findings | none | 5 |
| Smoke-check hits | none | none |

The old run did not cite dbt on berd. The model had partly corrected for the prompt on its own, which is why the earlier framing "off-domain citations" understated the problem. The real loss was what the old lens never asked about: the IPC boundary, capabilities, CSP, signing, sidecars, telemetry policy. Those are now five of the ten gaps.

## Defects observed

- One Phase 1 category outside the lens enum: `build-release-scripts`, a file tag the model used as a category on a handful of patterns. Harmless here, but Phase 1 output should be validated against the enum and coerced to `other` with a note. Filed as part of the follow-up below.
- Standard citations are often bare URLs rather than the authority name. Cosmetic; the report appendix maps them.

## Decision

`product-engineering-desktop` moves from `experimental` to `validated` per the promotion rule in DESIGN.md: one successful production-repository evaluation. It remains the only validated lens.

## Raw validation output

```
# Validation — block/berd — product-engineering-desktop v1

lens source: cache (lens-detection.json)   checks: [('composition_check', True), ('review_path_check', True)]
gates: ['biome', 'tsc', 'playwright', 'vitest', 'lefthook', 'tauri-capabilities']

Phase 1: 146 PRs, 0 errors, 1031 patterns
  other share: 4.0%  (threshold 15%)  -> PASS
  categories outside the lens enum: ['build-release-scripts']
  top categories: [('correctness', 318), ('testing', 116), ('maintainability', 111), ('ipc-boundary', 71), ('error-handling', 63), ('react-hygiene', 47), ('documentation', 41), ('other', 41), ('e2e-coverage', 38), ('accessibility', 34), ('security', 24), ('release-updater', 22)]
  maturity: {'guidance': 402, 'rule': 241, 'judgment': 313, 'convention': 71, 'deterministic': 4}
  top citations: [('https', 92), ('Web Content Accessibility Guidelines (WC', 20), ('Rules of React — https', 17), ('block/berd TELEMETRY.md and README (seco', 3), ('Security (trust boundaries and the IPC l', 2), ('Rules of React', 2), ('Playwright Best Practices — https', 2), ('Content Security Policy (CSP) — https', 1)]

Smoke checks (must be empty):
   none -> PASS

Phase 4: 10 gaps, 5 strengths, 4 candidates
  gaps by axis: {'e2e-practice': 1, 'unsafe-discipline': 1, 'dependency-supply-chain': 1, 'webview-csp': 1, 'capability-minimality': 1, 'react-hygiene': 1, 'accessibility': 1, 'telemetry-privacy': 1, 'packaging-sidecars': 1, 'updater-signing': 1}
  mentions ipc-boundary               yes
  mentions capability-minimality      yes
  mentions dependency-supply-chain    yes
  mentions e2e-practice               yes

  gaps:
   - [knowledge_gap] (e2e-practice) Playwright E2E coverage for new UI surfaces  § https://playwright.dev/docs/best-practices
   - [blind_spot] (unsafe-discipline) Unsafe block justification and unsafe growth in the dependency tree  § https://doc.rust-lang.org/nomicon/
   - [blind_spot] (dependency-supply-chain) Dependency supply-chain hygiene — advisory and license auditing for both npm and crates  § https://github.com/EmbarkStudios/cargo-deny
   - [blind_spot] (webview-csp) CSP configuration review — unsafe-inline/remote source scrutiny in tauri.conf.json  § https://v2.tauri.app/security/csp/
   - [knowledge_gap] (capability-minimality) Capability minimality — per-window permission scoping and deny-by-default review  § https://v2.tauri.app/security/capabilities/
   - [knowledge_gap] (react-hygiene) React effect dependency hygiene and cleanup beyond what Biome catches  § https://react.dev/reference/rules/rules-of-hooks
   - [blind_spot] (accessibility) Accessibility beyond Biome a11y static rules — keyboard operability and ARIA semantics  § https://www.w3.org/TR/WCAG22/
   - [blind_spot] (telemetry-privacy) Telemetry event review against published policy — path sanitization, identifier hashing, opt-out  § https://github.com/block/berd
   - [blind_spot] (packaging-sidecars) Per-platform sidecar packaging and target-triple correctness  § https://v2.tauri.app/reference/config/
   - [knowledge_gap] (updater-signing) macOS notarization and Windows code-signing review for release artifacts  § https://v2.tauri.app/distribute/sign/macos/

  institutionalized / already-deterministic mentions: yes

Old dbt-lens run for comparison: 7 gaps
   - [blind_spot] TypeScript strict-mode and type safety review: no reviewer comments on type annotations, inference g  § TypeScript strict mode
   - [knowledge_gap] Test strategy and coverage for edge cases: reviewers like caregullin identify complex behavioral edg  § Testing pyramid
   - [blind_spot] Accessibility (WCAG) review for UI components: no evidence of any reviewer ever checking keyboard na  § WCAG 2.1
   - [knowledge_gap] Performance regression review: the polling interval concern (30s database query cost) was raised but  § None
   - [coverage_gap] Naming, readability, and code style feedback: across the reviewed PRs no reviewer comments address f  § Google's Code Review Developer Guide — readability
   - [blind_spot] Conventional Commits enforcement: no evidence that commit message format is reviewed or enforced, de  § Conventional Commits
   - [knowledge_gap] Validation rollback and release preparation failure handling: rollback of tracked files on failed pr  § The Checklist Manifesto (Gawande) — irreversible a
  old run smoke hits: []
```
