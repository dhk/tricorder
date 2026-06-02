# tricorder — Design Document

> *"A room full of data people and you named it tricorder instead of data. Yes, on purpose."*

**Version:** 1.0  
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

Tricorder is a two-phase tool that analyzes the merged pull request history of a dbt/SQL analytics repository and returns a structured map of what the team knows, what it misses, and what is ready to institutionalize.

Phase one (harvest) pulls merged PRs and their review activity from the GitHub API and writes structured JSON to a local cache. Phase two (synthesize) loads that cache, runs four Claude API calls, and produces a Markdown report with reviewer focus fingerprints, per-author growth profiles, and a team-level gap analysis.

The output is a document, not a dashboard. It is designed to be read, discussed, and acted on — not monitored.

---

## What it is not

**Not a metrics dashboard.** Tricorder does not count PRs, measure review cycle time, or report on merge frequency. Those numbers exist elsewhere and answer a different question. Tricorder answers: what is the team actually learning from code review?

**Not a performance review tool.** Author growth profiles describe patterns in the review feedback an author receives — where reviewers consistently intervene, and where they consistently do not. This is material for a manager having a growth conversation, not for an HR system. It is not a ranking or an evaluation.

**Not a replacement for code review.** Tricorder reads historical review data. It does not participate in live review, suggest inline comments, or generate feedback. It looks backward, not forward.

**Not a GitHub Analytics competitor.** GitHub's analytics tools answer questions about activity: who is committing, how fast are PRs merging, what is the review load distribution. Tricorder answers questions about knowledge: what does the team understand, and what does it consistently miss?

---

## The problem in detail

Consider what happens to a substantive code review comment. A senior engineer writes three sentences explaining why a staging model should not expose primary keys directly. The author addresses it. The PR merges. Those three sentences exist in a thread that no one will read again.

If the same issue comes up in the next PR, the reviewer writes it again — or doesn't, because they are tired of repeating themselves, or because they are not assigned to review that PR. The comment either recurs, fades, or gets enforced inconsistently.

This pattern describes the gap between team knowledge and team practice. The knowledge exists — it was written down. But it was written in a format (threaded comments on a closed PR) that makes it nearly impossible to aggregate, analyze, or act on systematically.

The second problem is coverage. A team with three active reviewers has three focus fingerprints. One reviewer catches grain issues. One catches test coverage. One catches documentation. The team may believe its review process is comprehensive when in fact it has systematic blind spots — entire dimensions of code quality that nobody reliably checks because nobody was assigned to own them.

Tricorder makes both problems visible.

---

## Architecture

**Two phases. Independent. Cache-first.**

```
harvest  →  cache  →  synthesize  →  report
```

### Harvest

Pulls merged PRs from the GitHub REST API via the `gh` CLI. For each PR: full metadata, description, and review threads (formal reviews and inline diff comments). Writes structured JSON to `~/.learn-from-work/cache/<owner>__<repo>/`.

The cache is append-only and incremental. Re-running harvest fetches only PRs newer than the last run timestamp. Once written, a PR's cache entry is not re-fetched.

Harvest also captures repo context: `dbt_project.yml` (model paths), `.sqlfluff` (rules already enforced in CI), and the PR template (expected description structure). Synthesis uses this context to avoid recommending things already enforced as CI gates.

Five signals are computed at harvest time and stored with each PR:

- **Description quality score** (high / medium / low) — based on word count and presence of why, what, and testing signals. Low-quality descriptions reduce extraction confidence; Claude is instructed to flag those PR results as tentative.
- **Review iteration count** — CHANGES_REQUESTED states before APPROVED. A count of 2 or more marks the PR as high-signal.
- **Has-reply flag** — inline comments that received a reply are marked; these were substantive enough to warrant discussion.
- **File type tags** — inline comments are tagged by the file they touch (dbt-model, dbt-macro, dbt-test, dbt-schema, python, dbt-config, documentation).
- **Author tenure signal** — how many days of cache history exist for this author. Calibrates how much weight to place on gap findings.

### Synthesize

Loads the cache and runs four Claude API calls (claude-sonnet-4-6):

1. **Per-PR pattern extraction** — one call per PR. Returns structured JSON: patterns identified, evidence quotes, author strengths and gaps, reviewer focus signals for that PR. PRs with no review activity are skipped.

