# tricorder equip — Design Document

> *"The tricorder tells you what's wrong with the away team. The replicator is in the next room."*

**Version:** 1.0
**Status:** Design — agreed in interview 2026-07-05/06, ready for review
**Parent design:** [DESIGN.md](../DESIGN.md) (v2 six-level architecture)
**Repo:** [dhk/tricorder](https://github.com/dhk/tricorder)

This document specifies **Level 6: `tricorder equip`** — the stage that turns
tricorder from an audit tool into a process improvement tool. Everything below
extends DESIGN.md; nothing here changes Levels 0–5 except the two schema
amendments called out in [§6](#6-schema-amendments-to-levels-3-5).

---

## 1. Thesis

Tricorder today ends with a diagnosis. Level 5 (`improve`) produces a roadmap
that says *"this recurring review pattern is costing you; here is what to
change."* Then a human reads a Markdown file and, in practice, nothing happens.

The last mile is missing: **the repo itself never gets better tools.**

Equip closes that mile for one lane first — **agent skills** — because skills
are the one repo support tool that:

1. can be generated from review evidence with high fidelity (the evidence *is*
   the checklist),
2. has an existing authoring discipline (Anthropic's `skill-creator`) and an
   existing quality bar (skill-map's `skill-doctor`), and
3. compounds: a skill installed in `.claude/skills/` changes every future
   AI-assisted authoring and review session in that repo.

The other lanes — CI gates, lint rules, PR templates, CLAUDE.md amendments,
hooks — are real and are named in [§10](#10-future-lanes), but v1 designs the
skill lane end-to-end rather than all lanes shallowly.

**The loop this creates:**

```
review history → evidence → proposal → skill installed → future PRs → review history
                     ▲                                          │
                     └────────── effectiveness audit ◄──────────┘
```

The feedback edge (effectiveness audit) is what makes this *process
improvement* rather than *artifact generation*: a proposed skill ships with a
falsifiable claim, and a later tricorder run checks whether the claim held.

---

## 2. What equip is / is not

**Equip is** the pipeline stage that: triages Level 3–5 findings into
skill-shaped proposals with cited evidence; checks each proposal against the
skill-map corpus (adopt vs create); walks the human through each proposal in an
interactive Claude Code session; authors accepted skills via `skill-creator`;
hardens them via `skill-doctor`; delivers them as a PR into the target repo's
`.claude/skills/`; and records every decision in a ledger so effectiveness can
be measured later.

**Equip is not:**

- **Not autonomous.** No skill is authored, let alone PR'd, without a human
  accepting the specific proposal in-session. The current `improve --forge`
  behavior (silently generating and PRing a batch of skills) is retired — see
  [§9](#9-disposition-of-improve---forge).
- **Not a skill generator with a repo attached.** A proposal that cannot cite
  specific past PRs it would have prevented does not reach the session at the
  "strong" tier. Evidence first, generation second.
- **Not a second opinion on skill quality.** Equip does not carry its own
  rubric. `skill-doctor` is the single place a skill gets judged; equip
  composes it.

---

## 3. Position in the architecture

### 3.1 The seventh level

```
discover → discover --history → analyze → learn → interpret → improve → equip
                                                                            ↓
                                                              .tricorder/proposals.json
                                                              .tricorder/equip-ledger.json
                                                              PR into target repo
```

### 3.2 Trust ratchet extension

Equip adds one row to the DESIGN.md access contract. It is the first level
that **writes outside `.tricorder/`**, which is exactly why it is the last
level and why the human gate is structural, not optional:

| Level | Command | Data sources | Network | Credentials | Writes | Failure behavior |
|---|---|---|---|---|---|---|
| 6 | `equip` | Level 3–5 artifacts + skill-map corpus-index | Yes (corpus fetch; GitHub write for delivery) | `GITHUB_TOKEN` or `gh` auth with PR scope | `.tricorder/proposals.json`, `.tricorder/equip-ledger.json`; branch + PR in target repo (only after in-session acceptance) | If corpus-index is unreachable, fail with actionable error (corpus is a v1 prerequisite, §7.1). If gh lacks write access, complete the session and emit skills to a local directory with manual-PR instructions. |

### 3.3 `make-it-so` integration

`make-it-so` gains an `L6` entry with `requires: ["llm_key", "L5",
"gh_write"]`. Because equip's session phase is interactive, `make-it-so` runs
only equip's deterministic **propose** step (§5.1) and ends with:

```
L6  Equip Proposals    ✓  4 proposals (2 strong, 2 emerging)
    Next: run the equip session in Claude Code — say "tricorder equip session"
```

### 3.4 Two runtimes, one stage

Equip deliberately splits across the CLI and the Claude Code skill:

| Phase | Runtime | Why |
|---|---|---|
| **propose** | CLI (`tricorder equip`) | Deterministic triage; reproducible artifact; no judgment calls |
| **session** | Claude Code (tricorder skill) | Judgment, conversation, `skill-creator` + `skill-doctor` composition, AskUserQuestion |
| **deliver** | CLI plumbing invoked from session | Reuses forge's proven branch/PR mechanics |

A nice property falls out: the expensive judgment work (matching refinement,
skill authoring, doctoring) runs on the Claude Code session model at zero
marginal API cost. The CLI's LLM key is not used by equip at all in v1.

---

## 4. The tool composition

Three tools, three owners, no overlap:

| Tool | Lives in | Role in equip | Status |
|---|---|---|---|
| `tricorder equip` | this repo | Evidence, triage, proposals, session orchestration, delivery, ledger | to build |
| `skill-creator` | Anthropic plugin (installed) | Authoring discipline: structure, description optimization, evals | exists |
| `skill-doctor` | [dhk/skill-map](https://github.com/dhk/skill-map) plugin | Quality gate: 5-axis rubric (frontmatter / triggering / disclosure / structure / safety) | exists (v1.0.0) |
| corpus-index | dhk/skill-map (new export) | Adopt-vs-create triage data | **prerequisite, to build** (§7.1) |
| doctor evidence mode | dhk/skill-map (extension) | Effectiveness audit input | parallel workstream (§7.2) |

Division-of-labor rule: **tricorder owns evidence, skill-map owns judgment
about skills, skill-creator owns authoring.** When equip needs to know "is
this SKILL.md good," it invokes skill-doctor; it never grows its own opinion.

---

## 5. The equip pipeline

### 5.1 Propose (deterministic, CLI)

`tricorder equip OWNER/REPO` reads `learnings.json`, `standards-candidates.json`,
`interpretations.json`, and `roadmap.json`, plus the repo-context captured at
Level 2 (CI-enforced rules — `.sqlfluff`, lint configs — and any existing
`.claude/skills/` in the target repo), and emits `proposals.json`.

**Evidence gate — tiered, never silently filtering.** Every skill-shaped
finding becomes a proposal; the gate assigns a tier rather than dropping
candidates (interview decision: conviction levels are shown, not hidden).

| Tier | Criteria (all must hold) | Session treatment |
|---|---|---|
| **strong** | ≥3 occurrences · ≥2 distinct authors · occurred within last 90 days · not already CI-enforced · ≥2 citable counterfactual PRs | Presented first, with full evidence dossier |
| **emerging** | ≥2 occurrences · within last 180 days · not CI-enforced | Presented after strong, flagged as emerging |
| **watch** | everything else skill-shaped | Listed in proposals.json, not presented in-session; visible with `--all` |

All thresholds live in `.tricorder/config.yml` under `equip.gates` and the doc
of record for *why each default* is this section:

- **≥3 occurrences / ≥2 authors** — one person's habit is coaching material,
  not tooling material. Two authors making the same mistake means the *repo*
  lacks the guardrail.
- **90-day recency** — a pattern that stopped recurring was fixed by something
  else; proposing a skill for it burns credibility.
- **not CI-enforced** — Level 2 already captures lint/CI config precisely so
  recommendations don't duplicate existing gates (DESIGN.md, Level 2).
- **≥2 counterfactual PRs** — the "strong enough opinion" test. A strong
  proposal must name real merged PRs where a reviewer spent a round-trip on
  exactly this pattern, i.e., PRs the skill would plausibly have prevented.

**Coverage diagnosis.** Each proposal is triaged against two corpora:

1. **The target repo's own skills** (`.claude/skills/` scanned at Level 2):
   if an installed skill already targets this pattern, the proposal becomes an
   *effectiveness question* (the skill exists but the pattern still recurs —
   route to doctor evidence mode, §7.2) instead of a creation proposal.
2. **The skill-map corpus-index** (§7.1): deterministic tag/keyword matching
   in v1 produces `adopt_candidates` — corpus skills whose tags and
   description overlap the pattern. Semantic refinement of these matches
   happens in-session where a human confirms; the CLI never auto-decides
   "adopt."

**Adopt gate (interview decision):** only corpus skills with quality grade
A/B *and* source tier `canonical` or `curated` may appear as adopt
candidates. Everything else in the corpus is **prior art** — cited in the
authoring context to inform a fresh skill, never recommended for installation.

**`proposals.json` schema:**

```json
{
  "generated_at": "…",
  "tricorder_level": 6,
  "source_repo": "OWNER/REPO",
  "gates": { "strong": {"min_occurrences": 3, "min_authors": 2, "recency_days": 90, "min_counterfactual_prs": 2},
             "emerging": {"min_occurrences": 2, "recency_days": 180} },
  "proposals": [
    {
      "id": "EQ-001",
      "tier": "strong",
      "pattern_signal": "User-supplied configuration takes precedence over inferred defaults",
      "category": "skill",
      "occurrences": 5,
      "distinct_authors": 3,
      "last_seen": "2026-06-28",
      "ci_enforced": false,
      "counterfactual_prs": [
        {"pr": 142, "url": "…", "review_cost": "2 CHANGES_REQUESTED rounds",
         "evidence_quote": "explicit override should win here — same issue as last time"}
      ],
      "coverage": {
        "installed_skill": null,
        "adopt_candidates": [
          {"corpus_id": "anthropics/…", "grade": "A", "tier": "canonical", "match_basis": ["tags:transform", "kw:config precedence"]}
        ],
        "prior_art": ["…corpus ids…"]
      },
      "skill_sketch": {
        "name": "config-precedence-check",
        "description_draft": "…",
        "trigger_context": "authoring or reviewing code that infers defaults",
        "success_metric": "occurrences of this pattern per 30 merged PRs drops below 1 within 90 days of install"
      }
    }
  ]
}
```

Every proposal carries a **falsifiable `success_metric`** at birth. This is
what the ledger (§5.4) and the effectiveness audit (§7.2) later check.

### 5.2 Session (interactive, Claude Code)

The tricorder Claude Code skill gains an equip mode ("tricorder equip
session", "equip the repo", "propose skills"). Flow per proposal, strong tier
first:

1. **Present the dossier** — pattern, tier, occurrence counts, the
   counterfactual PRs with quotes, cost framing, and the coverage verdict
   (create / adopt candidate / effectiveness question).
2. **Decision via AskUserQuestion** — `accept-create` / `accept-adopt <candidate>`
   / `edit` (reshape scope, rename, merge with another proposal) / `reject`
   (with reason, recorded) / `defer`.
3. **Author** — for `accept-create`: invoke **skill-creator** with the full
   evidence dossier as authoring context (the counterfactual quotes become the
   skill's examples; the pattern's comment evidence becomes the checklist).
   For `accept-adopt`: fetch the corpus skill by pinned `body_sha`, adapt
   frontmatter/paths to the target repo, preserve upstream attribution and
   license.
4. **Doctor** — invoke **skill-doctor** on the authored/adapted SKILL.md.
   Doctor's interview questions (tool scoping, data sensitivity, high-stakes
   surface) are answered in the same session. A skill that doctor grades below
   B does not proceed; equip-generated skills must pass the bar every other
   skill is held to — no self-exemption.
5. **Stage** — write to a local staging dir with a `WIRING.md` declaring
   provenance (source analysis run, proposal id, evidence PRs) per skill-map's
   WIRING spec.

Format corrections locked in (fixing forge's mistakes): generated skills use
the **real** Claude Code frontmatter (`name`, `description` with embedded
triggers *and anti-trigger*, `license`) — not forge's invented `triggers:`
list — and install to **`.claude/skills/<name>/`** in the target repo, not a
root-level `skills/` directory.

### 5.3 Deliver (CLI plumbing)

Reused from forge, with the batch inverted: only session-accepted skills are
delivered. One branch (`feat/tricorder-equip-YYYY-MM-DD`), one PR whose body
is the evidence dossier per skill (counterfactual PRs linked — the PR argues
for itself), one tracking issue (soft-fail). If `gh` lacks write access to the
target repo, emit the staged skills locally with manual instructions instead
of failing the session.

### 5.4 Ledger

`.tricorder/equip-ledger.json` — append-only record of every proposal's fate:

```json
{
  "proposal_id": "EQ-001",
  "decision": "accept-create | accept-adopt | reject | defer",
  "decision_reason": "…",
  "decided_at": "…",
  "skill_name": "config-precedence-check",
  "delivered_pr": "https://github.com/OWNER/REPO/pull/…",
  "installed_at": null,
  "success_metric": "…",
  "baseline": {"occurrences_per_30_prs": 2.1, "window": "2026-03-01..2026-06-28"}
}
```

The ledger is what makes the loop closeable: a future `analyze`+`learn` run
computes the same recurrence measure post-install, and doctor evidence mode
(§7.2) renders the verdict. Rejected proposals matter too — a pattern rejected
with reason "we're deprecating that subsystem" should not be re-proposed next
run.

---

## 6. Schema amendments to Levels 3–5

Two small, backfillable changes equip depends on:

1. **Pattern → PR linkage (Level 3).** `learnings.json` patterns currently
   carry `comment_evidence` quotes but no PR identifiers, which makes the
   counterfactual gate impossible. Amend per-PR extraction to record
   `occurrences: [{pr_number, pr_url, merged_at, comment_evidence: […]}]` per
   pattern instead of flat quote lists. Backfill is possible from the cached
   per-PR extraction results without re-calling the LLM.
2. **Installed-skill scan (Level 2).** `analyze` additionally records the
   target repo's `.claude/skills/*/SKILL.md` (names + descriptions) in
   `repo-context.json`, alongside the existing CI-config capture. Needed for
   coverage diagnosis and for re-proposal suppression.

---

## 7. Cross-repo contracts (skill-map)

### 7.1 Corpus-index export — **prerequisite for equip v1**

Interview decision: adopt-vs-create triage is the heart of the feature; equip
does not ship without it.

Skill-map publishes `dist/corpus-index.json` (regenerated by the crawl
pipeline), one entry per deduplicated skill:

```json
{
  "id": "anthropics/skills:algorithmic-art",
  "name": "algorithmic-art",
  "description": "…full description string…",
  "source_repo": "anthropics/skills",
  "source_tier": "canonical | curated | community",
  "quality_grade": "A", "quality_score": 91.5,
  "tags": {"action": "transform", "complexity": "intermediate", "output_type": "media", "integration": "standalone"},
  "domain": "Media & Creative",
  "license": "MIT",
  "raw_url": "…", "body_sha": "…",
  "dedup": {"concept_cluster": "…", "is_canonical_instance": true}
}
```

Source-tier assignment is skill-map's call (it has the lineage and originator
data); the working definition: `canonical` = anthropics + official plugins;
`curated` = named originators with maintained repos; `community` = the rest,
including the mega template-dumps. Tricorder fetches the index with a cached
TTL and records the index version in `proposals.json` for reproducibility.

All the ingredients exist in skill-map today (`skill_quality.json`,
`skill_tags.json`, `skill_clusters.json`, crawl `data.json` with full bodies);
this is an export/consolidation task, not new research.

### 7.2 skill-doctor evidence mode — parallel workstream

Doctor gains an optional evidence input: a file tricorder produces comparing a
skill's `success_metric` baseline against post-install recurrence:

```json
{
  "skill": "config-precedence-check",
  "claim": "occurrences per 30 merged PRs < 1 within 90 days of install",
  "baseline": {"rate": 2.1, "window": "…"},
  "observed": {"rate": 0.4, "window": "…", "n_prs": 47},
  "verdict_input": "improving"
}
```

With evidence present, doctor's report adds an **Effectiveness** section
(working / not-working / insufficient-data) alongside its five static axes.
Without it, doctor runs exactly as today. Degrades gracefully; does not block
equip v1 — the ledger accumulates the data the mode will eventually consume.

### 7.3 Contract discipline

This document is the source of truth for both contracts until skill-map
implements them, at which point skill-map's schemas win and this doc links out.

---

## 8. Dogfood plan

Interview decision: both targets, in order.

1. **tricorder on tricorder.** `.tricorder/` artifacts already exist from a
   self-run. Shakes out the mechanics end-to-end (gate → session →
   skill-creator → skill-doctor → PR into this repo). Known weakness: a
   mostly-solo repo has thin multi-author recurrence, so expect mostly
   emerging-tier proposals — that itself validates the tiering display.
2. **cal-itp/data-infra.** Already harvested; real team, real dbt review
   history, matches the analytics-engineering lens (the one lens with strong
   v1 evidence per DESIGN.md). Deliverable is an *outreach artifact*: the
   proposals dossier + generated skills as a draft PR or shared doc — a
   credibility demo for the Substack narrative, not an imposition on a team
   we're not part of.

Success criteria for calling the design validated:
- A strong-tier proposal exists whose counterfactual PRs a human reads and
  says "yes, that skill would have caught this."
- A generated skill passes skill-doctor at grade B+ without manual rework.
- The full session for 4–6 proposals completes in under 30 minutes.

---

## 9. Disposition of `improve --forge`

Forge ([skills_forge.py](../tricorder/commands/skills_forge.py)) proved the
delivery plumbing and is otherwise superseded:

| Forge piece | Fate |
|---|---|
| Branch / commit / PR / tracking-issue mechanics | **Kept** — moves under equip deliver (§5.3) |
| One-shot LLM skill generation (`SYSTEM_SKILL` prompt) | **Retired** — replaced by skill-creator in-session |
| Invented SKILL.md schema (`triggers:` list, `inputs:`, `outputs:`) | **Retired** — real frontmatter format (§5.2) |
| Root-level `skills/` install location | **Retired** — `.claude/skills/` |
| Batch-without-human-gate flow | **Retired** — per-proposal acceptance is structural |
| `improve --forge` flag | **Deprecated** — prints a pointer to `tricorder equip` for one release, then removed |

`roadmap.json`'s `skill_implementable` flags remain as the hand-off surface
between improve and equip's propose step.

---

## 10. Future lanes

Named, not designed. Each follows the same shape — evidence gate → proposal →
human session → delivery — with a different artifact type:

- **ci-gate** — patterns at `rule` maturity with mechanical checks
  (`standards-candidates.json` already suggests SQLFluff/ESLint encodings)
  become proposed lint-config diffs.
- **pr-template** — checklist-category gaps become PR template checkbox
  proposals.
- **claude-md** — convention-category patterns become proposed CLAUDE.md
  amendments (the cheapest lane: no trigger problem, always in context).
- **hooks** — deterministic pre-commit/pre-push checks for patterns that
  graduate beyond skill maturity.

The maturity path from DESIGN.md applies across lanes: a pattern may enter as
a skill (judgment-assist) and graduate to a CI gate (deterministic) once the
team validates it — equip's ledger records the graduation candidates.

---

## 11. Risks and open questions

- **Thin-history repos** produce only emerging/watch tiers; the session must
  frame this honestly ("not enough recurrence to be confident") rather than
  padding. First impressions decide whether equip is trusted.
- **skill-creator is an external dependency** — Anthropic's plugin can change
  under us. Mitigation: equip passes it a self-contained authoring brief, so
  a fallback path (author directly in-session against skill-doctor's rubric)
  exists if the plugin regresses.
- **Adopt-candidate licensing** — corpus skills carry licenses; the adopt path
  must preserve them and refuse license-incompatible adoption. Corpus-index
  carries `license` for this; enforcement lives in the session step.
- **Counterfactual honesty** — "this skill would have prevented PR #142's
  review round-trip" is a plausibility claim, not a proof. The dossier
  language must say *plausibly prevented*; overselling here is the fastest way
  to lose the audience the whole tool depends on.
- **Open:** should rejected-with-reason proposals expire (re-proposed after N
  months if still recurring) or be permanent? Leaning: expire after 2× the
  recency window, because "we're deprecating that" sometimes isn't true.
- **Open:** explorer integration — proposals and ledger as an explorer tab.
  Deferred; the explorer is an audit surface today and equip's surface is the
  session.

---

## 12. Workstreams and sequencing

| # | Workstream | Repo | Blocking? |
|---|---|---|---|
| 1 | Corpus-index export (§7.1) | skill-map | **Blocks equip v1** |
| 2 | Level 3 pattern→PR linkage + Level 2 installed-skill scan (§6) | tricorder | Blocks propose |
| 3 | `equip` propose command + gates + proposals.json | tricorder | — |
| 4 | Tricorder skill equip-session mode (skill-creator + skill-doctor composition) | tricorder (+ ~/.claude/skills/tricorder) | Needs 3 |
| 5 | Deliver plumbing lift from forge + ledger | tricorder | Needs 4 |
| 6 | Dogfood 1 (self-run), then dogfood 2 (cal-itp) | — | Needs 1–5 |
| 7 | skill-doctor evidence mode (§7.2) | skill-map | Post-v1; needs ledger data to exist |
| 8 | Future lanes (§10) | tricorder | Post-v1 |

Sequencing note: workstream 1 and 2–3 can run in parallel; the propose step
should stub the corpus fetch behind an interface so tricorder-side work isn't
serialized on skill-map.
