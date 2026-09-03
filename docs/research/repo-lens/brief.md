# Research brief: repository composition detection and per-archetype review rubrics

Topic slug: `repo-lens`
Date opened: 2026-09-02
Motivating documents: [SKILL.md § Known limitations](../../../SKILL.md), [DESIGN.md § Discipline lenses](../../../DESIGN.md), `tricorder-synthesize.py` (legacy prompts), `tricorder/commands/discover.py` (archetype detection), `tricorder/commands/interpret.py` (lens definitions)
Test repository: `block/berd` (159 merged PRs, 2026-08-12 to 2026-09-02, harvested 2026-09-02)

## Why this research exists

Tricorder reads a team's merged pull-request history and produces four things: per-PR review patterns, reviewer focus fingerprints, author growth profiles, and a team-level gap analysis. Every one of those outputs is interpreted through a **lens**: a bundle of domain standards, interpretation axes, and pattern categories.

Today only one lens is grounded in evidence. The legacy synthesis prompts hardwire an analytics-engineering lens (dbt, SQLFluff, Kimball, dbt-project-evaluator) into all four phases, the pattern category enum, the file classifier, and the report footer. The v2 code has five named lenses, but four of them are short, uncited paragraphs written from memory, and the archetype detector is a hand-written list of file globs with guessed weights.

When the lens is wrong, the output is not merely vague. It is confidently wrong. Run against `block/berd`, a Tauri desktop app written in TypeScript and Rust, the Phase 4 gap analysis reported missing "grain declarations on fact models" and absent SQLFluff gates. Those are artifacts of the prompt, not observations about the team. Because Tricorder's value is that its findings are specific and actionable, off-domain findings are worse than no findings: they cost credibility and they cost money to generate.

The design decision in DESIGN.md is explicit: Tricorder detects the lens rather than asking the user to configure it, because "auto-detecting the likely lens from the repository fingerprint removes a configuration step that most users would get wrong". That places the whole burden on two things getting it right: **composition detection** and **rubric selection**. This brief asks what the accepted, citable practice is for both.

## Research questions

Each question names the code or document it traces to. Answer only these; do not run open-ended scans.

### Q1. Repository composition detection

Traces to: `discover.py` `ARCHETYPE_SIGNALS`, `EXT_LANGUAGE`, `KEY_FILES`; legacy `tag_file()`.

What are the accepted methods and reference implementations for determining what a repository *is* from its contents alone, with no execution and no API key? Specifically:

- Language and framework fingerprinting: what do GitHub Linguist, and comparable tools, actually use (extension maps, filename maps, heuristics, vendored-path exclusion, generated-file exclusion), and what is published as primary documentation for them?
- Manifest and build-file inventories: which manifest files are authoritative indicators of ecosystem (for example `Cargo.toml`, `package.json` with workspaces, `pnpm-workspace.yaml`, `tauri.conf.json`, `go.mod`, `pyproject.toml`), and which are weak or misleading?
- Monorepo and polyglot handling: how do established tools partition a repository with multiple ecosystems, and how do they decide whether it is one project with layers or several projects?
- Which files should be **excluded** from archetype inference because they now appear in repositories of every type? AI-assistant configuration is the pressing case: `CLAUDE.md`, `AGENTS.md`, `.agents/`, `.cursor/`, and similar now sit in ordinary product repositories and must not by themselves pull a repository toward an "agent engineering" lens.

### Q2. Archetype taxonomy

Traces to: `interpret.py` `VALID_LENSES`; DESIGN.md lens table.

Tricorder currently partitions repositories into five archetypes: `analytics-engineering`, `product-engineering`, `platform-engineering`, `security`, `agent-engineering`. Is this a defensible partition, and is it complete enough for the lens to be *specific*?

