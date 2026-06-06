# tricorder — Design Document

> *"A room full of data people and you named it tricorder instead of data. Yes, on purpose."*

**Version:** 1.0.1.0  
**Status:** Active — validated against one production dbt/BigQuery team  
**Repo:** [dhk/tricorder](https://github.com/dhk/tricorder)

---

## Thesis

Software repositories contain two kinds of content. The first is code — what teams build, version, and deploy. The second is everything else: the comments on pull requests, the review threads, the back-and-forth before a merge. This content is rich with information about how a team thinks, what it values, where it struggles, and what it has learned.

Almost none of it gets used.

Code review comments are the most honest knowledge base most teams produce. They are more current than wikis, less curated than runbooks, and more candid than retrospectives. The problem is that they exist only in threads — visible one at a time, searchable only if you know what you're looking for, and effectively lost when a reviewer leaves the team.

Tricorder reads that record and extracts the signal.

The broader thesis: non-code repository content — reviews, comments, discussions — is training material. Not just for human processes (conventions, checklists, CI gates), but for AI tools that assist the work. A team's review history contains the implicit standards that govern their codebase. Making those standards explicit is the first step toward encoding them anywhere useful.

---

## What tricorder is

Tricorder is a CLI tool that analyzes the merged pull request history of a dbt/SQL analytics repository and returns a structured map of what the team knows, what it misses, and what is ready to institutionalize.

It runs in five steps:

```bash
tricorder ready      OWNER/REPO          # is this repo a good candidate?
tricorder probe      OWNER/REPO          # what will it cost?
tricorder harvest    OWNER/REPO          # pull PR data from GitHub
tricorder synthesize OWNER/REPO          # run four LLM calls
tricorder render     OWNER/REPO          # generate the interactive explorer
```

The output is a Markdown report and a static HTML explorer — both designed to be read, discussed, and acted on.

---

## What it is not

**Not a metrics dashboard.** Tricorder does not count PRs, measure review cycle time, or report on merge frequency. Those numbers exist elsewhere. Tricorder answers: what is the team actually learning from code review?

**Not a performance review tool.** Author growth profiles describe patterns in the review feedback an author receives — where reviewers consistently intervene, and where they consistently do not. This is material for a growth conversation, not an HR system. It is not a ranking or an evaluation.

**Not a replacement for code review.** Tricorder reads historical review data. It does not participate in live review, suggest inline comments, or generate feedback. It looks backward, not forward.

**Not a GitHub Analytics competitor.** GitHub's analytics tools answer questions about activity. Tricorder answers questions about knowledge: what does the team understand, and what does it consistently miss?

---

## The problem in detail

Consider what happens to a substantive code review comment. A senior engineer writes three sentences explaining why a staging model should not expose primary keys directly. The author addresses it. The PR merges. Those three sentences exist in a thread that no one will read again.

If the same issue comes up in the next PR, the reviewer writes it again — or doesn't, because they are tired of repeating themselves, or because they are not assigned to review that PR. The comment either recurs, fades, or gets enforced inconsistently.

This pattern describes the gap between team knowledge and team practice. The knowledge exists — it was written down. But it was written in a format (threaded comments on a closed PR) that makes it nearly impossible to aggregate, analyze, or act on systematically.

The second problem is coverage. A team with three active reviewers has three focus fingerprints. One reviewer catches grain issues. One catches test coverage. One catches documentation. The team may believe its review process is comprehensive when in fact it has systematic blind spots — entire dimensions of code quality that nobody reliably checks because nobody was assigned to own them.

Tricorder makes both problems visible.

---

## Architecture

**Five scripts. One cache. One explorer.**

```
ready → probe → harvest → synthesize → render
                   ↓              ↓         ↓
               ~/.learn-from-work/cache/  report.md  explorer/data.js
```

### `tricorder ready`

Pre-flight check. Uses only the GitHub REST API — no Claude spend. Checks PR volume, review density, inline comment rate, dbt/SQL markers, description quality, and PR template presence. Returns GO / CAUTION / NO-GO per finding with a recommended action for each. Prevents spending money on a repo that will produce thin output.

### `tricorder probe`

Cost estimator. Pulls a sample of real PRs, assembles the exact prompts, counts tokens, and prints a cost table with extrapolations. No Claude API spend until you decide to proceed. Typical: ~$0.015/PR.

### `tricorder harvest`

Pulls merged PRs from the GitHub REST API. For each PR: metadata, description, formal review threads, and inline diff comments. Writes structured JSON to `~/.learn-from-work/cache/<owner>__<repo>/`.

The cache is append-only and incremental — re-running only fetches PRs newer than the last harvest. Bot PRs (Dependabot etc.) are filtered before writing.

Five signals are computed and stored with each PR:

- **Description quality score** (high / medium / low) — word count + presence of why, what, and testing signals
- **Review iteration count** — CHANGES_REQUESTED states before approval; ≥2 marks the PR as high-signal
- **Has-reply flag** — inline comments that received a reply; proxy for substantive discussion
- **File type tags** — comments tagged by file touched (dbt-model, dbt-schema, python, etc.)
- **Author tenure** — days of cache history for this author; calibrates confidence in growth findings

Harvest also captures repo context: `dbt_project.yml`, `.sqlfluff` (rules already enforced in CI), and the PR template. Synthesis uses this context to avoid recommending things already enforced as CI gates.

### `tricorder synthesize`

Loads the cache, resolves the active LLM provider from config or CLI flag, and runs four provider-selected LLM calls:

1. **Per-PR pattern extraction** — one call per PR. Returns structured JSON: patterns identified, evidence quotes, author signals, reviewer signals. PRs with no review activity are skipped.

2. **Reviewer fingerprints** — one call per reviewer. Returns: primary focus areas with frequency and standard citations, apparent blind spots with basis, review style, and signal quality rating.

3. **Author growth profiles** — one call per author. Returns: strengths, growth areas with persistence assessment, support recommendations, and trajectory (improving / stable / regressing / insufficient-data).

4. **Team gap analysis** — one aggregate call. Returns: team strengths, gaps classified by type (coverage_gap / knowledge_gap / blind_spot), institutionalization candidates with maturity path targets, and review culture observation.

Intermediate results are cached after each call. A failed run can resume from the last completed phase.

Outputs a Markdown report to `--out DIR` (default: `./output/` if no prior path exists).

### `tricorder render`

Reads the synthesis cache and writes `explorer/data.js` — the data layer for the static HTML explorer. Applies a name map if one exists at `~/.tricorder/<owner>__<repo>-name-map.json`, replacing real GitHub logins with aliases before writing.

The explorer is deployed to GitHub Pages at `https://OWNER.github.io/tricorder/explorer/`. Pushing `data.js` is the only deploy step.

---

## The maturity path

Every pattern tricorder identifies is tagged with a maturity level:

```
judgment → guidance → convention → rule → deterministic
```

| Level | Meaning | What to do |
|-------|---------|------------|
| `judgment` | Too context-dependent to codify | Document the heuristic |
| `guidance` | Ready for a team norm document | Write it down |
| `convention` | Ready for a PR checklist or template | Add to template |
| `rule` | Ready for automated enforcement | SQLFluff or dbt-project-evaluator |
| `deterministic` | Ready for a CI gate | Block merges that violate it |

The maturity tag is the action signal. Tricorder identifies where patterns currently sit and what the next step is. Promotion is a human decision.

---

## Outputs

### Markdown report

Written to `--out DIR/YYYY-MM-DD-<repo-slug>.md`. Four sections:

1. **Patterns ready to institutionalize** — table with current maturity, next step, target maturity, and standard citation
2. **Reviewer focus fingerprints** — per-reviewer narrative: primary focus areas with evidence quotes, apparent blind spots with basis, review style and signal quality
3. **Author growth profiles** — per-author narrative: strengths, growth areas with persistence, support recommendations, trajectory
4. **Team gap analysis** — team strengths, gaps by type, review culture observation

### Interactive explorer

A static HTML application served via GitHub Pages. Five tabs:

- **Maturity Pipeline** — patterns arranged in a kanban by maturity level
- **Pattern Coverage** — reviewer × category grid driven by `category_freq` from fingerprints; cells clickable, drawer shows quotes and focus areas
- **Team Gaps** — 11-gap analysis with gap type, standard citation, and recommendation
- **Reviewer Fingerprints** — composite radar (all reviewers overlaid) + individual radar cards with focus areas and blind spots
- **Author Profiles** — per-author trajectory, strengths, growth areas, support recommendations

### Visibility model

Output files carry a `visibility` field: `private` (all sections), `team` (author profiles redacted), `public` (anonymized patterns and team gaps only). Set at synthesis time with `--visibility`.

### Name maps

For demos and sharing, real GitHub logins can be replaced with aliases. Create `~/.tricorder/<owner>__<repo>-name-map.json` before running `tricorder render`. Applied automatically on render; not stored in the repo.

---

## CLI

Installed via `pip install -e .`. Entry point: `tricorder`.

```
tricorder ready      OWNER/REPO [--days N]
tricorder probe      OWNER/REPO [--limit N] [--since YYYY-MM-DD]
tricorder harvest    OWNER/REPO [--since YYYY-MM-DD] [--limit N] [--force]
tricorder synthesize OWNER/REPO [--visibility private|team|public] [--out DIR]
                               [--provider anthropic|gemini] [--model NAME]
                               [--api-key-env NAME] [--keychain-service NAME]
tricorder render     OWNER/REPO [--out PATH] [--name-map PATH]
tricorder demo       [--fast] [--no-pause]
tricorder --version
```

`tricorder demo` runs a scripted 5-scene walkthrough (cost probe → harvest → synthesis phases 1–4 → report) using pre-baked cal-itp/data-infra data and Trek aliases. No GitHub or Claude API calls.

---

## Versioning

Version format: `MAJOR.MINOR.PATCH.BUILD`

- **BUILD** — auto-incremented by GitHub Actions on every push to main
- **PATCH** — bumped manually when a collection of fixes warrants a label
- **MINOR** — bumped manually for meaningful new features
- **MAJOR** — bumped manually for structural changes

Current version: `1.0.1.0`. The `VERSION` file is the source of truth; `pyproject.toml` reads from it dynamically.

---

## Who should use this

- **Analytics engineering teams** using dbt, SQL, and BigQuery/Snowflake/Databricks, with an active PR review practice on GitHub
- **Team leads and managers** who want evidence-backed material for growth conversations and coverage gap identification
- **Platform or tooling engineers** identifying what should move from convention to automated enforcement

The minimum viable input is 30+ merged PRs with substantive inline review activity. Use `tricorder ready` to check before investing.

---

## Requirements and cost

**Install:**
```bash
git clone https://github.com/dhk/tricorder && cd tricorder && pip install -e .
```

**Credentials:**
- `GITHUB_TOKEN` — classic PAT, `public_repo` scope for public repos, `repo` for private
- LLM API key — `ANTHROPIC_API_KEY` (or macOS keychain `anthropic_api_key`) for Anthropic; `GEMINI_API_KEY` for Gemini

**LLM provider config** (`~/.learn-from-work/config`):
```
provider=anthropic          # anthropic | gemini
model=claude-sonnet-4-6     # or gemini-2.0-flash, etc.
api_key_env=ANTHROPIC_API_KEY
```
Provider resolves in order: CLI flag → env override (`TRICORDER_LLM_PROVIDER`) → config file → auto-detect from available keys → default (anthropic).

**Cost model (Anthropic claude-sonnet-4-6, June 2026):**
- ~$0.014 per PR (phases 1–4 combined, amortized)
- 60-PR run: ~$0.85
- 90-PR run: ~$1.25
- 190-PR run (3 months, active team): ~$2.65

Always run `tricorder probe` first. The probe assembles the exact prompts from real data, counts tokens, and extrapolates cost. Most useful for Anthropic runs — Gemini uses the same prompts but different billing, so treat the probe as directional there.

---

## Limitations

**What tricorder cannot see:**
- Verbal review culture — conversations in Slack, Zoom, or standups
- Reviewer availability constraints — a reviewer who never catches testing issues might never be assigned to testing-heavy PRs
- Domain ownership — a reviewer might not comment on an area they know another reviewer will cover
- PRs merged without review — the no-review rate is reported; the analysis is silent on what those PRs contained
- Sentiment and tone — tricorder reads content, not register

**Confidence thresholds:**
- Low-quality descriptions reduce Claude's ability to infer context; these PRs are flagged in output
- Author growth findings require at least 5–8 reviewed PRs in the window; shorter histories produce `insufficient-data`
- Reviewer blind spots are inferred, not observed — a blind spot means this standard never appeared in this reviewer's comments, not that the reviewer is unaware of it

**Scope:**
Tricorder is scoped to dbt/SQL analytics repositories. The category taxonomy, standard citations, and prompt design are calibrated for this domain. Output on other repository types degrades — findings become generic and standard citations stop mapping.

---

## Key design decisions

**Why Claude, not a keyword classifier?**
Review comments require interpretation. "This model is doing too much" is a grain issue in one PR and a modeling issue in another. Claude reads the comment alongside the PR description, the file path, and the repo context, and makes the same judgment a human reader would.

**Why a provider layer?**
Different environments have different keys and different LLM access. Tricorder resolves the active provider from a shared config file or a CLI flag, so a personal Anthropic setup and a work Gemini setup can run the same pipeline without code changes. The prompts and output schema are identical across providers.

**Why a local cache, not a live API?**
The cache enables incremental runs, resume-on-failure, and re-synthesis after prompt changes without re-fetching. The raw data is inspectable on disk — if a result looks wrong, the input is there to check.

**Why Markdown output, not a database?**
The primary consumer of tricorder output is a human reading a document. Markdown commits to git, diffs cleanly, and publishes anywhere.

**Why static HTML for the explorer, not a React app with a build step?**
The explorer is a single `index.html` + a handful of `.jsx` files transpiled by Babel in the browser. No build pipeline. Deployable to GitHub Pages with a single `git push`. The data is in `data.js` — swapping repos means swapping one file.

**Why dbt/SQL scope only?**
Broad scope produces vague output. Calibrating the category taxonomy and standard citations to a specific domain makes findings specific enough to act on.

**Why a readiness check before the cost probe?**
The cost probe still makes GitHub API calls and takes 30 seconds. The readiness check answers a prior question — is this repo even a good candidate? — in a way that surfaces rubber-stamp teams and Slack-heavy cultures before any real investment.

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

### Completed (v1.0.1.0)

- ✓ First synthesis run — cal-itp/data-infra, 190 PRs, March–May 2026
- ✓ Interactive HTML explorer deployed to GitHub Pages
- ✓ Composite radar chart (all reviewers overlaid)
- ✓ Readiness check (`tricorder ready`)
- ✓ Installable CLI (`pip install -e .`)
- ✓ Name map anonymization for demos
- ✓ Version scheme with auto-bump on merge (1.0.0.x)
- ✓ HOWTO, DEMO, and presenter guide
- ✓ Codespaces devcontainer
- ✓ Configurable LLM provider — Anthropic and Gemini, resolved from `~/.learn-from-work/config` or CLI flag (PR #24)

### Open

- Second repo run — validate that findings generalize beyond cal-itp (issue #15)
- Trend detection — diff pattern maturity across synthesis runs on the same repo (issue #16)
- Domain expansion — Python data pipelines, infrastructure-as-code (issue #18, broader)

### Under discussion

- Scope expansion: from dbt/SQL analytics to any repository type, with discipline lenses per repo archetype (issue #22)
- Progressive trust model: start from local filesystem, earn GitHub access, earn Claude API access incrementally
- Artifact contract: structured outputs consumed by MCP servers and external agents

### Not planned

- A hosted service or SaaS version
- GitHub App or webhook-based automation
- Real-time review assistance

---

## Status

Tricorder is at v1.0.1.0. The full pipeline is validated and working. The explorer is live.

**First synthesis run — cal-itp/data-infra, June 2026:**
- 172 PRs harvested (March–May 2026), 154 with review activity
- 15 contributors, 14 reviewer profiles, 15 author growth profiles
- 5 institutionalization candidates (maturity: judgment → convention/rule)
- 11 team gaps (5 coverage, 4 blind spots, 2 knowledge)

Key validation finding: review quality is concentrated in one reviewer (high signal) while the broader team defaults to low-signal approvals — including on breaking SQL changes. The composite radar makes this visible at a glance. The finding matched informal prior knowledge about the team, confirming that the synthesis is reading real signal, not producing plausible-sounding noise.

The next strategic question — whether to stay scoped to dbt/SQL or expand to a broader progressive model — is open in issue #22.
