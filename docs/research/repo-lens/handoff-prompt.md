# Handoff prompt: repository lenses for Tricorder

Copy everything below the line into Perplexity (or any other research tool or person). It is self-contained: no repository access is needed. The findings come back as one Markdown document plus YAML lens files, in the formats specified in Part 4.

---

## Your task

You are producing a research report and two machine-readable rubric files for a tool called **Tricorder**. Tricorder mines a GitHub repository's merged pull-request history and extracts what the team's code reviewers consistently catch, what they miss, and which review habits are ready to become automated checks. It does this by sending review comments to an LLM together with a **lens**: a bundle of domain standards, interpretation axes, and pattern categories for the kind of repository being analysed.

Tricorder currently has one well-grounded lens, for dbt/SQL analytics repositories. When it is pointed at any other kind of repository it still applies that lens, and the results are confidently wrong: for a desktop application written in TypeScript and Rust it reported missing "grain declarations on fact models" and absent SQLFluff gates. Those findings are artifacts of the prompt, not observations about the team.

Your job is to establish, from **primary sources**, how Tricorder should (a) inspect a repository and determine its composition, (b) choose the right rubric for it, and (c) what that rubric must contain so the findings are on-domain and specific. The test case is the public repository **`block/berd`**, whose fingerprint is given in Part 3. Your lens for its archetype must be validated against that fingerprint.

Accuracy matters more than breadth. A wrong lens produces plausible-sounding, wrong findings that cost the user money and credibility. Where the evidence is thin, say so rather than fill the gap.

## Part 1: What Tricorder does with a lens (the contract you are filling)

Tricorder runs four LLM phases, then an interpretation step. The lens supplies context to each.

| Phase | Input | Output | What the lens contributes |
|-------|-------|--------|---------------------------|
| 1. Per-PR extraction | One PR: description, review bodies, inline comments with file paths | Patterns, each with a `category`, a `maturity` level, an optional `standard_citation`, and quoted comment evidence | The category enum, the file-path tags, the list of citable standards |
| 2. Reviewer fingerprint | All patterns for one reviewer | Primary focus areas, apparent blind spots, review style, signal quality | Which focus areas are meaningful in this domain, which standards to cite |
| 3. Author growth profile | All patterns for one author, chronological | Strengths, growth areas with persistence, trajectory, support recommendation | Which standards to cite, what "support" looks like in this domain |
| 4. Team gap analysis | Everything | Team strengths, gaps typed as `coverage_gap`, `knowledge_gap`, or `blind_spot`, institutionalization candidates | The list of named best practices whose *absence* from the review record is itself a finding. This is where an off-domain lens does the most damage |
| Interpret | Phase outputs plus the lens | Standard mappings, domain blind spots, quick wins, lens summary | The full lens: authorities, axes, and framing |

Two vocabularies are fixed and your lens must use them:

- **Maturity ladder** for a review pattern: `judgment` (a reviewer noticed it once), `guidance` (written down somewhere), `convention` (the team consistently does it), `rule` (a documented requirement), `deterministic` (a tool enforces it in CI or a hook). Tricorder's most valuable output is the set of patterns ready to move up this ladder.
- **Gap taxonomy**: `coverage_gap` (nobody reviews for this), `knowledge_gap` (reviewers raise it but shallowly or inconsistently), `blind_spot` (a named best practice never appears in any review).

The current lens definitions are prose paragraphs. Here is the existing dbt lens, verbatim, so you can see the level of specificity the one working lens has. Your lenses must be at least this specific, and every authority must carry a URL.

