# tricorder — Live Demo Guide

4-minute scripted walkthrough for technical audiences (analytics engineers, data team leads).

Real data from cal-itp/data-infra (June 2026). Contributor names anonymized with Star Trek character names. No API spend during the demo.

---

## Setup

```bash
# Clone or pull the repo on any machine with Python 3.9+
git clone https://github.com/dhk/tricorder.git
cd tricorder

# No dependencies beyond stdlib — runs anywhere
python tricorder-demo.py
```

**Flags:**
```bash
python tricorder-demo.py              # full demo — typewriter pacing, 4 pauses
python tricorder-demo.py --fast       # no delays, pauses still fire (dry-run)
python tricorder-demo.py --no-pause   # straight through, no input() stops
```

**Before you present:** run `--fast` once to confirm it works on your machine. Takes ~15 seconds.

---

## Naming note (say this upfront, 10 seconds)

> "Names in the demo are Star Trek character aliases — this is a real team's real data, anonymized."

If someone asks: the real→alias mapping is at `~/.tricorder/cal-itp__data-infra-name-map.json`, not committed to the repo.

---

## Demo flow and narration (4 minutes)

### Scene 1 — Header (~15 sec, no pause)

The script prints the repo, contributor count, and date window. Let it run.

---

### Scene 2 — Harvest scroll (~40 sec)

172 PRs scroll past with PR number, Trek alias, and title. The first 5 and last 3 are slightly slower.

**PAUSE 1** — after harvest summary prints:

> "172 PRs, 90 days of review threads. Every inline comment, every formal review, all the back-and-forth before each merge — pulled from the GitHub API and written to a local cache. About 4MB of JSON. Zero API spend. The cache is permanent and incremental: re-harvest only fetches PRs newer than the last run. Now we synthesize."

---

### Scene 3 — Phase 1: Per-PR extraction (~75 sec)

The script shows the system prompt Claude receives, then processes three PRs slowly to establish the pattern, then shows the full extraction JSON for **PR #5220** (`fct_tides_trips_performed` by Data, reviewed by Spock).

The JSON has 4 patterns: grain scoping, incremental strategy, modeling boundary, dbt exposures — each with a direct quote from the review thread and a maturity tag.

**PAUSE 2** — after PR #5220 JSON prints, before the fast-scroll continues:

> "That's what Claude sees: the PR description, the diff file paths, every review comment thread in sequence. And what it returns: structured JSON. Notice the `comment_evidence` field — those are direct quotes, not summaries.
>
> The `maturity` tag is the action signal. `rule` means this is ready for CI enforcement — add a dbt-project-evaluator check and block the merge. `convention` means add it to the PR template. `judgment` means document the heuristic.
>
> 154 of these calls ran. Total Phase 1 time on the real run: about 25 minutes."

---

### Scene 4 — Phase 2: Reviewer fingerprints (~45 sec)

14 reviewers listed with signal quality. Then Spock's full fingerprint prints — 40 PRs reviewed, 5 focus areas, 2 blind spots.

**PAUSE 3** — after Spock's fingerprint prints:

> "40 PRs distilled into that. Spock is the team's only high-signal reviewer — thorough, blocking, focused on incremental strategy and dedup correctness.
>
> But look at the blind spots: no test coverage comments across 40 PRs. Not once. Across multiple new mart models introduced in that window.
>
> Now look at the rest of the reviewer list: 11 low-signal reviewers. Most of them are approving breaking SQL changes with a single line and no inline technical scrutiny.
>
> One expert reviewer, 13 LGTM-stampers. That's not a knowledge problem. That's a process problem."

---

### Scene 5 — Phase 3: Author growth profiles (~20 sec, no pause)

15 authors listed with trajectory. Runs fast. Let it go — the numbers speak for themselves: 8 improving, 4 stable, 3 insufficient-data.

---

### Scene 6 — Phase 4: Team gap analysis (~30 sec)

