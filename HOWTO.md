# How to use Tricorder v2

This is the authoritative operating guide for the v2 interface:
`discover → analyze → learn → interpret → improve → build`. Each step leaves
inspectable artifacts under `.tricorder/`; do not commit that directory.

## Install from source in isolation

Python 3.9+ and git are required. A virtual environment prevents Tricorder and its
dependencies from modifying your system Python or another project's environment.

```bash
git clone https://github.com/dhk/tricorder.git
cd tricorder
python3 -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
tricorder --version
tricorder --help
```

Leave the environment with `deactivate`. To remove this isolated installation,
delete only the `.venv` directory you created.

### npm bridge

```bash
npm install dhk/tricorder
```

**This is not a JavaScript-only install.** npm automatically runs `node install.js`
through `postinstall`. That script locates `pip3` or `pip` on `PATH` and runs
`pip install -e <npm-package-directory>`. It can therefore install Python packages
and an editable `tricorder` command into whichever Python environment that `pip`
selects. The script soft-fails (npm may succeed even if pip fails). Prefer the
virtual-environment procedure above when isolation or reproducibility matters.

## Start locally

From the repository you want to inspect:

```bash
tricorder discover
tricorder discover --history
```

These commands require no credentials or network. `discover` reads the local
filesystem; `--history` additionally invokes local git history. Review the generated
`.tricorder/` artifacts before continuing.

## Credentials

### GitHub

`tricorder analyze` uses the first credential it finds:

1. `GITHUB_TOKEN` in the process environment;
2. the token returned by an authenticated `gh` CLI;
3. a supported macOS Keychain entry (`github-tricorder-pat` or
   `github-fossil-pat`).

Use a dedicated, least-privilege credential that can read only the repositories you
intend to analyze. For a public repository, read access to public repository data is
enough. For a private repository, the token or GitHub CLI identity must explicitly
have access to that repository and its pull requests. Organization SSO or token
policies may require additional authorization. Tricorder performs GitHub reads in
`analyze`; it writes results locally.

```bash
export GITHUB_TOKEN=...       # placeholder only; never put a real token in docs
tricorder analyze OWNER/REPO --since 2026-01-01 --limit 20
```

The cache includes PR titles and bodies, review bodies, inline comments, file paths,
GitHub logins, and small repository context files fetched through the GitHub API.
Treat a private repository's `.tricorder/` directory as private review data.

### LLM providers

Tricorder supports Anthropic and Gemini. Provider selection can come from CLI flags,
environment overrides, or `~/.learn-from-work/config`. The config names the provider,
model, and environment variable; it should not contain the secret itself.

```text
provider=anthropic
model=claude-sonnet-4-6
api_key_env=ANTHROPIC_API_KEY
```

```bash
export ANTHROPIC_API_KEY=...
tricorder learn OWNER/REPO --provider anthropic --visibility private
```

If both supported provider keys are present, pass `--provider` or set
`TRICORDER_LLM_PROVIDER`; Tricorder otherwise refuses to guess. Anthropic keys can
also be resolved from the configured macOS Keychain service. Before running an LLM
level, confirm that your provider account, retention settings, region, and agreement
permit transmission of the repository's review data.

## Run the v2 levels

### 1. Discover the repository

```bash
tricorder discover
tricorder discover --history
```

Level 0 writes a profile and fingerprint. Level 1 adds contributor, hotspot, and
timeline artifacts based on local git history.

### 2. Analyze review history

```bash
tricorder analyze OWNER/REPO --since 2026-01-01
```

Useful flags are `--limit N` for a small validation run, `--force` to refresh cached
records, and `--deny`/`--allow` to filter reviewer logins. This level calls GitHub
but not an LLM. Artifacts are stored below `.tricorder/OWNER__REPO/`, including raw
per-PR caches in `.raw/`.

### 3. Learn from review content

```bash
tricorder learn OWNER/REPO --provider anthropic --visibility private --out ./reports
```

This sends PR descriptions, formal review text, inline comments, file paths, and
associated GitHub identities/context to the configured LLM as needed for per-PR
patterns, reviewer fingerprints, author growth profiles, and team gaps. Intermediate
responses are cached under `.tricorder/OWNER__REPO/.raw/synthesis/` for resume.

`--visibility` currently controls the optional Markdown report:

- `private`: includes named reviewer and author profiles;
- `team`: omits author profiles, but reviewer identities remain;
- `public`: omits author profiles, but is **not** a complete anonymization guarantee.

All modes still generate named local JSON artifacts and synthesis caches. Do not
publish them. Visibility is an output-format choice, not an access-control boundary.

### 4. Interpret with a lens

```bash
tricorder interpret OWNER/REPO --lens analytics-engineering
```

Interpretation reads Level 3 artifacts and sends relevant material to the chosen LLM
for domain-specific judgment. Lenses are experimental; review citations and
recommendations rather than treating them as authoritative.

### Lenses: how the domain gets chosen

