# tricorder

> *"A room full of data people and you named it tricorder instead of data. Yes, on purpose."*

<img width="1672" height="941" alt="Tricorder explorer showing review-pattern maturity, team gaps, reviewer coverage, and author profiles" src="https://github.com/user-attachments/assets/106d5cca-03eb-47ee-a5fe-281ca98063d2" />

Tricorder helps teams understand how well they build and systematically raise the standard.

Today it does that as a repository learning system: it turns local repository evidence, git history, and code-review discussions into an inspectable map of recurring standards, repeated correction, expertise concentration, team gaps, and opportunities to move useful knowledge upstream into education, workflow, tooling, or automation.

**[Try the live explorer](https://dhk.github.io/tricorder/explorer/)** (sample data) ·
[How to use Tricorder](HOWTO.md) · [Documentation index](docs/README.md) ·
[Privacy and data flow](docs/PRIVACY.md)

## Product governance

Product intent follows this hierarchy:

**[Constitution](CONSTITUTION.md) → [Product Vision](PRODUCT_VISION.md) → [Product Strategy](PRODUCT_STRATEGY.md) → [Roadmap](ROADMAP.md) → Issues and PRs**

[DESIGN.md](DESIGN.md) describes the system architecture. [BRIEF.md](BRIEF.md) is a compatibility summary for older links, not a competing product authority.

## Install

Requires Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install git+https://github.com/dhk/tricorder.git
```

> **npm side effect:** `npm install dhk/tricorder` runs this repository's
> `postinstall` script, which invokes `pip install -e` and changes the Python
> environment selected by `pip3`/`pip`. Use the isolated Python install above if
> you do not want npm to install Python packages. See [HOWTO.md](HOWTO.md#npm-bridge).

## Quick start

```bash
# From inside a git repository
tricorder make-it-so
```

The orchestrator runs what available credentials permit, stores artifacts under
`.tricorder/`, and skips locked levels. Run the levels individually when you want
to inspect the boundary before granting more access:

| Command | Access added | Result |
|---|---|---|
| `tricorder discover` | local files | repository profile and technology fingerprint |
| `tricorder discover --history` | local git history | contributors, hotspots, timeline |
| `tricorder analyze OWNER/REPO` | GitHub read credential | review observations, patterns, expertise map |
| `tricorder learn OWNER/REPO` | configured LLM provider | learnings and named reviewer/author profiles |
| `tricorder interpret OWNER/REPO` | LLM provider + lens | domain interpretation |
| `tricorder improve OWNER/REPO` | LLM provider | prioritized roadmap |
| `tricorder build --open` | local artifacts | interactive explorer at `localhost:7372` |

```text
local files ──> git history ──> GitHub review data ──> LLM analysis ──> explorer
   no key          no key          GitHub credential      provider key     publishable
```

The practical consequence: value begins locally, while every later step crosses a
clearer trust boundary. `analyze` can read private review history; `learn` sends
selected review content and identities to the configured LLM provider; local caches
retain source and generated data; and explorer output may be publishable. Read
[Privacy and data flow](docs/PRIVACY.md) before using credentials or sharing output.

## Lenses

Every LLM phase reads the repository through a discipline lens: a YAML file in
`tricorder/lenses/data/` (override per repo in `.tricorder/lenses/`) that carries the
detection signals, file tags, categories, cited authorities, review axes, prompt
context, and prohibitions for one kind of repository. `discover` picks the lens from
the file tree and can answer `unknown` or `mixed` rather than guess; `learn --dry-run`
shows the lens, the fit checks, and the exact prompts before any LLM call. Shipped:
`analytics-engineering`, `product-engineering`, `product-engineering-desktop`,
`platform-engineering`, `security`, `agent-engineering`. `product-engineering-desktop` is
validated on block/berd ([record](docs/research/repo-lens/findings/perplexity-lenses/VALIDATION.md));
the others are experimental until a production-repository validation passes. Design: [DESIGN.md](DESIGN.md#discipline-lenses);
evidence: [docs/research/repo-lens](docs/research/repo-lens/README.md).

## Oversight density

In agentic development, code review is where human oversight concentrates, so the
review record is the audit trail of human judgment over machine-assisted change. The
failure to detect is rubber-stamping, not a reviewer blind spot. Tricorder therefore
computes, from the harvested record and without a model, how much human attention each
reviewer applies (silent approvals: approve with no comment) and how much each lens axis
receives (PRs that changed files under the axis with no human comment there). Measured
on block/berd on 2026-09-03: every PR that touched the Tauri capabilities manifest or the
CSP configuration merged with no human comment on those files. The numbers appear on the
explorer's Team Gaps and Reviewer Fingerprints tabs and go to Phase 4 as context.

## Primary research supporting the methodology

The lens design is not an opinion about how repositories should be read. It follows a
commissioned research pass, answered from primary sources, that is checked into this
repository so the reasoning can be audited and challenged:

- [How tricorder reads and recognizes a repository](docs/research/repo-lens/tricorder-lens-methodology-research.md)
  (lens methodology research, 2026-09-02). Seven questions, each answered with a verdict table and citations
  carrying title, publisher, URL, and retrieval date.
- [The brief](docs/research/repo-lens/brief.md) that traces every question to the code it
  was meant to fix, and [the handoff prompt](docs/research/repo-lens/handoff-prompt.md)
  that was sent, including the `block/berd` fingerprint used as the test case.
- [The lens file the research produced](docs/research/repo-lens/findings/perplexity-lenses/product-engineering-desktop.yaml),
  now shipped as `tricorder/lenses/data/product-engineering-desktop.yaml`.

What the research established, in brief:

- **Detection** copies the shape of GitHub Linguist: content-only, exclusion-first,
  maintainer-overridable. Ecosystem manifests (`Cargo.toml`, `package.json`,
  `tauri.conf.json`) are strong evidence; community-health and AI-assistant files
  (`SECURITY.md`, `CLAUDE.md`, `AGENTS.md`) appear in repositories of every kind and are
  excluded from inference. Without that exclusion the previous detector classified a
  desktop app as an agent-engineering repository.
- **Taxonomy** follows Backstage's small-core, open-extension model: five top-level
  archetypes, with `product-engineering` as a parent for desktop, mobile,
  backend-service, library, and CLI sub-profiles. Archetype describes the artifact being
  engineered, not its subject matter.
- **Review standards** per domain come from the maintainers of the tools the repository
  uses: for a Tauri desktop app, the Tauri security model, the Rust API Guidelines and
  Clippy, the Rules of React, Playwright's best practices, WCAG 2.2.
- **The maturity ladder** (`judgment → guidance → convention → rule → deterministic`)
  maps onto rustc's `allow / warn / deny / forbid` lint levels and Google's
  enforce-in-build versus advise-in-review split (Sadowski et al., ICSE 2015 and CACM
  2018).
- **Review-comment categories** rest on the modern-code-review literature (Mäntylä and
  Lassenius 2009; Beller et al. 2014; Bacchelli and Bird 2013; Sadowski et al. 2018):
  roughly three quarters of review findings are maintainability rather than functional
  across languages and organisations, which justifies a domain-neutral core with
  per-lens extensions.
- **Thresholds are a design choice.** No published classifier exposes an abstention
  threshold for this problem, so `min_score` and `min_margin` are engineering values to
  be calibrated on a labelled corpus, and the tool reports `unknown` or `mixed` rather
  than guess.

The research also records what it could not settle, in its
[open gaps](docs/research/repo-lens/tricorder-lens-methodology-research.md#open-gaps): no
authoritative `unsafe`-Rust checklist, partial Biome coverage of the React hook rules,
no primary standard for desktop telemetry review or for infrastructure-as-code change
semantics. Those limits are carried into the lenses as maturity ceilings, not papered over.

## Credentials

`analyze` checks `GITHUB_TOKEN`, then `gh auth token`, then supported macOS
Keychain entries. A credential must be able to read the target repository; private
repositories require corresponding private-repository access.

`learn`, `interpret`, and `improve` use Anthropic or Gemini. Set exactly one provider
key, or choose a provider explicitly:

```bash
export GITHUB_TOKEN=...           # never commit it
export ANTHROPIC_API_KEY=...      # or GEMINI_API_KEY
tricorder learn OWNER/REPO --provider anthropic --visibility private
```

Configuration and credential details are in [HOWTO.md](HOWTO.md#credentials).

## Compatibility and maturity

The v2 interface above is authoritative. The v1 commands `ready`, `probe`,
`harvest`, `synthesize`, `render`, and `demo` remain available through legacy script
dispatch for compatibility, but new usage and documentation should use v2.

Tricorder is under active development. The six-level v2 command surface is shipped;
discipline lenses and generated judgments remain experimental and require human
review. Tricorder is not a performance-review system, a developer ranking system, a live code reviewer, or a guarantee that anonymized output is safe to publish.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and test instructions and
[SECURITY.md](SECURITY.md) for private vulnerability reporting.
