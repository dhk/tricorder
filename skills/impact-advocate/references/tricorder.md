# Using Tricorder to strengthen an impact case

Tricorder turns git history and code-review discussion into an inspectable map of ownership,
expertise and review behavior. For an impact case it fills the weakest spot: the quality and
influence of review work, which raw counts flatten.

It's optional. Offer it once, after the document is written, and only if it would address a
"Not visible" or thin rating. Name which ones.

**Install (one command, with the person's OK).** Check first with `tricorder --version`. If
it's missing, offer one of these, whichever tool they have (`command -v pipx uv`):

```bash
pipx install git+https://github.com/dhk/tricorder.git
uv tool install git+https://github.com/dhk/tricorder.git
```

Either puts `tricorder` on the PATH in its own environment, leaving system Python alone.
Undo with `pipx uninstall tricorder` or `uv tool uninstall tricorder`. Before the first
command, add `.tricorder/` to the repository's local ignore list
(`echo ".tricorder/" >> .git/info/exclude`): its files can name colleagues.

For a personal packet, use only the two commands below. Neither needs an API key; you are
already the LLM. Tell the person to run them one at a time from inside the repository and
inspect `.tricorder/` after each (never commit that directory):

| Step | Command | Access | What it adds to the case |
|---|---|---|---|
| 1 | `tricorder discover --history` | local only | Contributors, hotspots, timeline: evidence of **ownership** of the areas they claim |
| 2 | `tricorder analyze OWNER/REPO --since <window start>` | GitHub sign-in or token | Review observations, an **expertise map**, and a local cache of every review and inline comment, under `.tricorder/OWNER__REPO/.raw/reviews/` and `.raw/comments/` |

After step 2, offer to read `expertise-map.json` and the person's own entries in the `.raw/`
review and comment caches yourself (ask for the full path to the clone), then characterize
their reviewing: areas, recurring asks, share of approvals that carried a comment. Cite
each point to a PR. Ignore other people's comments except as context; never quote or
characterize colleagues.

Tricorder's keyed commands (`learn`, `interpret`, `improve`, and the explorer that depends
on them) are for team-level analysis. Don't suggest them for a personal packet.

## How to use what it produces

- **Pointers, not verdicts.** Follow each finding to the PR or comment it came from and cite
  that.
- **Strongest uses:**
  - sustained ownership (hotspots, timeline);
  - raising the standard in review: asks they repeat across PRs that later became a
    convention, checklist item or lint rule;
  - substantive review (approvals that carry comments, not silent ones);
  - breadth: areas they review in that they don't author in.
- **Privacy.** `analyze` caches private review history, colleagues' included. Keep
  `.tricorder/` local, and quote only the person's own contributions in the final document.
  See [PRIVACY.md](https://github.com/dhk/tricorder/blob/main/docs/PRIVACY.md).