2. **Reviewer fingerprints** — one call per reviewer. Takes their full review history across all cached PRs. Returns: primary focus areas with frequency and standard citations, apparent blind spots with basis, review style, and signal quality rating.

3. **Author growth profiles** — one call per author. Takes their chronological PR + review history. Returns: strengths, growth areas with persistence assessment, support recommendations, and trajectory (improving / stable / regressing / insufficient-data).

4. **Team gap analysis** — one aggregate call. Takes all patterns from step 1 and all reviewer fingerprints from step 2. Returns: team strengths, gaps classified by type (coverage_gap / knowledge_gap / blind_spot), institutionalization candidates with maturity path targets, and review culture observations.

Intermediate results are cached to disk after each call. A failed synthesis run can resume without re-running completed calls.

---

## The maturity path

Every pattern tricorder identifies is tagged with a maturity level. This taxonomy is inherited from the `learn-from-work` skill ecosystem:

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

The maturity tag is the action signal. Tricorder does not promote patterns up this path — it identifies where they currently sit and what the next step is. Promotion is a human decision.

---

## Outputs

A synthesis run produces two outputs:

**Markdown report** — committed to the analysis repo at `adventures-in-ai/tricorder/YYYY-MM-DD-<repo-slug>.md`. Sections: institutionalization candidates (table), reviewer fingerprints (per-reviewer narrative), author growth profiles (per-author narrative, private by default), team gap analysis (strengths, gaps, blind spots, culture observations), methodology and caveats, reference standards.

**React explorer** — an interactive artifact rendered in Claude Chat. Five tabs: pattern heatmap (reviewer × category), maturity pipeline kanban, author profiles with trajectory indicators, team gaps panel, reviewer fingerprint radar charts. The explorer is built on actual synthesis output — it is not a prototype.

**Visibility model** — output files carry a `visibility` field: `private` (all sections), `team` (author profiles redacted), or `public` (anonymized patterns and team gaps only). Default is private. Set at synthesis time with `--visibility team`.

---

## Who should use this

Tricorder is designed for:

- **Analytics engineering teams** using dbt, SQL, and BigQuery/Snowflake/Databricks, with an active PR review practice on GitHub
- **Team leads and managers** who want to understand review culture, identify coverage gaps, and support author growth with specific evidence
- **Platform or tooling engineers** looking to identify what should move from convention to automated enforcement

The minimum viable input is 30–60 merged PRs with substantive review activity. Tricorder degrades gracefully with thin review data — it will tell you the data is thin — but its outputs are most useful when reviewers have been writing detailed comments.

Tricorder is less useful for teams where review happens in Slack rather than GitHub, or where PRs are merged without review.

---

## Requirements and cost

**Dependencies:**
- `gh` CLI, authenticated (`gh auth login`)
- Python 3.9+
- `pip install anthropic requests`
- `GITHUB_TOKEN` — classic PAT, `public_repo` scope (for public repos)
- Anthropic API key in macOS keychain (`anthropic_api_key`) or `ANTHROPIC_API_KEY` env var

**Cost model (claude-sonnet-4-6, May 2026):**
- ~$0.015 per PR (Prompt 1 through 4 combined, amortized)
- 60-PR run: ~$0.90
- 90-PR run: ~$1.35
- 190-PR run (3 months, active team): ~$2.85

Run `tricorder-cost-probe.py` before any full synthesis. It assembles exact prompts from real data, counts tokens, and extrapolates cost. No Claude API spend until you decide to proceed.

---

## Limitations

**What tricorder cannot see:**

- Verbal review culture — conversations that happen in Slack, Zoom, or standups before a PR is opened
- Reviewer availability constraints — a reviewer who never catches testing issues might simply never be assigned to testing-heavy PRs
- Domain ownership — a reviewer might not comment on an area they know another reviewer will cover
- PRs merged without review — the no-review rate is reported; the analysis is silent on what those PRs contained
- Sentiment and tone — tricorder reads the content of review comments, not their register

**Confidence thresholds:**

- PR description quality affects extraction confidence. Low-quality descriptions (under 50 words, no why/what/testing signals) reduce Claude's ability to infer context. These PRs are flagged in the output.
- Author growth findings require at least 5–8 PRs with reviews in the window to be reliable. Shorter histories produce `insufficient-data` trajectories.
- Reviewer blind spots are inferred, not observed. A blind spot finding means: this named standard never appeared in this reviewer's comments. It does not mean the reviewer is unaware of it.