- What archetype taxonomies exist in published practice (software catalogs such as Backstage's component types, OpenSSF or SLSA project classifications, academic repository-mining classifications, package-registry categories)?
- Is "product-engineering" too broad to produce specific findings? A desktop application, a mobile app, a backend HTTP service, an SDK, and a CLI have different review concerns. Should the taxonomy have sub-profiles, and if so what is the accepted split?
- Where does `block/berd` land? It is a desktop application with a Rust core and a React/TypeScript UI, plus a companion CLI. State which archetype or sub-profile applies and why.

### Q3. Review standards per archetype, with primary sources

Traces to: `interpret.py` `LENS_CONTEXT` (the "Authoritative standards" and "Key interpretation axes" blocks); legacy `SYSTEM_P1` through `SYSTEM_P4`.

For each archetype that matters here, what are the **primary** sources a reviewer in that domain would recognize as authoritative, and what review dimensions do they define? A primary source is an official specification, an official style or API guideline, a standards-body publication, a peer-reviewed paper, or the maintained documentation of the tool the repository actually uses. Blog posts and vendor marketing are secondary and should be marked as such.

The archetype for `block/berd` must be covered in full. At minimum it needs:

- TypeScript and React front-end review standards, and the rule catalog of the linter the repository uses (Biome, per `biome.json`).
- Rust review standards: the Rust API Guidelines, the Clippy lint catalog, guidance on `unsafe`, dependency and license auditing.
- Tauri-specific concerns: the IPC boundary between the Rust core and the web view, the capabilities and permissions model, content security policy, updater and code-signing practice.
- Desktop-application concerns that a service-oriented lens would miss: cross-platform build and packaging (the repository carries Swift, Objective-C, PowerShell, and a `distro/` directory), release and update channels, telemetry and privacy (the repository has `TELEMETRY.md`), accessibility.
- End-to-end testing practice for the framework the repository uses (Playwright, per `playwright.config.ts`).

At least one **other** archetype must also be covered to the same depth, so that the lens format is proven on two domains rather than fitted to one. Prefer `platform-engineering` or a backend-service profile.

### Q4. Deterministic versus judgment: the maturity ladder

Traces to: legacy prompts' maturity levels `judgment | guidance | convention | rule | deterministic`; Phase 4 `institutionalization_candidates`.

Tricorder's most useful output is the list of review patterns that are ready to move up the ladder from human judgment toward automated enforcement. That requires knowing, per review dimension, what tooling can enforce it.

- For each axis in the `block/berd` lens, which dimensions are enforceable by tools already present in the repository (Biome, Clippy and rustfmt, cargo-audit or cargo-deny, Playwright, lefthook hooks, GitHub Actions) and which can only be human judgment?
- What is the accepted vocabulary for this ladder? Tricorder's five levels are home-grown. Is there published practice (for example in Google's engineering practices, in "shift-left" literature, in maturity models such as DORA or CMMI) that maps onto it or that Tricorder should adopt instead?

### Q5. Pattern category taxonomy for review comments

Traces to: `SYSTEM_P1` `category` enum (`grain | naming | testing | documentation | style | performance | modeling | schema | business-logic | incremental | exposure-contract | source-freshness | macro-complexity | test-pyramid | other`).

The Phase 1 category enum is dbt-specific. Twelve of its fifteen values are meaningless for `block/berd`, so most extracted patterns collapse into `other` and the downstream fingerprints lose resolution.

- What published taxonomies classify code-review comments? Candidates include the modern-code-review literature (Bacchelli and Bird 2013; Sadowski et al. 2018 on code review at Google; Mäntylä and Lassenius on defect types found in review; Beller et al. on review-finding categories) and practitioner conventions such as Conventional Comments.
- Should Tricorder use one domain-neutral taxonomy with per-lens extensions, or a fully per-lens enum? State a recommendation and the evidence for it.

### Q6. Confidence, mixed repositories, and abstention

Traces to: `discover.py` scoring (sum of matched weights, highest wins); DESIGN.md "Why lens detection, not user configuration?"

The failure mode this research exists to prevent is confident misclassification.

- What thresholds or margins do established classifiers use before committing to a label, and how do they express "unknown" or "mixed"?
- When a repository is genuinely multi-archetype, is the accepted approach a composite lens, a per-path lens (Rust files under one rubric, TypeScript files under another), or primary-plus-secondary? What does the evidence say about which produces more accurate downstream judgments?
- What should Tricorder verify *after* selecting a lens, so a wrong choice is caught before money is spent on synthesis? Examples: the lens's expected languages against the observed language bytes; the lens's file tags against the paths reviewers actually comment on.

### Q7. Validation on the test case

Traces to: DESIGN.md's promotion rule (a lens moves from `Experimental` to `Validated` after a successful production-repo evaluation).

Using the `block/berd` fingerprint supplied in the handoff prompt, show that the proposed detection rubric selects the intended lens, that the current Tricorder detector would or would not have selected it, and that every axis in the proposed lens is one a Berd reviewer could plausibly comment on. Name the specific evidence, such as the comment-path histogram, that supports each claim.

## Non-goals

- Do not redesign Tricorder's four-phase pipeline or its artifact contract. The lens is a plug-in to the existing phases.
- Do not evaluate LLM providers or models.
- Do not review `block/berd`'s code quality. The repository is the test fixture, not the subject.
- Do not propose a lens for every conceivable archetype. Two fully specified lenses plus a detection rubric that can be extended is the deliverable.

## Deliverables

Defined in full in [handoff-prompt.md](handoff-prompt.md). In short: a narrative findings document following [findings/TEMPLATE.md](findings/TEMPLATE.md) with primary-source citations, plus machine-readable lens files in the YAML schema the handoff prompt specifies, one per archetype, each validated against `block/berd`.
