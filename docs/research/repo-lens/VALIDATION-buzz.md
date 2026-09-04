# Run record: block/buzz under product-engineering

**Date:** 2026-09-04 · **Lens:** product-engineering v1, the parent lens, selected by detection (score 11, margin 4 over platform-engineering) · **Cache:** 272 merged PRs, 17 August to 3 September 2026, 245 with review activity, 817 inline comments · **Cost:** about $5 across nine launches; the resumable, lens-keyed cache meant no paid call was repeated.

This is a run record, not a lens promotion. buzz is a multi-archetype monorepo (Flutter mobile client, Rust backend, Tauri desktop client) and no single lens fits it; the parent lens was the honest choice and DESIGN.md records per-path lenses as the follow-up. The point of the run was to replace the dbt-lens synthesis of buzz, which cited Kimball and dbt-project-evaluator against a Rust and Dart repository, with one that is at least on-domain.

## Checks

| Criterion | Bar | Measured |
|---|---|---|
| Detection | score ≥ 6, margin ≥ 3 (parent lens thresholds) | 11, margin 4 |
| composition_check, review_path_check | pass | pass, 99% of comments on tagged paths |
| Phase 1 `other` share | ≤ 15% | 5.0% (100 of 2004 patterns) |
| Smoke checks | zero | zero |
| Errors in the final cache | zero | zero |

Phase 4 produced eight gaps, seven mapped to a lens axis and one, silent approvals, written directly from the oversight block handed to it. The dbt-lens run of the same repository had produced thirteen, six of them about grain, incremental models, source freshness, and materialization on a repository with no SQL.

## What the run showed that no lens would have

The oversight measurement, which uses no model, is the finding on buzz.

| | Count |
|---|---:|
| Inline comments in the window | 817 |
| By the Codex reviewer bot | 365 |
| By PR authors replying on their own PRs | 378 |
| By a human reviewing someone else's code | 74 |
| PRs where a bot commented and no human reviewer did | 34 of 272 |
| PRs with no human engagement at all | 61 of 272 |
| Silent approvals | 124 of 354 |

Per file tag, of the PRs that changed files there, who commented on those files:

| Tag | PRs touching | Human reviewer | Bot only | Nobody |
|---|---:|---:|---:|---:|
| source | 235 | 24 | 31 | 180 |
| test | 183 | 1 | 3 | 179 |
| docs | 53 | 1 | 0 | 52 |
| config | 34 | 1 | 1 | 32 |
| dependency-manifest | 31 | 0 | 1 | 30 |
| ci | 26 | 0 | 2 | 24 |

Reading: line-level review on buzz has been delegated to the bot. Authors answer the bot, humans issue the approval verdict, and the human inline comment is rare: 74 in three weeks across 272 PRs. Tests were changed in 183 PRs and a human commented on those files once. The approval step is where human oversight still lives, and a third of approvals carry no comment.

This is the inference the framing asked for: what the team delegates to AI review and what it keeps for humans, read from the record rather than asked. The record says the split is line-level to the bot, verdict to the human, and the verdict is often silent.

## Caveats

- The parent lens's axes are generic (test coverage, error handling, observability, API contracts), so the per-axis rows are broad. A per-path mobile lens on `mobile/` would give Flutter-specific axes for the 279 Dart comments.
- `is_human` classifies by login pattern. Two bots on buzz (`chatgpt-codex-connector[bot]`, `github-advanced-security[bot]`) carry the `[bot]` suffix and are classified correctly; a human-named AI account would not be.
- Phase 2 reviewer fingerprints for the bot's review comments are excluded; its 213 review verdicts are all `COMMENTED`, never approvals.

## Reproduce

```
tricorder-synthesize.py block/buzz --visibility private
```

Detection and the phase outputs are cached under `~/.learn-from-work/cache/block__buzz/synthesis/product-engineering-v1/`; `oversight.json` there carries the tables above.