```
Lens: analytics-engineering
Domain: dbt, SQL, data modeling, analytics pipelines (BigQuery / Snowflake / Redshift)

Authoritative standards for this lens:
- dbt Labs style guide — https://docs.getdbt.com/best-practices/how-we-style/0-how-we-style-our-dbt-projects
- dbt-project-evaluator check catalog — https://github.com/dbt-labs/dbt-project-evaluator
- SQLFluff rule catalog — https://docs.sqlfluff.com/en/stable/rules.html
- Kimball dimensional modeling techniques — https://www.kimballgroup.com/...
- dbt Labs best practices: testing — https://docs.getdbt.com/best-practices/writing-custom-generic-tests

Key interpretation axes for analytics engineering:
- Grain clarity: is the grain of each model explicitly declared or inferable?
- Test coverage: are uniqueness, not-null, and FK tests present on key columns?
- Naming conventions: staging/int/mart prefixes, snake_case, no reserved words
- Source freshness: are freshness thresholds configured?
- Incremental model safety: is_incremental() blocks, full-refresh safety
- Exposure contracts: are final mart models exposed and contracted?
- Documentation: model + column descriptions in schema.yml
- Macro complexity: are macros testable and documented?
- CI gate coverage: what is enforced by SQLFluff / dbt-project-evaluator vs. left to judgment?
```

The Phase 1 category enum today is: `grain | naming | testing | documentation | style | performance | modeling | schema | business-logic | incremental | exposure-contract | source-freshness | macro-complexity | test-pyramid | other`. Twelve of these are meaningless outside dbt.

Tricorder's current archetype detector is a hand-written list of file globs with guessed weights, summed per archetype, highest score wins, no threshold and no "unknown". The five archetypes are `analytics-engineering`, `product-engineering`, `platform-engineering`, `security`, `agent-engineering`. Note one trap in the current signals: `CLAUDE.md` scores 6 and any `**/agents/**` directory scores 5 toward `agent-engineering`. Those files now appear in ordinary repositories of every kind, including the test case.

## Part 2: Research questions

Answer these seven questions in order. Each names what it is for. Do not add questions.

**Q1. Composition detection.** What are the accepted methods and reference implementations for determining what a repository is from its contents alone, with no execution? Cover: language and framework fingerprinting as implemented by GitHub Linguist and comparable tools (extension maps, filename maps, heuristics, vendored and generated-file exclusion); which manifest and build files are authoritative ecosystem indicators and which are weak; how established tools partition monorepos and polyglot repositories; and which files must be **excluded** from archetype inference because they now appear everywhere, with AI-assistant configuration (`CLAUDE.md`, `AGENTS.md`, `.agents/`, `.cursor/`) as the pressing case.

**Q2. Archetype taxonomy.** Is Tricorder's five-way partition defensible and specific enough? Survey published taxonomies (software-catalog component types such as Backstage's, OpenSSF and SLSA classifications, repository-mining classifications, registry categories). Is `product-engineering` too broad, given that a desktop app, a mobile app, a backend service, an SDK, and a CLI have different review concerns? If sub-profiles are warranted, what is the accepted split? State where `block/berd` lands and why.

**Q3. Review standards per archetype, with primary sources.** For the `block/berd` archetype in full, and for at least one other archetype to the same depth (prefer platform-engineering or a backend-service profile): what are the primary sources a domain reviewer would recognize as authoritative, and what review dimensions do they define? For Berd this must include TypeScript and React review standards and the Biome rule catalog; Rust review standards (Rust API Guidelines, the Clippy lint catalog, guidance on `unsafe`, dependency and license auditing); Tauri-specific concerns (the IPC boundary, capabilities and permissions, CSP, updater and code signing); desktop-application concerns a service lens would miss (cross-platform packaging, release channels, telemetry and privacy, accessibility); and Playwright end-to-end testing practice.

**Q4. Deterministic versus judgment.** For each axis in the Berd lens, which dimensions are enforceable by tooling already in the repository (Biome, Clippy and rustfmt, cargo-audit or cargo-deny, Playwright, lefthook, GitHub Actions) and which are human judgment only? Is there published practice that maps onto Tricorder's five-level maturity ladder, or that it should adopt instead?

**Q5. Pattern category taxonomy.** What published taxonomies classify code-review comments? Consider the modern-code-review literature (Bacchelli and Bird 2013; Sadowski et al. 2018; Mäntylä and Lassenius; Beller et al.) and practitioner conventions such as Conventional Comments. Recommend, with evidence, whether Tricorder should use one domain-neutral taxonomy with per-lens extensions or a fully per-lens enum.

