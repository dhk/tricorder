# Tricorder — Product Brief

**Version:** 2.0 (in design)  
**Status:** Specification — design decisions finalized, implementation pending  
**Supersedes:** v1.0.1.0 scope (dbt/SQL analytics repositories only)

---

## What tricorder is

Tricorder is a repository learning system.

It reads the evidence already present in a repository — code, git history, and review discussions — and progressively extracts organizational knowledge: what the team has learned, what it consistently misses, and where that knowledge can create the most leverage.

The core insight:

> Every recurring review comment is evidence that the organization is paying the same cost repeatedly.

Tricorder discovers those costs, identifies patterns, and recommends ways to move learning upstream — so that the same problems occur less frequently over time.

---

## What tricorder is not

**Not a code review tool.** Tricorder reads historical review data. It does not participate in live review, suggest inline comments, or evaluate individual PRs.

**Not a metrics dashboard.** Tricorder does not count PRs or measure review velocity. It answers: what is the team actually learning from review?

**Not a performance review tool.** Author profiles describe patterns in the feedback an author receives. This is material for a growth conversation, not an HR system.

**Not a GitHub Analytics competitor.** GitHub's analytics answer questions about activity. Tricorder answers questions about knowledge.

---

## The product thesis

Every repository contains evidence about:

- how software is built
- how software is reviewed
- what standards matter
- what mistakes recur
- where expertise resides
- where automation is missing

Most teams generate this knowledge continuously and then discard it.

Tricorder progressively extracts, structures, and operationalizes that knowledge.

---

## How trust works

Tricorder earns access incrementally.

Every increase in access must unlock a visibly better class of insight. Users should encounter something interesting before being asked to invest more.

The progression:

```
Local filesystem          →  Repository Profile
Local git history         →  Evolution Timeline
GitHub read access        →  Review Patterns
LLM analysis              →  Organizational Learnings
Lens interpretation       →  Recommendations
Full synthesis            →  Improvement Plan
```

At each stage, tricorder states clearly:

- what access it used
- what it did not access
- what it found
- what the next step is

---

## Trust levels

### Level 0 — Discovery

**Command:** `tricorder discover`  
**Access:** Local filesystem only. No network. No credentials.

Tricorder reads the repository to understand what it is.

**Output:**
- Repository Profile (archetype, confidence, evidence)
- Technology Fingerprint (languages, frameworks, tooling)
- Proposed discipline lens
- Initial observations

**Example findings:**
- dbt project detected
- SQL dominant
- GitHub Actions present
- SQL linting not found in CI
- Contributor count: 8

Artifacts written to `.tricorder/repository-profile.yml`, `.tricorder/repository-fingerprint.json`.

---

### Level 1 — Archaeology

**Command:** `tricorder discover --history`  
**Access:** Local git history only. No network.

Tricorder reads how the repository evolved.

**Output:**
- Contributor patterns and ownership signals
- Churn analysis and hotspot map
- Evolution timeline

Artifacts written to `.tricorder/contributors.json`, `.tricorder/hotspots.json`.

---

### Level 2 — Review Analysis

**Command:** `tricorder analyze`  
**Access:** GitHub read access (pull requests, review comments, commit metadata).

Tricorder reads how people discuss the repository.

**Output:**
- Review themes
- Reviewer expertise map
- Knowledge concentration
- Review coverage gaps

Artifacts written to `.tricorder/review-observations.json`, `.tricorder/review-patterns.json`, `.tricorder/expertise-map.json`.

---

### Level 3 — Learning Extraction

**Command:** `tricorder learn`  
**Access:** LLM API. Reads from Level 2 artifacts.

Tricorder identifies recurring lessons.

**Output:**
- Organizational knowledge map
- Hidden standards
- Recurring lessons
- Automation candidates
- Documentation candidates

Artifacts written to `.tricorder/learnings.json`, `.tricorder/standards-candidates.json`.

---

### Level 4 — Interpretation

**Command:** `tricorder interpret`  
**Access:** LLM API. Reads from Level 3 artifacts. Applies discipline lens.

Tricorder explains why discovered patterns matter, grounded in domain-specific authorities.

**Output:**
- Discipline-specific interpretation
- Maturity assessments
- Improvement opportunities
- Named standard citations

Artifacts written to `.tricorder/interpretations.json`.

---