Every LLM phase (`learn` and `interpret`, and the legacy synthesize script) reads the
repository through a discipline lens. Lenses are YAML files in
`tricorder/lenses/data/`; drop an override into `.tricorder/lenses/` (per repository)
or `~/.tricorder/lenses/` (per user). `discover` selects one from the file tree and
records it in `repository-profile.yml`; `learn` reads that, or `--lens NAME`, or, when
neither exists and a GitHub token is available, detects it from the GitHub tree.

Before spending on an LLM run, dry-run:

```bash
tricorder learn OWNER/REPO --dry-run
```

This prints the lens, the two verification checks, the tooling gates found, and the
Phase 1 and Phase 4 system prompts, and makes no LLM calls. Outcomes:

| `discover` says | Meaning | Do |
|-----------------|---------|----|
| `selected` | one lens cleared its `min_score` with a `min_margin` lead | run |
| `mixed` | the runner-up is close; its axes go to Phase 4 as a secondary section, reported only with evidence | run, or choose with `--lens` |
| `unknown` | nothing cleared `min_score` | pass `--lens NAME`, or write a lens |
| `composition_check ✗` | the language mix contradicts the lens | pick another lens, or `--force` |
| `review_path_check ✗` | reviewers comment on paths the lens cannot tag | pick another lens, or `--force` |

Phase outputs are cached per lens, under `.raw/synthesis/<lens>-v<version>/` (legacy
caches: `synthesis/<lens>-v<version>/`), and every cached file is stamped with the lens
that produced it. Switching lenses therefore starts a fresh set of LLM calls rather than
reusing outputs made under another lens's prompts; a pre-existing flat cache is moved
into a sub-directory on first use, named from its recorded lens or `pre-lens`.
`synthesis/current.json` names the directory of the most recent run.

`learn` also computes **oversight density** from the harvested record alone, with no
model involved: per reviewer, how many approvals carried no comment; per lens axis, how
many PRs changed files under that axis and received no human comment there. It is
written to `oversight.json` beside the phase outputs, handed to Phase 4 as context, and
shown on the explorer's Team Gaps and Reviewer Fingerprints tabs. `analyze` now records
each PR's changed files to make this possible and backfills them for cached PRs.

After a run, `learnings.json` records the lens, the checks, the tooling gates, and any
smoke-check hits (off-domain terms the lens forbids). A run with smoke-check hits exits
non-zero; its cached phase outputs are kept so you can fix the lens and re-run.

### 5. Produce an improvement plan

```bash
tricorder improve OWNER/REPO
```

This uses prior artifacts and the configured LLM to write a prioritized roadmap.
`--forge` can create repository changes and GitHub objects; review its prompts and
target carefully before authorizing that separate write workflow.

### 6. Build and inspect the explorer

```bash
tricorder build OWNER/REPO --open
```

The local server uses `http://localhost:7372`. A hosted sample is available at the
[live explorer](https://dhk.github.io/tricorder/explorer/).

`build` writes `explorer/data.js`, a portable JavaScript data file. With no name map,
it contains real identities and is labeled private. A name map replaces configured
login strings with aliases and changes the explorer label to team, but aliases alone
do not remove identifying quotations, repository names, file paths, rare events, or
other context. Inspect the complete generated file before any publication.

```json
{
  "mapping": {
    "github-login": "Reviewer-A"
  }
}
```

Save that example as `~/.tricorder/OWNER__REPO-name-map.json`, or pass
`--name-map PATH`. Never commit the source map.

## Run the complete pipeline

```bash
tricorder make-it-so OWNER/REPO
```

This is convenient after you understand the boundaries. It skips levels whose
credentials are unavailable. Running commands individually is safer for a first use
because you can inspect artifacts before GitHub or LLM access is added.

## Troubleshooting and cleanup

- `No GitHub token found`: set a valid `GITHUB_TOKEN` or authenticate `gh`.
- `review-observations.json not found`: run `tricorder analyze` for the same repo.
- LLM key missing or ambiguous: set one provider key and/or pass `--provider`.
- Interrupted `learn`: rerun it; completed intermediate responses are reused.
- To remove local analysis, delete the specific repository subdirectory under
  `.tricorder/` after confirming it is the intended target.

## v1 history and compatibility reference

The original interface used `ready`, `probe`, `harvest`, `synthesize`, `render`, and
`demo`. Those commands still dispatch to the historical scripts so existing callers
are not broken. They are compatibility entry points, not the current workflow.

| Historical v1 concept | Authoritative v2 path |
|---|---|
| readiness scan | `tricorder discover` |
| harvest GitHub data | `tricorder analyze` |
| synthesize report | `tricorder learn` |
| render explorer | `tricorder build` |
| end-to-end sequence | `tricorder make-it-so` |

For architectural history, see [EVOLUTION.md](docs/EVOLUTION.md). For current
behavior, use this guide, [README.md](README.md), and command `--help` output.