**Q6. Confidence, mixed repositories, abstention.** What thresholds or margins do established classifiers use before committing to a label, and how do they express "unknown" or "mixed"? For a genuinely multi-archetype repository, is the accepted approach a composite lens, a per-path lens, or primary-plus-secondary? What should Tricorder verify after selecting a lens so a wrong choice is caught before synthesis is paid for? Examples: expected languages against observed language bytes; lens file tags against the paths reviewers actually comment on.

**Q7. Validation on the test case.** Using the fingerprint in Part 3, show that your detection rubric selects the intended lens for `block/berd`, state whether Tricorder's current detector would have, and show that every axis in your Berd lens is one a Berd reviewer could plausibly comment on. Cite the specific fingerprint evidence for each claim.

### Source rules

- **Primary** means: an official specification; an official style, API, or security guideline from the language or framework maintainers; a standards-body publication; a peer-reviewed paper; or the maintained documentation of a tool the repository actually uses. Mark anything else as **secondary** and use it only when no primary source covers the point.
- Every citation carries: title, publisher or authors, URL, the date you retrieved it, and the specific claim it supports. A URL alone is not a citation.
- Do not cite the dbt lens's sources for any non-dbt archetype. If you are tempted to, that is the failure mode this research exists to remove.
- If a question has no good primary source, say `none found` and explain what you looked for. Do not pad.

## Part 3: The test case, `block/berd`

Public repository. GitHub description: "a desktop app for getting work done with any model". Primary language per GitHub: TypeScript. Default branch: `main`. All figures below were collected on 2026-09-02.

**Language bytes (GitHub languages API):**

| Language | Bytes |
|----------|-------|
| TypeScript | 15,308,659 |
| Rust | 3,781,965 |
| JavaScript | 313,787 |
| PowerShell | 205,723 |
| Shell | 173,036 |
| CSS | 88,839 |
| Objective-C | 76,479 |
| Just | 32,197 |
| Swift | 28,306 |
| HTML | 23,999 |
| Python | 14,831 |
| C | 3,434 |
| Dockerfile | 2,561 |
| HCL | 60 |

**Top-level entries of the default branch:**

```
.agents/  .github/  AGENTS.md  CHANGELOG.md  CLAUDE.md  CODEOWNERS  CODE_OF_CONDUCT.md
CONTRIBUTING.md  DESIGN.md  GOVERNANCE.md  LAWS/  LICENSE  PRODUCT.md  README.md
SECURITY.md  TELEMETRY.md  acp-tools.lock.json  app-icon.png  bb-cli/  bin/  biome.json
crates/  distro/  docker/  docs/  doctor.config.ts  goose-backend.lock.json  index.html
justfile  lefthook.yml  node-runtime.lock.json  package.json  playwright.config.ts
playwright.table-overflow.config.ts  pnpm-lock.yaml  pnpm-workspace.yaml
postcss.config.js  public/  src/  src-tauri/
```

(The listing was truncated by the API after `public/`; `src/` and `src-tauri/` are confirmed from review-comment paths below.)

**Merged PRs harvested:** 159, merged between 2026-08-12 and 2026-09-02, 18 distinct contributors.

**Inline review comments:** 471 total. By file extension of the commented path:

| Extension | Comments |
|-----------|----------|
| .rs | 170 |
| .tsx | 131 |
| .ts | 131 |
| .sh | 12 |
| .swift | 7 |
| .json | 4 |
| .m | 4 |
| .md | 4 |
| .mjs | 4 |
| .yml | 2 |
| .css | 1 |
| .toml | 1 |

By top-level directory of the commented path:

| Directory | Comments |
|-----------|----------|
| src/ | 267 |
| src-tauri/ | 168 |
| bb-cli/ | 26 |
| LAWS/ | 4 |
| scripts/ | 4 |
| .github/ | 2 |

**PR template** (`.github/PULL_REQUEST_TEMPLATE.md`) has three sections: Summary, Related issue, Testing. The Testing section asks for before/after screenshots or a recording for UI changes. The template states that outside PRs are closed automatically.

