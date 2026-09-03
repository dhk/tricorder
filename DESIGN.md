# tricorder — Design Document

> *"A room full of data people and you named it tricorder instead of data. Yes, on purpose."*

**Version:** 2.0  
**Status:** v2 architecture implemented; design document (some future sections remain proposals)

**Repo:** [dhk/tricorder](https://github.com/dhk/tricorder)

**Current shipped interface:** v2 command set in [tricorder/cli.py](tricorder/cli.py),
with v1 names retained as legacy compatibility dispatch. Operational details live in
[HOWTO.md](HOWTO.md); privacy details live in [docs/PRIVACY.md](docs/PRIVACY.md).

---

## Thesis

Software repositories contain two kinds of content. The first is code — what teams build, version, and deploy. The second is everything else: the comments on pull requests, the review threads, the back-and-forth before a merge. This content is rich with information about how a team thinks, what it values, where it struggles, and what it has learned.

Almost none of it gets used.

Code review comments are the most honest knowledge base most teams produce. They are more current than wikis, less curated than runbooks, and more candid than retrospectives. The problem is that they exist only in threads — visible one at a time, searchable only if you know what you're looking for, and effectively lost when a reviewer leaves the team.

Tricorder reads that record and extracts the signal.

The broader thesis: non-code repository content — reviews, comments, discussions — is training material. Not just for human processes (conventions, checklists, CI gates), but for AI tools that assist the work. A team's review history contains the implicit standards that govern their codebase. Making those standards explicit is the first step toward encoding them anywhere useful.

---

## What tricorder is

Tricorder is a repository learning system.

It reads evidence already present in a repository — code, git history, and review discussions — and progressively extracts organizational knowledge: what the team has learned, what it consistently misses, and where that knowledge can create the most leverage.

The core insight:

> Every recurring review comment is evidence that the organization is paying the same cost repeatedly.

Tricorder discovers those costs, identifies patterns, and recommends ways to move learning upstream — so the same problems occur less frequently over time.

---

## What it is not

**Not a code review tool.** Tricorder reads historical review data. It does not participate in live review, suggest inline comments, or generate feedback on individual PRs.

**Not a metrics dashboard.** Tricorder does not count PRs, measure review cycle time, or report on merge frequency. It answers: what is the team actually learning from code review?

**Not a performance review tool.** Author growth profiles describe patterns in the review feedback an author receives. This is material for a growth conversation, not an HR system.

**Not a GitHub Analytics competitor.** GitHub's analytics answer questions about activity. Tricorder answers questions about knowledge: what does the team understand, and what does it consistently miss?

---

## Trust model

Tricorder earns access incrementally.

Every increase in access must unlock a visibly better class of insight. Users encounter something interesting before being asked to invest more. The interaction model is a ratchet: trust increases, signal increases, artifacts accumulate, and the next action is always obvious.

```
Level 0   Local filesystem     →  Repository Profile
Level 1   Local git history    →  Evolution Timeline
Level 2   GitHub read access   →  Review Patterns
Level 3   LLM API              →  Organizational Learnings
Level 4   LLM API + lens       →  Interpretation
Level 5   LLM API              →  Improvement Plan
```

At every level, tricorder states clearly what access it used, what it did not access, what it found, and what the next step is.

### Access contract

| Level | Command | Data sources | Network | Credentials | Writes | Failure behavior |
|---|---|---|---|---|---|---|
| 0 | `discover` | Local repository files only | No | None | `.tricorder/repository-profile.yml`, `.tricorder/repository-fingerprint.json` | If repository path is unreadable/writable output location fails, exit with actionable filesystem error and no partial trust escalation |
| 1 | `discover --history` | Local git history only | No | None | `.tricorder/contributors.json`, `.tricorder/hotspots.json`, `.tricorder/repository-timeline.json` | If git history is unavailable, exit with actionable git error and suggest running from a git repository |
| 2 | `analyze` | GitHub PR/review metadata + local repo context files | Yes (GitHub API) | `GITHUB_TOKEN` | `.tricorder/review-observations.json`, `.tricorder/review-patterns.json`, `.tricorder/expertise-map.json` | If token/missing scopes/API errors occur, exit with actionable auth/API error; do not proceed to LLM levels |
| 3 | `learn` | Level 2 artifacts | Yes (LLM API) | Provider API key (`ANTHROPIC_API_KEY` or `GEMINI_API_KEY`) | `.tricorder/learnings.json`, `.tricorder/standards-candidates.json`, markdown report | If LLM auth/quota/request errors occur, stop at last completed step; preserve completed artifacts for resume |
| 4 | `interpret` | Level 3 artifacts + selected lens | Yes (LLM API) | Provider API key | `.tricorder/interpretations.json` | If lens is unsupported or LLM call fails, return actionable error and keep prior artifacts unchanged |
| 5 | `improve` | All prior artifacts | Yes (LLM API) | Provider API key | `.tricorder/improvement-plan.md`, `.tricorder/roadmap.json` | If required upstream artifacts are missing, fail fast with missing-prerequisite error and suggested command sequence |

This table is the authoritative trust boundary for v2 cutover implementation.

---

## Architecture

**Six levels. One artifact chain. One explorer.**

```
discover  →  discover --history  →  analyze  →  learn  →  interpret  →  improve
    ↓               ↓                  ↓           ↓           ↓            ↓
.tricorder/     .tricorder/        .tricorder/  .tricorder/  .tricorder/  .tricorder/
profile.yml   contributors.json   patterns.json learnings.json interpretations.json roadmap.json
```

### Level 0 — `tricorder discover`

**Access:** Local filesystem only. No network. No credentials.

Reads the repository to understand what it is. Detects repository archetype (analytics-engineering, product-engineering, platform-engineering, security), technology fingerprint, tooling gaps, and contributor count. Proposes the most likely discipline lens based on detected evidence. No API calls.

**Artifacts written:**
```
.tricorder/
├── repository-profile.yml
└── repository-fingerprint.json
```

### Level 1 — `tricorder discover --history`

**Access:** Local git history only. No network.

Reads how the repository evolved. Contributor patterns, ownership signals, churn analysis, hotspot map, evolution timeline.

**Artifacts written:**
```
.tricorder/
├── contributors.json
├── hotspots.json
└── repository-timeline.json
```

### Level 2 — `tricorder analyze`

**Access:** GitHub REST API — read only. Pull requests, review comments, commit metadata. No repository contents fetched.

Pulls merged PRs from GitHub. For each PR: metadata, description, formal review threads, and inline diff comments. Writes structured JSON to the artifact store.

The cache is append-only and incremental — re-running only fetches PRs newer than the last harvest. Bot PRs (Dependabot etc.) are filtered before writing.

Five signals are computed and stored with each PR:
- **Description quality score** (high / medium / low)
- **Review iteration count** — CHANGES_REQUESTED states before approval
- **Has-reply flag** — inline comments that received a reply
- **File type tags** — comments tagged by file touched
- **Author tenure** — days of cache history for this author

Analyze also captures repo context: `dbt_project.yml`, `.sqlfluff` (rules already enforced in CI), and the PR template. Learn uses this context to avoid recommending things already enforced as CI gates.

**Artifacts written:**
```
.tricorder/
├── review-observations.json
├── review-patterns.json
└── expertise-map.json
```

### Level 3 — `tricorder learn`

**Access:** LLM API. Reads from Level 2 artifacts.

Runs four LLM calls:

1. **Per-PR pattern extraction** — one call per PR. Returns structured JSON: patterns identified, evidence quotes, author signals, reviewer signals. PRs with no review activity are skipped.

2. **Reviewer fingerprints** — one call per reviewer. Returns: primary focus areas with frequency and standard citations, apparent blind spots with basis, review style, signal quality.

3. **Author growth profiles** — one call per author. Returns: strengths, growth areas with persistence assessment, support recommendations, trajectory (improving / stable / regressing / insufficient-data).

4. **Team gap analysis** — one aggregate call. Returns: team strengths, gaps classified by type (coverage / knowledge / blind spot), institutionalization candidates with maturity path targets, review culture observation.

Intermediate results are cached after each call. A failed run can resume from the last completed phase.

**Artifacts written:**
```
.tricorder/
├── learnings.json
└── standards-candidates.json
```

Also writes a Markdown report to `--out DIR`.

### Level 4 — `tricorder interpret`

**Access:** LLM API. Reads from Level 3 artifacts. Applies the detected (or user-selected) discipline lens.

The lens provides domain-specific interpretation: which standards apply, which authorities to cite, how to read the patterns for this repository type. The `analytics-engineering` lens is currently `Experimental` with strong evidence from v1 outputs, and other lenses remain `Experimental` until validated.

**Artifacts written:**
```
.tricorder/
└── interpretations.json
```

### Level 5 — `tricorder improve`

**Access:** LLM API. Reads from all prior artifacts.

Synthesizes findings from all levels into a prioritized improvement roadmap.

**Artifacts written:**
```
.tricorder/
├── improvement-plan.md
└── roadmap.json
```

### `tricorder probe`

**Access:** GitHub REST API. No LLM spend.

Cost estimator. Pulls a sample of real PRs, assembles the exact prompts, counts tokens, and prints a cost table with extrapolations. Run before `learn` to confirm cost. Typical: ~$0.015/PR.

### `tricorder build`

**Access:** Reads from artifact store only.

Generates the static HTML explorer from the artifact store. Applies a name map if one exists at `~/.tricorder/<owner>__<repo>-name-map.json`. Writes `explorer/data.js`.

The explorer is deployed to GitHub Pages. Pushing `data.js` is the only deploy step.

### `tricorder demo`

Scripted walkthrough using pre-baked cal-itp/data-infra data and Trek aliases. No GitHub or LLM API calls.

---

## Discipline lenses

A lens provides the interpretive framework for every LLM phase (Levels 3 and 4), not only interpretation. It is data: one YAML file per lens under `tricorder/lenses/data/`, overridable per repository from `.tricorder/lenses/` and per user from `~/.tricorder/lenses/`. The schema and the research behind it live in `docs/research/repo-lens/`.

A lens file carries:

- **detection**: positive signals and counter-signals (globs with weights), a global ignore list, `min_score`, `min_margin`, and two post-selection checks (`composition_check` against language bytes, `review_path_check` against where reviewers actually comment).
- **file_tags**: first-match globs that label every inline comment for the model.
- **categories**: a ten-item domain-neutral core shared by every lens (`correctness, security, testing, documentation, style, performance, error-handling, maintainability, dependencies, other`) plus domain extensions, each with an example comment.
- **authorities**: primary sources with URLs; the only standards the model may cite.
- **axes**: the review dimensions of the domain, each with an enforceability ceiling on the maturity ladder and a flag saying whether its absence from the review record is itself a blind spot.
- **tooling_gates**: config files whose presence makes a dimension deterministic; Phase 4 reports those as institutionalized, never as gaps.
- **prompt_context** per phase, **must_not** prohibitions, and **validation** smoke checks that fail a run if off-domain terms appear in output.

Detection scores every lens from the repository's file paths after dropping the global ignore list (`CLAUDE.md`, `AGENTS.md`, `.agents/`, community-health files: they appear in repositories of every kind). The winner must clear its own `min_score`, otherwise the result is `unknown` and no lens runs; it must lead the runner-up by `min_margin`, otherwise the result is `mixed` and the runner-up's axes are offered to Phase 4 as a secondary section, reported only with evidence. Lenses are never blended. Users can override at any time with `--lens <name>`, and `--force` proceeds past a failed check.

| Lens | Domain | Status | Evidence |
|------|--------|--------|----------|
| `analytics-engineering` | dbt, SQL, warehouse modeling | experimental | cal-itp/data-infra (v1 runs; detection selects it with platform-engineering as a mixed runner-up) |
| `product-engineering` | product software, parent of the sub-profiles | experimental | fallback when no sub-profile matches |
| `product-engineering-desktop` | Tauri/Electron-class desktop apps: webview UI + native core | **validated** | block/berd, 2026-09-03: score 32, margin 28, both checks pass, Phase 1 `other` 4%, zero smoke hits, ten on-axis gaps ([record](docs/research/repo-lens/findings/perplexity-lenses/VALIDATION.md)) |
| `product-engineering-mobile` | Flutter/Dart mobile apps with Swift/Kotlin shells | experimental | Flutter-shaped fixture selects it (score 30, margin 26); block/buzz deliberately falls back to the parent (mobile scores 2) because Dart is 12% of bytes in a desktop-heavy monorepo |
| `platform-engineering` | IaC, Kubernetes, CI/CD, supply chain | experimental | none yet |
| `security` | security engineering | experimental | rarely auto-selected; use `--lens security` or `learn --focus-on security` |
| `agent-engineering` | agent systems, MCP servers, evals | experimental | none yet |

A lens moves from `experimental` to `validated` after one successful production-repository evaluation: detection selects it with margin, both checks pass, the Phase 1 `other` share stays under 15%, and the smoke checks find nothing. Backend-service, library, and CLI sub-profiles of `product-engineering` are planned (beads epic `tricorder-8t5`). A multi-archetype monorepo such as block/buzz (Flutter mobile client, Rust backend, Tauri desktop) is not served well by any single lens; the honest path is a per-path lens scoped to one component, which is future work.

The maturity ladder maps onto published practice: rustc's `allow / warn / deny / forbid` lint levels and Google's enforce-in-build versus advise-in-review split both operationalize the same idea. `warn`-level tooling sits at the `convention`/`rule` boundary; `deny` or `forbid` in CI is `deterministic`; documented but unenforced is `rule`; an unwritten team habit is `convention`; a one-off reviewer catch is `judgment`.

---

## The artifact contract

Artifacts are first-class outputs, not implementation details.

Every level writes structured artifacts that subsequent levels read. No level re-fetches data that a prior level already collected.

```
repository-profile.yml
    ↓
contributors.json + hotspots.json
    ↓
review-patterns.json + expertise-map.json
    ↓
learnings.json + standards-candidates.json
    ↓
interpretations.json
    ↓
improvement-plan.md + roadmap.json
```

Artifacts are:
- **Human-readable** — YAML, JSON, or Markdown
- **Inspectable** — if a finding looks wrong, the input that produced it is on disk
- **Reusable** — external tools, MCP servers, and AI agents can consume them without rerunning analysis

---

## Artifact storage

Default: `.tricorder/` inside the repository being analyzed, when tricorder is run from that repository.

Configurable via `~/.learn-from-work/config`. Falls back to XDG cache conventions if the current directory is not writable. The storage location is recorded in `.tricorder/config.yml` on first write.

---

## Status blocks

Every command ends with a status block:

```
Tricorder — Review Analysis

Access used
  ✓ Pull requests (read)
  ✓ Review comments (read)
  ✓ Commit metadata (read)

  No write operations performed.
  Repository contents remain local.

Completed
  ✓ Repository Profile
  ✓ Technology Fingerprint
  ✓ Contributor Patterns
  ✓ Review Patterns

Not yet unlocked
  ○ Organizational Learnings   →  tricorder learn
  ○ Interpretation             →  tricorder interpret
  ○ Improvement Planning       →  tricorder improve

Next
  tricorder learn
```

Users should never wonder: what happened, what was analyzed, what access was used, what remains, or what to do next.

---

## The maturity path

Every pattern is tagged with a maturity level. This is the action signal.

| Level | Meaning | What to do |
|-------|---------|------------|
| `judgment` | Too context-dependent to codify | Document the heuristic |
| `guidance` | Ready for a team norm | Write it down |
| `convention` | Ready for a PR template | Add to checklist |
| `rule` | Ready for automated enforcement | SQLFluff, dbt-project-evaluator |
| `deterministic` | Ready for a CI gate | Block merges that violate it |

Promotion is a human decision. Tricorder identifies where patterns sit and what the next step is.

---

## Outputs

### Markdown report

Written to `--out DIR/YYYY-MM-DD-<repo-slug>.md` by `tricorder learn`. Four sections:

1. **Patterns ready to institutionalize** — table with current maturity, next step, target maturity, and standard citation
2. **Reviewer focus fingerprints** — per-reviewer narrative with evidence quotes, blind spots, and signal quality
3. **Author growth profiles** — per-author trajectory, strengths, growth areas, support recommendations
4. **Team gap analysis** — team strengths, gaps by type, review culture observation

### Structured artifacts

Written progressively by each level into `.tricorder/`. See artifact contract above.

### Interactive explorer

A static HTML application served via GitHub Pages. Five tabs:

- **Maturity Pipeline** — patterns arranged in a kanban by maturity level
- **Pattern Coverage** — reviewer × category grid; cells clickable, drawer shows quotes
- **Team Gaps** — gap analysis with type, standard citation, and recommendation
- **Reviewer Fingerprints** — composite radar (all reviewers overlaid) + individual radar cards
- **Author Profiles** — per-author trajectory, strengths, growth areas, support recommendations

### Visibility model

Output files carry a `visibility` field: `private` (all sections), `team` (author profiles redacted), `public` (anonymized patterns and team gaps only). Set at synthesis time with `--visibility`.

### Name maps

For demos and sharing, real GitHub logins can be replaced with aliases. Create `~/.tricorder/<owner>__<repo>-name-map.json` before running `tricorder build`. Applied automatically on build; not stored in the repo.

---

## CLI

Installed via `pip install -e .`. Entry point: `tricorder`.

```
tricorder discover    OWNER/REPO [--lens NAME]
tricorder discover    OWNER/REPO --history [--lens NAME]
tricorder probe       OWNER/REPO [--limit N] [--since YYYY-MM-DD]
tricorder analyze     OWNER/REPO [--since YYYY-MM-DD] [--limit N] [--force]
tricorder learn       OWNER/REPO [--visibility private|team|public] [--out DIR]
                                 [--provider anthropic|gemini] [--model NAME]
                                 [--api-key-env NAME] [--keychain-service NAME]
tricorder interpret   OWNER/REPO [--lens NAME]
tricorder improve     OWNER/REPO [--out DIR]
tricorder build       OWNER/REPO [--out PATH] [--name-map PATH]
tricorder demo        [--fast] [--no-pause]
tricorder --version
```

**v1 compatibility:** v2 names are authoritative. The older commands remain
available through legacy script dispatch so existing workflows are not broken.

| Legacy | Authoritative v2 path |
|---------|------------|
| `ready` | `discover` |
| `harvest` | `analyze` |
| `synthesize` | `learn` |
| `render` | `build` |

---

## LLM provider

The LLM provider is resolved in order: CLI flag → env override (`TRICORDER_LLM_PROVIDER`) → config file → auto-detect from available keys → default (anthropic).

Config at `~/.learn-from-work/config`:
```
provider=anthropic
model=claude-sonnet-4-6
api_key_env=ANTHROPIC_API_KEY
```

Supported providers: Anthropic, Gemini. The prompts and output schema are identical across providers.

---

## Versioning

Format: `MAJOR.MINOR.PATCH.BUILD`

- **BUILD** — auto-incremented by GitHub Actions on every push to main
- **PATCH** — bumped manually for a collection of fixes
- **MINOR** — bumped manually for meaningful new features
- **MAJOR** — bumped manually for structural changes

The `VERSION` file is the source of truth; `pyproject.toml` reads from it dynamically.

---

## Requirements and cost

**Install:**
```bash
git clone https://github.com/dhk/tricorder && cd tricorder && pip install -e .
```

**Credentials:**
- `GITHUB_TOKEN` — classic PAT, `public_repo` scope for public repos, `repo` for private. Required for `analyze` and above.
- LLM API key — `ANTHROPIC_API_KEY` (or macOS keychain `anthropic_api_key`) for Anthropic; `GEMINI_API_KEY` for Gemini. Required for `learn` and above.

`tricorder discover` requires no credentials.

**Cost model (Anthropic claude-sonnet-4-6, June 2026):**
- ~$0.014 per PR (phases 1–4 combined, amortized)
- 60-PR run: ~$0.85
- 90-PR run: ~$1.25
- ~172-PR run (3 months, active team): ~$2.40

Always run `tricorder probe` before `tricorder learn`.

---

## Who should use this

- **Engineering leads and team leads** who want evidence-backed material for growth conversations and coverage gap identification
- **Platform or tooling engineers** identifying what should move from convention to automated enforcement
- **Individual contributors** building a picture of what their team actually values

**Repository requirements:** Active PR review practice on GitHub, 30+ merged PRs in the target window, some inline comment activity. Use `tricorder discover` to assess before investing.

---

## Limitations

**What tricorder cannot see:**
- Verbal review culture — conversations in Slack, Zoom, or standups
- Reviewer availability constraints — a reviewer who never catches testing issues might never be assigned to testing-heavy PRs
- Domain ownership — a reviewer might not comment on an area they know another reviewer will cover
- PRs merged without review
- Sentiment and tone

**Confidence thresholds:**
- Low-quality descriptions reduce the LLM's ability to infer context; flagged in output
- Author growth findings require at least 5–8 reviewed PRs; shorter histories produce `insufficient-data`
- Reviewer blind spots are inferred, not observed

**Scope:**
The `analytics-engineering` lens is currently `Experimental` with strong evidence, while `discover` and `analyze` are designed to be repository-agnostic. The `learn` and `interpret` commands degrade outside analytics-engineering until additional lenses are validated.

---

## Key design decisions

**Why progressive trust?**
V1 required two credentials before producing anything. Users invested trust before seeing value. The progressive model inverts this: `discover` runs with no credentials and produces something interesting immediately. GitHub access and LLM API access are earned by demonstrating value at each prior level.

**Why lens detection, not user configuration?**
Broad scope produces vague output. The lens preserves the domain-specificity that made v1 findings actionable. Auto-detecting the likely lens from the repository fingerprint removes a configuration step that most users would get wrong — and proposes it in a way that is easy to override.

**Why an artifact contract?**
V1 produced outputs designed for humans. The artifact contract makes every analysis stage the foundation for the next — and for external consumers. The future MCP integration depends on stable, structured artifacts that agents can consume without rerunning analysis.

**Why rename the commands?**
V1 names described internal pipeline mechanics (harvest, synthesize, render). V2
names describe what users experience and what they get (analyze, learn, build). The
shipped CLI retains v1 names through legacy dispatch while making v2 authoritative.

**Why a local cache, not a live API?**
The cache enables incremental runs, resume-on-failure, and re-synthesis after prompt changes without re-fetching. The raw data is inspectable on disk — if a result looks wrong, the input is there to check.

**Why Claude, not a keyword classifier?**
Review comments require interpretation. "This model is doing too much" is a grain issue in one PR and a modeling issue in another. Claude reads the comment alongside the PR description, the file path, and the repo context, and makes the same judgment a human reader would.

**Why static HTML for the explorer?**
No build pipeline. Deployable to GitHub Pages with a single `git push`. The data is in `data.js` — swapping repos means swapping one file.

---

## Future: MCP integration

Artifacts will be exposed as MCP resources:

```
mcp://repository/profile
mcp://repository/review-patterns
mcp://repository/learnings
mcp://repository/recommendations
mcp://repository/roadmap
```

External agents will be able to consume repository knowledge without rerunning analysis.

---

## Reference standards

Patterns are grounded against named standards:

- [dbt Labs style guide](https://docs.getdbt.com/best-practices/how-we-style/0-how-we-style-our-dbt-projects)
- [dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator)
- [SQLFluff rule catalog](https://docs.sqlfluff.com/en/stable/rules.html)
- [Kimball dimensional modeling techniques](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- [Google Engineering Practices: code review](https://google.github.io/eng-practices/review/)
- [Smart Bear: 11 proven practices for peer review](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/)

---

## Roadmap

### Completed (v1.0.1.x)

- ✓ First synthesis run — cal-itp/data-infra, ~172 PRs, March–May 2026
- ✓ Interactive HTML explorer deployed to GitHub Pages
- ✓ Composite radar chart (all reviewers overlaid)
- ✓ Readiness check (`tricorder ready`)
- ✓ Installable CLI (`pip install -e .`)
- ✓ Name map anonymization for demos
- ✓ Version scheme with auto-bump on merge
- ✓ HOWTO, DEMO, and presenter guide
- ✓ Codespaces devcontainer
- ✓ Configurable LLM provider — Anthropic and Gemini

### Implemented v2 command surface

- Progressive trust model — `discover` with no credentials, access earned by level
- Discipline lenses — auto-detect archetype, apply domain-specific interpretation
- Artifact contract — structured outputs consumed by subsequent levels and external tools
- Command renames — vocabulary describes user outcomes, not pipeline internals
- Status blocks — access transparency and next-action prompt at every level

### Open

- Second repo run — validate that findings generalize beyond cal-itp (issue #15)
- Trend detection — diff pattern maturity across synthesis runs on the same repo (issue #16)
- Non-analytics-engineering lenses — Python data pipelines, infrastructure-as-code (issue #18)
- MCP integration — expose artifacts as resources for AI agents

### Not planned

- A hosted service or SaaS version
- GitHub App or webhook-based automation
- Real-time review assistance
- Performance evaluation or HR reporting

---

## Status

**v1.0.1.x** — Full pipeline validated and working. Explorer live at [dhk.github.io/tricorder/explorer](https://dhk.github.io/tricorder/explorer/).

**v2 command surface** — Shipped and authoritative. Legacy v1 dispatch remains for
compatibility. [BRIEF.md](BRIEF.md) and [docs/EVOLUTION.md](docs/EVOLUTION.md) retain
the migration history; they do not override the current CLI or HOWTO.

**First synthesis run — cal-itp/data-infra, June 2026:**
- ~172 PRs harvested (March–May 2026), 154 with review activity

_Note: cal-itp/data-infra is an active repository; exact totals vary slightly by run date, window boundaries, and filtering._
- 15 contributors, 14 reviewer profiles, 15 author growth profiles
- 5 institutionalization candidates (maturity: judgment → convention/rule)
- 11 team gaps (5 coverage, 4 blind spots, 2 knowledge)

Key validation finding: review quality is concentrated in one reviewer (high signal) while the broader team defaults to low-signal approvals — including on breaking SQL changes. The composite radar makes this visible at a glance. The finding matched informal prior knowledge about the team, confirming that the synthesis is reading real signal, not producing plausible-sounding noise.
