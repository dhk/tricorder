# tricorder

> *"A room full of data people and you named it tricorder instead of data. Yes, on purpose."*

<img width="1672" height="941" alt="Tricorder explorer showing review-pattern maturity, team gaps, reviewer coverage, and author profiles" src="https://github.com/user-attachments/assets/106d5cca-03eb-47ee-a5fe-281ca98063d2" />

A repository learning system. Tricorder turns local repository evidence, git history,
and code-review discussions into an inspectable map of what a team knows, repeatedly
misses, and could move upstream into guidance, tooling, or automation.

**[Try the live explorer](https://dhk.github.io/tricorder/explorer/)** (sample data) ·
[How to use Tricorder](HOWTO.md) · [Documentation index](docs/README.md) ·
[Privacy and data flow](docs/PRIVACY.md)

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
review. Tricorder is not a performance-review system, a live code reviewer, or a
guarantee that anonymized output is safe to publish.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development and test instructions and
[SECURITY.md](SECURITY.md) for private vulnerability reporting.