**No** `dbt_project.yml`, **no** `.sqlfluff`, **no** SQL files were detected.

**What the current Tricorder detector would see:** `package.json` (+5 product-engineering), `CLAUDE.md` (+6 agent-engineering), `.agents/` (+5 agent-engineering via `**/agents/**`), `SECURITY.md` (+8 security), `Dockerfile` under `docker/` (+5 platform-engineering), `.github/workflows/*.yml` (+2 platform-engineering). Work out which archetype wins and whether that is right. This is part of Q7.

**Known symptom to design against:** with the dbt lens, Phase 4 on this repository produced gaps citing the dbt style guide, SQLFluff, and Kimball. None of those can be relevant here. A validated lens for Berd must make that output impossible.

## Part 4: Required output format

Produce **two artifacts**. Both are required.

### Artifact A: findings document (Markdown)

One Markdown file. Seven sections, `## Q1` through `## Q7`, in order, matching the questions in Part 2. Each section contains:

1. A table with exactly these columns:

   `Entry | What it is | Tricorder concept overlap | Verdict`

   - **Entry**: the source, tool, taxonomy, or practice found.
   - **What it is**: one or two sentences.
   - **Tricorder concept overlap**: which part of Part 1 it touches (detection signals, category enum, maturity ladder, gap taxonomy, an axis, a phase prompt).
   - **Verdict**: exactly one of `adopt/reference`, `differentiate`, `ignore`. No other labels. No rationale in this cell.

2. A `**Notes**` block below the table with the rationale for each verdict, the direct answer to the question, and the full citations (title, publisher or authors, URL, retrieval date, claim supported).

3. If nothing was found, a single table row whose Entry is `none found`, with the reason in Notes. Never an empty table.

End with a `## Open gaps` section: what you could not answer from primary sources, and what evidence would settle it.

### Artifact B: lens files (YAML)

At least **two** YAML files, one per archetype: the archetype you assign to `block/berd`, and one other archetype covered to the same depth. Plus one shared `detection-rubric.yaml` if your detection rules are not fully expressible inside the lens files.

Every field below is required unless marked optional. The schema is the ingestion contract; do not rename or omit keys. Tricorder will load these with PyYAML and use them to replace its hand-written prose lenses, its file classifier, its category enum, and its archetype signals.