### Level 5 — Improvement Planning

**Command:** `tricorder improve`  
**Access:** LLM API. Reads from all prior artifacts.

Tricorder produces a concrete roadmap.

**Output:**
- Prioritized improvement plan
- Tooling opportunities
- Process improvements
- Documentation opportunities
- Architecture improvements

Artifacts written to `.tricorder/improvement-plan.md`, `.tricorder/roadmap.json`.

---

## Discipline lenses

A lens provides the interpretive framework for Level 4.

Tricorder detects the likely lens from the repository fingerprint (Level 0) and proposes it. Users can select an alternative.

| Lens | Domain | Authorities |
|------|--------|-------------|
| `analytics-engineering` | dbt, SQL, BigQuery/Snowflake | dbt Labs, Kimball, SQLFluff, dbt-project-evaluator |
| `product-engineering` | Product software | Marty Cagan, Teresa Torres, Shape Up |
| `platform-engineering` | Infrastructure, SRE | Google SRE, DORA, AWS Well-Architected |
| `security` | Security engineering | OWASP, NIST, CIS |

The `analytics-engineering` lens is the validated lens — built from the v1 synthesis run on cal-itp/data-infra. Other lenses ship as the corresponding repo types are validated.

---

## The artifact contract

Every level writes structured artifacts. Every subsequent level reads them.

```
repository-profile.yml
    ↓
contributors.json + hotspots.json
    ↓
review-patterns.json + expertise-map.json
    ↓
learnings.json + standards-candidates.json
    ↓
interpretations.json
    ↓
improvement-plan.md + roadmap.json
```

Artifacts are first-class outputs, not implementation details. They are:
- Human-readable (YAML/JSON/Markdown)
- Written to `.tricorder/` in the repository being analyzed (or a configured cache location)
- Reusable by external tools, MCP servers, and AI agents without rerunning analysis

---

## Artifact storage

Default: `.tricorder/` inside the repository being analyzed when tricorder is run from that repository.

Configurable via `~/.learn-from-work/config`. Follows XDG conventions for fallback.

The storage location is recorded in `.tricorder/config.yml` so all subsequent commands resolve to the same place.

---

## Status blocks

Every command ends with a status block.

```
Tricorder — Review Analysis

Access used
  ✓ Pull requests (read)
  ✓ Review comments (read)
  ✓ Commit metadata (read)

  No write operations performed.
  Repository contents remain local.

Completed
  ✓ Repository Profile
  ✓ Technology Fingerprint
  ✓ Contributor Patterns
  ✓ Review Patterns

Not yet unlocked
  ○ Organizational Learnings   →  tricorder learn
  ○ Interpretation             →  tricorder interpret
  ○ Improvement Planning       →  tricorder improve

Next
  tricorder learn
```

Users should never wonder: what happened, what was analyzed, what access was used, what remains, or what to do next.

---

## The maturity path

Every pattern is tagged with a maturity level. This is the action signal.

| Level | Meaning | What to do |
|-------|---------|------------|
| `judgment` | Too context-dependent to codify | Document the heuristic |
| `guidance` | Ready for a team norm | Write it down |
| `convention` | Ready for a PR template | Add to checklist |
| `rule` | Ready for automated enforcement | SQLFluff, dbt-project-evaluator |
| `deterministic` | Ready for a CI gate | Block merges that violate it |

Promotion is a human decision. Tricorder identifies where patterns sit and what the next step is.

---

## Who this is for

**Primary users:**
- Engineering leads and team leads who want evidence for growth conversations and coverage gap identification
- Platform or tooling engineers deciding what should move from convention to automated enforcement
- Individual contributors building a picture of what their team actually values

**Repository requirements:**
- Active PR review practice on GitHub
- 30+ merged PRs in the target window
- Some inline comment activity (use `tricorder discover` to assess before investing)

---

## Future: MCP integration

Artifacts will be exposed as MCP resources.

```
mcp://repository/profile
mcp://repository/review-patterns
mcp://repository/learnings
mcp://repository/recommendations
mcp://repository/roadmap
```

External agents will be able to consume repository knowledge without rerunning analysis. This makes tricorder a knowledge foundation, not just a reporting tool.

---

## What's not planned

- A hosted service or SaaS version
- GitHub App or webhook-based automation
- Real-time review assistance
- Performance evaluation or HR reporting
