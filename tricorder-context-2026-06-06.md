# tricorder — Session Context Snapshot
**Date:** 2026-06-06 (updated end-of-session)  
**Sessions:** b82e43ca (build session) → current session (design review)  
**Repo:** `/Users/dhk/Documents/dev/tricorder`  
**Branch:** `feat/v2-cli-implementation`  
**Version:** 1.0.1.3 (auto-bumped on main)  
**PR #23:** Merged ✓ (design complete)  
**PR:** https://github.com/dhk/tricorder/pull/new/feat/v2-cli-implementation (open when ready)

---

## Current state

**Design is complete.** v2 architecture is fully specified, reviewed across 4 rounds, and ready for implementation. PR #23 is open and ready to merge.

**v1 pipeline is still the shipped surface.** Nothing has changed in `tricorder/cli.py`. The design documents describe the target, not current behavior.

---

## What was done this session

### Documents written (all on feat/design-evolution-22)

| File | Purpose | Status |
|------|---------|--------|
| `BRIEF.md` | v2 product brief — migration doc (v1 current / v2 proposed) | Complete |
| `docs/EVOLUTION.md` | Narrative design history — v1 → v2 arc, key decisions | Complete |
| `DESIGN.md` | Technical design document — rewritten for v2 architecture | Complete |
| `docs/DESIGN-REVIEW.md` | Structured review log — 4 rounds, accept/reject reasoning | Complete |

### Review process

Four rounds of review between **Claude-author** (document author) and **Copilot-reviewer** (independent reviewer on a second machine). All findings resolved.

Key decisions made during review:
- `render` → `build` (final name)
- `learn` and `interpret` separated now, not deferred
- v1 commands **replaced**, not aliased — insufficient usage to maintain both
- Cutover definition: v2 is live when `discover`, `analyze`, `learn`, and `build` all work end-to-end on at least one repo
- Artifact storage fallback: prompt for folder location if `.tricorder/` not writable
- Lens validation requires 2 production repos + external domain reviewer + scoring thresholds
- `analytics-engineering` lens currently `Experimental` (strong evidence, 1 run) — moves to `Validated` after second production repo run

---

## v2 design summary

### Command surface (target — not yet implemented)

```
tricorder discover    OWNER/REPO [--lens NAME]
tricorder discover    OWNER/REPO --history
tricorder probe       OWNER/REPO
tricorder analyze     OWNER/REPO
tricorder learn       OWNER/REPO
tricorder interpret   OWNER/REPO [--lens NAME]
tricorder improve     OWNER/REPO
tricorder build       OWNER/REPO
tricorder demo
```

### Trust levels

| Level | Command | Credentials | Value |
|-------|---------|-------------|-------|
| 0 | `discover` | None | Repository profile + archetype |
| 1 | `discover --history` | None | Evolution timeline, hotspots |
| 2 | `analyze` | `GITHUB_TOKEN` | Review patterns, expertise map |
| 3 | `learn` | LLM API key | Organizational learnings |
| 4 | `interpret` | LLM API key | Domain-specific recommendations |
| 5 | `improve` | LLM API key | Improvement roadmap |

### Artifact store

`.tricorder/` in the repository being analyzed. Structured outputs at each level consumed by the next.

### Discipline lenses

| Lens | Status |
|------|--------|
| `analytics-engineering` | Experimental — strong evidence, 1 production run |
| `product-engineering` | Experimental — named, not designed |
| `platform-engineering` | Experimental — named, not designed |
| `security` | Experimental — named, not designed |

---

## v1 shipped surface (still current)

```
tricorder ready      OWNER/REPO
tricorder probe      OWNER/REPO
tricorder harvest    OWNER/REPO
tricorder synthesize OWNER/REPO
tricorder render     OWNER/REPO
tricorder demo
```

v1 DESIGN.md preserved at commit `95dfee7`: `git show 95dfee7:DESIGN.md`

---

## Open issues

| # | Title | Status |
|---|-------|--------|
| #22 | Update and evolve the design and product scope | Active — PR #23 ready to merge |
| #15 | Second repo run — validate generalizability | Open — needed to validate analytics-engineering lens |
| #16 | Trend detection across synthesis runs | Open |
| #18 | Switchable discipline lenses | Spec complete — implementation pending |

---

## File locations

| What | Where |
|------|-------|
| Repo | `/Users/dhk/Documents/dev/tricorder` |
| Cache | `~/.learn-from-work/cache/cal-itp__data-infra/` |
| Name map | `~/.tricorder/cal-itp__data-infra-name-map.json` |
| Skill | `~/.claude/skills/tricorder/SKILL.md` |
| Output report | `~/Documents/dev/adventures-in-ai/tricorder/2026-06-02-cal-itp__data-infra.md` |
| Explorer (local) | `/Users/dhk/Documents/dev/tricorder/explorer/index.html` |
| Explorer (live) | https://dhk.github.io/tricorder/explorer/ |

---

## How to continue

```
cd /Users/dhk/Documents/dev/tricorder
git checkout feat/v2-cli-implementation
git pull
```

**Next steps:**
1. Implement `tricorder discover` — Level 0, local filesystem only, no credentials, writes `.tricorder/repository-profile.yml` and `.tricorder/repository-fingerprint.json`
2. Implement `tricorder discover --history` — Level 1, local git history
3. Implement `tricorder analyze` (replaces `harvest`) — Level 2, GitHub read
4. Implement `tricorder learn` (replaces `synthesize`) + artifact contract — Level 3
5. Implement `tricorder interpret` — Level 4, lens application
6. Implement `tricorder improve` — Level 5
7. Implement `tricorder build` (replaces `render`)
8. Remove v1 commands (`ready`, `harvest`, `synthesize`, `render`)
9. Update README when v2 CLI is live
10. Run second synthesis on a new repo → move `analytics-engineering` from Experimental → Validated
