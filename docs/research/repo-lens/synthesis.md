# Synthesis: repository lenses

Two independent passes answered the same [brief](brief.md) without seeing each other's work: Perplexity on 2026-09-02 ([tricorder-lens-methodology-research.md](tricorder-lens-methodology-research.md), with [its lens files](findings/perplexity-lenses/)) and a Claude subagent on 2026-09-03 ([findings/claude-findings.md](findings/claude-findings.md), with [its lens files](findings/claude-lenses/)). The Claude pass was barred from the Perplexity documents and from the shipped lens files, and its header states what it read. This document compares them per question, says which source is more credible where they disagree, lists what only one caught, and records what remains open. It closes with the changes the comparison triggers in the shipped lenses.

Context the passes did not have: between them, the desktop lens was implemented, validated on block/berd ([VALIDATION.md](findings/perplexity-lenses/VALIDATION.md)), and the repository tree was fetched. Where a real measurement settles a question both passes could only estimate, it is noted.

## Q1. Composition detection

**Agree.** Both name GitHub Linguist as the reference implementation: content-only, exclusion-first, byte-weighted, maintainer-overridable through `.gitattributes`. Both treat framework-required manifests (`tauri.conf.json`, `Cargo.toml`, `pnpm-workspace.yaml`) as strong evidence and AI-assistant files as no evidence at all, citing the AGENTS.md adoption figure. Both say monorepos are partitioned by the package manager's declared members, not by the tool.

**Conflict: how much to ignore.** Perplexity's ignore list covers AI-assistant files and community-health files. Claude goes further, on Linguist's own `vendor.yml` and `documentation.yml`: `.github/` is vendored, and `README`, `CHANGELOG`, `CONTRIBUTING`, `LICENSE`, `docs/`, `examples/` are documentation, so none should score toward any archetype. Perplexity's platform lens keeps `.github/workflows/*.yml` as a weak positive signal. Claude is more credible here because it quotes the maintainers' classification of those paths and because the same file appears in repositories of every kind; a weak signal that fires everywhere only adds noise to the margin. **Triggered change:** extend the global ignore list and drop the workflows signal from the platform lens.