```yaml
lens:
  name: product-engineering-desktop        # kebab-case, unique. May be a sub-profile of an existing archetype.
  version: 1
  status: experimental                     # experimental | validated. Leave as experimental; Tricorder promotes it.
  extends: product-engineering             # optional. Parent archetype from the five, if this is a sub-profile.
  domain: >-
    One paragraph. What kind of repository this lens is for, in terms a reviewer would recognize.

  detection:
    # Positive evidence. Tricorder sums matched weights. Use globs relative to repo root.
    signals:
      - pattern: "src-tauri/tauri.conf.json"
        weight: 10
        rationale: "Tauri desktop shell; near-definitive."
        source: "URL of the primary doc that says this file is required by the framework"
    # Evidence against this lens. Negative weights.
    counter_signals:
      - pattern: "dbt_project.yml"
        weight: -10
        rationale: "..."
    # Files that must not influence ANY lens selection. Applies globally.
    ignore_for_detection:
      - "CLAUDE.md"
      - "AGENTS.md"
      - ".agents/**"
    min_score: 10                          # below this, the lens must not be auto-selected
    min_margin: 5                          # required lead over the runner-up; otherwise report "mixed"
    composition_check:                     # post-selection sanity check against language bytes
      languages_expected: [TypeScript, Rust]
      languages_unexpected: [SQL]          # presence above 5% of bytes should flag the selection
    review_path_check:                     # post-selection check against where reviewers actually comment
      min_share_of_comments_on_tagged_paths: 0.7

  # Replaces Tricorder's file classifier. First match wins. The tag is shown to the LLM next to each inline comment.
  file_tags:
    - glob: "src-tauri/**/*.rs"
      tag: "desktop-core-rust"
    - glob: "src/**/*.tsx"
      tag: "ui-react"
    - glob: "**/*.test.ts"
      tag: "test"

  # Replaces the Phase 1 category enum. Include a small domain-neutral core plus domain-specific entries.
  # Every category needs a real example comment a reviewer in this domain would write.
  categories:
    - id: ipc-boundary
      description: "Data crossing the Rust/webview boundary: serialization, validation, capability scoping."
      example_comment: "This command takes an arbitrary path from the frontend; scope it to the workspace dir."
      axes: [ipc-boundary]

  # Primary sources. Each must be citable in a finding.
  authorities:
    - id: rust-api-guidelines
      name: "Rust API Guidelines"
      publisher: "Rust project"
      url: "https://rust-lang.github.io/api-guidelines/"
      kind: primary                        # primary | secondary
      retrieved: 2026-09-02
      covers: [ipc-boundary, error-handling]   # category ids

  # Interpretation axes. These become the lens's "Key interpretation axes" and drive Phase 4 blind-spot detection.
  axes:
    - id: ipc-boundary
      question: "Are Tauri commands scoped, validated, and covered by the capabilities manifest?"
      categories: [ipc-boundary]
      authorities: [tauri-security-docs]
      enforceable_by:                      # empty list means judgment only
        - tool: "tauri capabilities manifest"
          config: "src-tauri/capabilities/*.json"
          coverage: partial                # full | partial
      max_maturity: rule                   # ceiling on the maturity ladder given available tooling
      phase4_absence_is_finding: true      # if no review ever touches this axis, report it as a blind_spot

  # Tools that make a dimension deterministic when present. Tricorder will check for the config file.
  tooling_gates:
    - tool: biome
      config_file: "biome.json"
      enforces: [style, import-order]      # category ids
      source: "URL of the rule catalog"

  # Text appended to each phase's system prompt. Keep each under 200 words. Must not mention any other domain.
  prompt_context:
    phase1_pr_extraction: |
      ...
    phase2_reviewer_fingerprint: |
      ...
    phase3_author_growth: |
      ...
    phase4_team_gaps: |
      ...
    interpret: |
      ...

  # Negative guidance. Phrases or authorities the LLM must never produce under this lens.
  must_not:
    - "Cite dbt, SQLFluff, Kimball, or dbt-project-evaluator."
    - "Report gaps about grain, fact models, or source freshness."

  validation:
    test_repo: "block/berd"
    expected_selection: true               # should this lens win for the test repo?
    expected_score_min: 25
    expected_runner_up: "agent-engineering"
    evidence:                              # fingerprint facts from Part 3 that justify each axis
      - axis: ipc-boundary
        evidence: "168 of 471 inline comments are under src-tauri/; 170 are on .rs files."
    smoke_checks:                          # strings that must NOT appear in any output under this lens
      - "grain"
      - "fact model"
      - "dbt"
```

Rules for Artifact B:

- Every `authorities[].url` must also appear as a citation in Artifact A.
- Every axis must reference at least one authority and at least one category.
- Every category must have a plausible `example_comment`; for the Berd lens, prefer paraphrases of the kind of comment the histogram in Part 3 suggests reviewers actually write.
- The Berd lens's `validation.evidence` must reference the Part 3 fingerprint explicitly.
- If you recommend a domain-neutral category core in Q5, put it in both lens files identically and mark those entries with `core: true`.
- Do not fill fields you cannot support. An honest `enforceable_by: []` is better than a guessed tool.

## Part 5: What success looks like

A Tricorder maintainer should be able to drop your YAML files into the tool, run detection on `block/berd`, get the lens you intended with a clear margin, run the four phases, and see gap findings that a Berd reviewer would nod at: IPC scoping, `unsafe` justification, capability manifests, React state and effect hygiene, Playwright coverage of UI changes, packaging and updater safety. Not one finding should mention a data warehouse.

If any part of that chain cannot be supported by primary sources, say which part and why in `## Open gaps`.