One aggregate call. The top 3 of 11 gaps print as JSON: one `coverage_gap`, one `blind_spot`, one `knowledge_gap`.

**PAUSE 4** — after the gaps JSON prints:

> "11 gaps. Three types.
>
> Coverage gap: nobody is checking it. Not because reviewers don't know it matters — because nobody was ever assigned to own it.
>
> Blind spot: the team doesn't know it's a gap. Source freshness checks, SQL style enforcement — these never come up in review because no reviewer has them on their checklist.
>
> Knowledge gap: they know it matters but have no shared process. 'Merge and watch' is normalized. There's no PR template field for rollback procedure.
>
> The fix for the top finding — LGTM approvals on breaking SQL changes — is a PR checklist template, not a training session. Two hours of work, not a workshop."

---

### Scene 7 — Report (~20 sec, no pause)

Report sections tick off, output path prints, final summary shows cost and links.

Point the audience at:
- **Explorer:** https://dhk.github.io/tricorder/explorer/
- **Full report:** https://github.com/dhk/adventures-in-ai/blob/main/tricorder/2026-06-02-cal-itp__data-infra.md

---

## Timing reference

| Scene | What's happening | Wall time |
|-------|-----------------|-----------|
| Header | Intro text | 0:00 |
| Harvest | 172 PRs scroll | 0:15 |
| **Pause 1** | Narrate cache / cost | 0:55 |
| Phase 1 prompt | System prompt prints | 1:25 |
| Phase 1 demo PR | PR #5220 JSON | 1:40 |
| **Pause 2** | Narrate extraction / maturity | 2:05 |
| Phase 1 fast-scroll | Remaining PRs | 2:50 |
| Phase 2 fingerprints | 14 reviewers + Spock | 3:05 |
| **Pause 3** | Narrate coverage gap | 3:30 |
| Phase 3 authors | 15 author trajectories | 4:05 |
| Phase 4 gaps | Team gap JSON | 4:25 |
| **Pause 4** | Narrate gap types / fix | 4:40 |
| Report | Summary + links | 5:20 |
| Done | | 5:40 |

With narration held tight, the full run is 5–6 minutes. For a hard 4-minute slot, drop Pause 3 and say the reviewer coverage point as an aside while Phase 3 is printing.

---

## Likely questions and answers

**"Why Star Trek names?"**
Real team, real data, public repo. The names are the only thing that would identify individuals to someone in this room who knows them. The quotes, the PR numbers, the patterns — all real.

**"Can I run this against my own team's repo?"**
Yes. `tricorder harvest OWNER/REPO --since YYYY-MM-DD` then `tricorder synthesize OWNER/REPO`. You need a GitHub PAT and an Anthropic API key. Run `tricorder-cost-probe.py OWNER/REPO --limit 20` first to see what a full run would cost. Roughly $0.015 per PR.

**"How long does the real synthesis take?"**
The cal-itp run was 154 PRs and took about 28 minutes. Phase 1 (per-PR) runs sequentially; phases 2–4 are fast aggregate calls.

**"What if our team doesn't use dbt?"**
The category taxonomy and standard citations are calibrated for dbt/SQL analytics repos. It'll run against anything on GitHub, but the findings will be less specific — Kimball and SQLFluff citations won't map. Python data pipelines and infrastructure-as-code are on the roadmap.

**"Is this open source?"**
Public repo: github.com/dhk/tricorder. MIT. Early and experimental.

---

## Files

| File | What it is |
|------|-----------|
| `tricorder-demo.py` | The demo script — run this |
| `DEMO.md` | This file |
| `tricorder-synthesize.py` | The real synthesis script |
| `tricorder-cost-probe.py` | Token/cost estimator — run before any real synthesis |
| `explorer/` | Interactive HTML explorer (live at dhk.github.io/tricorder/explorer/) |
| `DESIGN.md` | Full design document |
| `SKILL.md` | Technical specification |