**Scope:**

Tricorder is scoped to dbt/SQL analytics repositories. The category taxonomy, standard citations, and prompt design are calibrated for this domain. Running it against a React application or a Go service will produce output, but the standard citations and category tags will not fit well.

---

## Key design decisions

**Why Claude, not a keyword classifier?**  
Review comments require interpretation. "This model is doing too much" is a grain issue in one PR and a modeling issue in another. A keyword approach would miss the context. Claude reads the comment alongside the PR description, the file path, and the repo context, and makes the same judgment a human reader would.

**Why a local cache, not a live API?**  
The cache enables incremental runs, resume-on-failure, and synthesis without re-fetching. It also means the raw data is inspectable. If a synthesis result looks wrong, the input data is on disk.

**Why Markdown output, not a database?**  
The primary consumer of tricorder output is a human reading a document. Markdown commits to git, diffs cleanly, and publishes anywhere. A database would add infrastructure for a problem that does not require it.

**Why filter dependabot PRs?**  
Dependency bump PRs have no engineering signal. Tricorder filters them before synthesis to avoid diluting the analysis with auto-generated content.

**Why dbt/SQL scope only?**  
Broad scope produces vague output. Calibrating the category taxonomy and standard citations to a specific domain makes the findings specific enough to act on. Expansion to other domains (Python data pipelines, infrastructure as code) is a future milestone, not a current goal.

---

## Reference standards

Patterns are grounded against named standards. Where a review comment maps to a documented convention, tricorder cites it:

- [dbt Labs style guide](https://docs.getdbt.com/best-practices/how-we-style/0-how-we-style-our-dbt-projects)
- [dbt-project-evaluator](https://github.com/dbt-labs/dbt-project-evaluator)
- [SQLFluff rule catalog](https://docs.sqlfluff.com/en/stable/rules.html)
- [Kimball dimensional modeling techniques](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/)
- [Google Engineering Practices: code review](https://google.github.io/eng-practices/review/)
- [Smart Bear: 11 proven practices for peer review](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/)

---

## Roadmap

### Now
First synthesis run against a public dbt/BigQuery analytics team (190 PRs, March–May 2026). Validate that the four output sections are populated and coherent. Refine prompts based on actual output quality.

### Near
- React explorer built against real synthesis output
- Deploy as a live Claude skill in the `adventures-in-ai` ecosystem
- Expand cost probe to support `--output json` for programmatic go/no-go decisions

### Later
- Second repo run (contrast repo with different team culture) to validate generalizability
- Trend detection: diff pattern maturity across synthesis runs on the same repo, flag promotions and regressions
- Skill ecosystem integration: surface top institutionalization candidate in `weekly-reset`; log synthesis runs to `captains-log`
- Domain expansion: Python data pipelines, infrastructure as code

### Not planned
- A hosted service or SaaS version
- GitHub App or webhook-based automation
- Real-time review assistance

---

## Status

Tricorder is early and experimental. The harvest pipeline, synthesis prompts, and Markdown report renderer are complete and validated against production data.

**First synthesis run complete** — cal-itp/data-infra, 2026-06-02.
- 190 PRs harvested (March–May 2026), 184 with review activity
- 15 contributors, 14 reviewers with fingerprint profiles
- 5 institutionalization candidates identified (maturity: judgment → convention → rule)
- 11 team gaps classified (5 coverage gaps, 3 blind spots, 3 knowledge gaps)
- Output report: `adventures-in-ai/tricorder/2026-06-02-cal-itp__data-infra.md`

Key validation finding: the four synthesis prompts produced coherent, specific, actionable output. The reviewer fingerprint and author growth profile sections are the strongest — Claude read 184 PR threads and returned named-pattern findings with evidence quotes and concrete support recommendations, not generic advice. The team gap section correctly identified that review quality is concentrated in one reviewer (chrisyamas) while the broader team defaults to low-signal LGTM approvals — a finding that matched informal prior knowledge about the team.

The implementation lives in two places: this repo (`dhk/tricorder`) contains the specification, cost probe, and synthesis script. The `adventures-in-ai` repo contains synthesis outputs as they are produced.
