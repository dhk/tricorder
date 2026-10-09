# Using Tricorder to strengthen an impact case

Tricorder turns git history and code-review discussion into an inspectable map of standards,
expertise, review behavior and team gaps. For an impact case it fills the weakest spot: the
quality and influence of review work, which raw counts flatten. Install and credentials:
[HOWTO.md](../../../HOWTO.md).

Tell the person to run the steps one at a time and inspect `.tricorder/` after each (never
commit that directory):

Lead with the no-key path. Most people have no Anthropic or Gemini API key, and they don't
need one: you are already the LLM.

**Without an API key**

| Step | Command | Access | What it adds to the case |
|---|---|---|---|
| 1 | `tricorder discover --history` | local only | Contributors, hotspots, timeline: evidence of **ownership** of the areas they claim |
| 2 | `tricorder analyze OWNER/REPO --since <window start>` | GitHub sign-in or token | Review observations, an **expertise map**, and a local cache of every review and inline comment, under `.tricorder/OWNER__REPO/.raw/reviews/` and `.raw/comments/` |

After step 2, offer to read `expertise-map.json` and the person's own entries in the `.raw/`
review and comment caches yourself, then characterize their reviewing: areas, recurring
asks, share of approvals with comments. Cite each point to a PR. Ignore other people's
comments except as context; never quote or characterize colleagues.

**With an API key (optional)**

| Step | Command | Access | What it adds |
|---|---|---|---|
| 3 | `tricorder learn OWNER/REPO --dry-run`, then without `--dry-run`, `--visibility private` | Anthropic or Gemini key | **Reviewer fingerprint**, **author growth profile**, and the computed **oversight density** table |
| 4 | `tricorder build OWNER/REPO --open` | needs step 3's `learnings.json` | Explorer at `localhost:7372` for browsing and screenshots |

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
