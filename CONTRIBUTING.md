# Contributing to Tricorder

Thank you for improving Tricorder. The v2 command surface is authoritative; preserve working v1 dispatch unless a change explicitly includes a compatibility migration.

## Product governance

Product decisions follow this chain of intent:

**Constitution → Product Vision → Product Strategy → Roadmap → Issues and PRs**

Before proposing substantial product work:

1. Check [CONSTITUTION.md](CONSTITUTION.md) for enduring boundaries and non-negotiables.
2. Check [PRODUCT_VISION.md](PRODUCT_VISION.md) for the product direction.
3. Check [PRODUCT_STRATEGY.md](PRODUCT_STRATEGY.md) for the current bets, measures, and explicit unknowns.
4. Check [ROADMAP.md](ROADMAP.md) for current intent.
5. Make the issue or PR explain which roadmap intent it implements, or explicitly propose the roadmap/strategy change first.

Do not use an implementation PR to silently redefine the product. If evidence suggests the strategy or vision is wrong, change the appropriate governing document explicitly.

[DESIGN.md](DESIGN.md) describes system design and architecture; it does not override product governance.

## Development setup

```bash
git clone https://github.com/dhk/tricorder.git
cd tricorder
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Run the complete local suite and credential-free smoke commands:

```bash
python -m unittest discover -v
tricorder --help
tricorder --version
tricorder discover --help
tricorder analyze --help
tricorder learn --help
tricorder interpret --help
tricorder improve --help
tricorder build --help
```

For an end-to-end local smoke test, create a throwaway git repository and run `tricorder discover` and `tricorder discover --history`; the test suite does this without network credentials.

## Fixtures and sensitive data

Use synthetic, minimal fixtures with invented repository names and identities. Never commit real credentials, private PR/review content, contributor identities, `.tricorder/`, `~/.learn-from-work/cache/`, generated reports, name maps, or explorer data derived from a private run. Scrubbing a login is insufficient when quotations, paths, dates, or context can re-identify a person.

Tests that need network services must be opt-in and must not print secrets or full private payloads. Prefer dependency injection and recorded synthetic responses.

## Pull requests

Keep changes focused, explain user-visible behavior and data-boundary changes, add or update tests, and list the commands used for validation. Documentation must identify whether a command reads local files, calls GitHub, calls an LLM provider, writes local artifacts, or creates remote state.

Product PRs should identify the roadmap intent they implement and call out any requested change to strategy, vision, or constitutional boundaries.

By participating, follow the project's existing license and GitHub community norms.
