# Using Tricorder to strengthen an impact case

Tricorder turns git history and code-review discussion into an inspectable map of standards,
expertise, review behavior and team gaps. For an impact case it fills the weakest spot: the
quality and influence of review work, which raw counts flatten. Install and credentials:
[HOWTO.md](../../../HOWTO.md).

Tell the person to run the steps one at a time and inspect `.tricorder/` after each (never
commit that directory):

| Step | Command | Access | What it adds to the case |
|---|---|---|---|
| 1 | `tricorder discover --history` | local only | Contributors, hotspots, timeline: evidence of **ownership** of the areas they claim |
| 2 | `tricorder analyze OWNER/REPO --since <window start>` | GitHub read token | Review observations, patterns, and an **expertise map**: whether others' code in an area gets reviewed by them |
| 3 | `tricorder learn OWNER/REPO --dry-run`, then without `--dry-run`, `--visibility private` | LLM provider key | **Reviewer fingerprint** and **author growth profile**, plus **oversight density**: the share of their approvals that carried comments vs. silent approvals |
| 4 | `tricorder build OWNER/REPO --open` | local | Explorer at `localhost:7372` to locate and screenshot specific evidence |

## How to use what it produces

- **Pointers, not verdicts.** Follow each finding to the PR or comment it came from and cite
  that. Tricorder's lenses and generated judgments are experimental and require human review;
  its LLM-written text is Inferred at best and never goes into the document as fact.
- **Strongest uses:**
  - sustained ownership (hotspots, timeline);
  - raising the standard in review: patterns they repeatedly enforce that later became a
    convention, checklist item or lint rule (Tricorder's maturity ladder
    `judgment → guidance → convention → rule → deterministic` makes this visible);
  - substantive review (low silent-approval share);
  - growth across the window (author profile).
- **Privacy first.** `analyze` reads private review history. `learn` sends PR text, review
  comments and GitHub identities — colleagues' included — to the configured LLM provider, and
  `--visibility private` output names them. Before running `learn` on an employer repository,
  confirm the employer's policy and the provider's retention terms allow it. Never share the
  named artifacts; quote only the person's own contributions in the final document. See
  [PRIVACY.md](../../../docs/PRIVACY.md).