**Only Claude caught.** Biome's "domains" auto-enable framework rules from `package.json` dependencies, which is a maintainers' precedent for a second-order signal Tricorder does not use yet: read declared dependencies (react, playwright, vitest) as evidence without executing anything. Also the concrete workspace-partition primitives (Cargo `[workspace]` members, pnpm packages, npm workspaces, Turborepo's `apps/` and `packages/` convention) as the unit for per-package scoring.

**Only Perplexity caught.** go-enry as an embeddable Linguist port, should Tricorder ever want per-file classification locally.

**Unanswered.** Neither found a source on dependency-based fingerprinting beyond Biome; Nx's documentation was unreachable for Claude.

## Q2. Archetype taxonomy

**Agree.** Both adopt Backstage's small-core, open-extension model and conclude that `product-engineering` is too broad; both propose sub-profiles under it and both land block/berd in `product-engineering-desktop` with the same reasoning: archetype describes the artifact being engineered, not its subject matter.

**Conflict: the top level.** Perplexity keeps Tricorder's five archetypes. Claude argues that `security` and `agent-engineering` are not artifact kinds but what an artifact does, and that no published taxonomy (Backstage, crates.io, PyPI, Borges et al.) has such buckets at the top level; it recommends treating them as secondary overlays. Claude's argument is stronger and matches how Tricorder already behaves: `security` exists as a `--focus-on` area, and after the ignore list the `security` lens has almost no way to win detection. **Decision needed**, recorded as a bead: reclassify `security` and `agent-engineering` as overlays that add categories, axes, and authorities on top of a primary artifact lens.

**Only Claude caught.** Borges, Hora and Valente 2016, the peer-reviewed six-domain classification of 2,500 repositories, and its observation that GitHub carries no domain metadata, which is the empirical case for content-based detection. PyPI's `Environment ::` classifiers as a second registry vocabulary. Claude's sub-profile list is also longer: desktop, mobile, web-frontend, backend-service, library-sdk, cli. The shipped set now has desktop and mobile.

**Measured since.** The Q7 replay in both passes was on the truncated fingerprint; the real tree confirms berd's `src-tauri/tauri.conf.json`, three capability files, and per-platform config, and detection scores it 32 with margin 28.

## Q3. Review standards per archetype

**Agree.** Near-total overlap on the desktop lens's authority set: the Tauri security documents, the Rust API Guidelines and Clippy, the Rustonomicon, cargo-deny and cargo-audit, the Rules of React and Biome, Playwright's best practices, WCAG 2.2. Both mark the Unsafe Code Guidelines as not authoritative (Perplexity cites its own "not maintained" notice; Claude does not cite it at all). Both found no standards-body source for desktop telemetry consent.

**Only Claude caught, and worth adopting.** Several primary sources that sharpen existing axes:

- Tauri's isolation pattern, command scopes ("deny always supersedes the allow scope"; "command developers need to ensure that there are no scope bypasses possible"), and the application-lifecycle-threats page. The scopes statement is the best single citation for why capability minimality is a judgment axis.
- The Rust std-dev-guide safety-comments policy and Clippy's `undocumented_unsafe_blocks` lint, which mechanizes the SAFETY-comment half of the `unsafe-discipline` axis. This raises that axis's enforceability from judgment-only to partial.
- Apple's notarization requirement as a primary Apple document, and Microsoft's Authenticode page, alongside the Tauri signing pages.
- WCAG2ICT, the W3C note applying WCAG to non-web software, which is what a desktop app is from the operating system's side.
- TypeScript's `strict` flag family as the primary source for the `typescript-strictness` axis, where Perplexity cited typescript-eslint.
- For the platform lens: Docker's building best practices with hadolint, Kubernetes configuration best practices, the SRE book's four golden signals, and OpenAPI, which give the platform lens the container, manifest, and observability axes it lacked.

**Only Perplexity caught.** cargo-geiger for unsafe counting across the dependency tree, and the Biome accessibility rule group as the mechanizable subset of the accessibility axis.

**Unanswered by both.** A primary standard for desktop telemetry review. Both fall back to the repository's own `TELEMETRY.md`, marked secondary.

## Q4. Deterministic versus judgment

**Agree.** Both map Tricorder's ladder onto Clippy's `allow / warn / deny` levels and onto Google's enforce-versus-advise split, and both reject CMMI-style organisational maturity as the wrong kind of ladder. Both conclude no published vocabulary matches Tricorder's five words and that Tricorder should keep them and cite the mapping.

**Only Claude caught.** The precise semantics from the Google Tricorder paper: an analyzer is admitted to code review only if it points out an actual issue at least 90 percent of the time, and it is switched off when "not useful" clicks reach 10 percent. And from the 2018 case study: the two tiers are pre-commit checks that block unless overridden, versus analyses that surface but do not block. **Triggered change:** define `deterministic` as "enforced as a blocking check" and place warning-only tooling at `rule`; the shipped lenses' `enforceable_by` entries should say whether a gate blocks.

**Only Perplexity caught.** rustc's own six lint levels including `expect` and `forbid`, which give the ladder finer steps than Clippy's three.

## Q5. Pattern category taxonomy

**Agree.** Same literature (Mäntylä and Lassenius; Beller et al.; Bacchelli and Bird; Sadowski et al.), same conclusion: one domain-neutral core with per-lens extensions, and Conventional Comments classifies intent rather than topic and belongs in a separate field if anywhere.

**Conflict: the core set.** Perplexity's core has ten entries and is what shipped: `correctness, security, testing, documentation, style, performance, error-handling, maintainability, dependencies, other`. Claude's has thirteen: it splits `maintainability` into `design-structure` and `naming`, adds `process`, and adds `question`. The strongest point is `question`: Bacchelli and Bird's card sort found understanding-seeking comments to be among the most frequent kinds, and a core without that category files them under `other`, which is exactly the resolution loss the brief describes. Claude also cites Bosu et al. 2015 on which comment types reviewers find useful, which Perplexity did not. Claude is more credible on the composition of the core. **Decision needed**, recorded as a bead: add `question` and `naming` to the core, and consider `process`. The cost is a change to every shipped lens and to the explorer's radar, so it should be one deliberate version bump rather than drift.

**Measured since.** The berd validation put 4.0 percent of patterns in `other` under the ten-item core, below the 15 percent bar, so the shipped core is adequate; the question is whether `question` and `naming` would make Phase 2 fingerprints sharper, not whether the current core is broken.

## Q6. Confidence, mixed repositories, abstention

**Agree.** No published classifier exposes an abstention threshold for this problem; both propose `min_score` and `min_margin`; both choose 10 and 5 by construction; both reject composite lenses; both keep the 0.7 review-path threshold; both want the checks to run before money is spent.

**Only Claude caught, and the more important upgrade.** The formal grounding: Chow's reject option and modern selective classification (El-Yaniv and Wiener; Geifman and El-Yaniv), where the threshold is chosen for a target risk rather than a target coverage. That is the correct orientation for Tricorder, since a wrong lens is expensive and an abstention is cheap, and it turns "thresholds are a design choice" into "thresholds are a risk setting to calibrate," which is what the calibration bead should do.

**Conflict: what a secondary lens contributes.** Perplexity: attach the runner-up's axes as a secondary Phase 4 section. The shipped implementation does this, reported only with direct evidence. Claude: the secondary lens contributes file tags, extra Phase 1 categories on the paths it covers, and its `must_not` list, but never Phase 4 absence findings, because absence findings from two domains is the blending the research exists to prevent; and it sets a concrete admission bar, the secondary must tag at least 15 percent of comment paths the primary does not. Claude's rule is tighter and its rationale is sound. **Triggered change:** keep the secondary section but restrict it to evidence-backed observations, never absence-is-a-finding, and adopt the 15 percent bar; on berd, `bb-cli/` at 5.5 percent falls below it, which matches the shipped decision to handle the CLI with a file tag.

**Conflict: what a failed check does.** Claude downgrades the outcome to `mixed`; the shipped implementation refuses to run without `--force`. These are compatible: refusing is the stricter form. No change.

**Only Claude caught.** A `counter_signal_check` that reports which counter-signals matched next to the selection so a human can see what argued against the choice. Cheap and useful; triggered as a small change to `discover` output.

## Q7. Validation on block/berd

**Agree.** Both replay the old detector to `agent-engineering` 11 over `security` 8, both call it wrong, and both select `product-engineering-desktop` under their rubrics. Both pass composition and review-path checks.

**Differences are about evidence available, not judgment.** Perplexity scored 25 assuming the standard Tauri layout; Claude scored 19 on confirmed evidence and 35 if the layout was standard, and recorded `expected_score_min: 19` so validation would not depend on unconfirmed files. That caution was right in method. The real tree has since confirmed the layout, and the shipped detector measures 32 with margin 28. Claude's review-path share is 471 of 471 because its file tags also cover `LAWS/` and `.github/`; the shipped lens tags 444 of 471. Either passes.

**Only Claude caught.** The observation that a comment-path histogram at extension and top-level-directory resolution can only support plausibility claims per axis; whether reviewers actually raise an axis is a Phase 1 result. The berd validation then delivered that result: ten Phase 4 gaps, one per axis, and the oversight-density measurement showed that the capability and CSP files were touched in 21 PRs with zero human comments.

## Open gaps, merged

Resolved since the passes ran:

- berd's `src-tauri/` contents: confirmed by tree fetch. `tauri.conf.json`, `capabilities/{default,session-window,voice-buddy}.json`, per-platform configs present; `deny.toml` absent, which the validation run reported as a blind spot.
- Category `other` share: measured at 4.0 percent on berd.

Still open, by owner:

- Threshold calibration on a labeled corpus of 20 to 30 repositories across the sub-profiles, choosing thresholds for zero misclassification at maximum coverage (both passes; bead 8t5.12).
- No primary standard for desktop telemetry review (both passes; bead 8t5.14 watch list).
- No authoritative unsafe-Rust checklist; the std-dev-guide policy plus `undocumented_unsafe_blocks` now cover the documentation half (Perplexity's gap, narrowed by Claude).
- Biome lacks full Rules-of-Hooks parity (Perplexity).
- No primary standard for IaC change semantics; Claude's platform lens adds container, manifest, and observability axes from primary sources but still no plan-review or blast-radius authority (both).
- Naming-convention linters unverified (Claude); rustc case lints and Biome `useNamingConvention` would give the `naming` axis an enforceable entry.
- Chow 1970 and the CACM "Lessons" paper read through abstracts only (Claude).
- No peer-reviewed comparison of composite, per-path, and primary-plus-secondary policies; Claude proposes an ablation on berd under each policy, which Tricorder can now run cheaply (both).
- Two Perplexity artifacts, its platform lens and detection rubric, were never delivered (bead 8t5.10). Claude's platform lens and rubric now fill that hole for the purpose of comparison.

## Changes this synthesis triggers

Filed as beads under epic tricorder-8t5 so each is a reviewable PR rather than drift:

1. **Lens edits from the comparison.** Extend the global ignore list per Linguist's vendored and documentation lists; drop the workflows signal from the platform lens; add the Tauri isolation, scopes, and lifecycle pages, the std-dev-guide safety policy with `undocumented_unsafe_blocks` as a partial gate on `unsafe-discipline`, Apple notarization, Authenticode, WCAG2ICT, and TypeScript `strict` to the desktop lens; add Docker, hadolint, Kubernetes configuration, the four golden signals, and OpenAPI to the platform lens with the container, manifest, and observability axes; report matched counter-signals in `discover` output; note in `enforceable_by` whether a gate blocks.
2. **Decision: core category set.** Add `question` and `naming`, consider `process`; one version bump across all lenses and the explorer radar.
3. **Decision: security and agent-engineering as overlays** rather than top-level archetypes.
4. **Secondary-lens rule.** Restrict the secondary Phase 4 section to evidence-backed observations and adopt the 15 percent path-coverage bar.
5. **Policy ablation on berd.** Run Phases 1 through 4 under composite, per-path, and primary-plus-secondary and compare smoke-check hits and `other` share, since the cache is warm and the run is cheap.

The two passes agreed on every structural decision the shipped implementation made: lenses as data, Linguist-shaped detection with a global ignore list, sub-profiles under product-engineering, a neutral category core, abstention rather than guessing, checks before spend, and smoke checks after. Where they differed, the independent pass mostly added precision: better citations for the same conclusions, one sharper rule for secondary lenses, and a formal name for the abstention policy. Nothing in the second pass contradicts the validated desktop lens; several things make it more defensible.
