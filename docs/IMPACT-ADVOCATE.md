# How to use impact-advocate

`impact-advocate` is an agent skill that mines **your own** GitHub record and writes a
Markdown document you can use in a self-review, promotion packet, or manager 1:1. It rates
your work against your role and level, shows where you **exceed** and where you **meet**
expectations, and backs every claim with a link or a number.

It is self-directed by design. Tricorder's [constitution §6](../CONSTITUTION.md#6-study-the-system-not-the-worth-of-the-people)
rules out performance-review use, with one narrow exception: you run it on yourself, you own
the output, and no colleague is ranked. The skill declines requests to assess anyone else.

## What you need

| Need | Why | Without it |
|---|---|---|
| An agent that supports skills (Claude Code, Claude.ai) or any LLM chat | Runs the skill | Paste `SKILL.md` and its references into the chat |
| `git` and local clones of your repos | Commits, ownership, tests, co-authorship | Required |
| `gh` authenticated, or a `GITHUB_TOKEN` with read access | PRs, merge times, **reviews you gave**, issues | Review work is reported as "Not visible in GitHub" |
| Your leveling guide or role description | The yardstick | The skill offers a public ladder you choose, and labels every rating with it |
| Your KPIs / OKRs | Connects PRs to outcomes | The "Contribution to goals" section is skipped |
| [Tricorder](../HOWTO.md) (optional) | Evidence of review quality, ownership and expertise | The case leans on counts alone |

## Install

**Claude Code** — copy the skill into your personal skills directory so it is available in
every repository:

```bash
git clone https://github.com/dhk/tricorder.git
mkdir -p ~/.claude/skills
cp -rf tricorder/skills/impact-advocate ~/.claude/skills/
```

Or copy it into one repository's `.claude/skills/` to scope it there.

**Claude.ai** — zip the `skills/impact-advocate` folder and upload it as a custom skill.

**Other agents** — give the agent `SKILL.md` as its instructions and the files in
`references/` as context.

## Run it

Ask in your own words; the skill triggers on requests like:

> "Review season is coming up — help me pull together my self-review from GitHub."
>
> "Mine my GitHub for the last six months and make the case I'm operating at Staff."

The skill then:

1. **Interviews you** in three short rounds, and runs nothing until you say "go":
   - *Scope and yardstick* — lookback window, every GitHub login and commit email, which
     repos, level to assess against (current or next), leveling guide, KPIs/OKRs.
   - *What mattered* — the 2–4 things you're proudest of, and your role description.
   - *Context* — audience, conventions that skew counts (squash merges, stacked PRs, bots),
     how to describe co-authored and AI-assisted commits, off-GitHub work to look for.
2. **Harvests evidence** — delivery, reach, ownership, quality, review, design, unblocking,
   goal linkage — logging the command behind every number.
3. **Rates** each expectation **Exceeds**, **Meets**, or **Not visible in GitHub**. There is
   no "below": a repo shows the presence of evidence far better than the absence of behavior.
4. **Writes** `impact-<login>-<start>-to-<end>.md`: headline, scorecard, where you exceed,
   where you meet, goals, numbers, blind spots, next-level gap, Tricorder suggestions, and a
   methodology appendix.

Already know your answers? Put them in the first message and say "skip the interview" — the
skill lists every assumption at the top of the document instead.

## Reading the output

- **`Observed:`** claims come straight from the record. **`Inferred:`** claims carry a
  one-line reason. These follow the constitution's [§8 evidence labels](../CONSTITUTION.md#8-evidence-before-assertion).
- Numbers carry their sample size; anything with n < 5 is flagged.
- Team comparisons are anonymous medians. If you are the only contributor, the document says
  so and treats sole ownership as a scope claim instead.
- **Check every link before you send it.** The skill is told never to fabricate, but you are
  the one accountable for the document.

## Strengthen it with Tricorder

Raw counts flatten review work, which is often where senior impact lives. Tricorder fills that
gap. Run each step and inspect `.tricorder/` before the next:

| Step | Command | Adds to your case |
|---|---|---|
| 1 | `tricorder discover --history` | Ownership: contributors, hotspots, timeline |
| 2 | `tricorder analyze OWNER/REPO --since <window start>` | Expertise map: whose code you review, in which areas |
| 3 | `tricorder learn OWNER/REPO --dry-run`, then `--visibility private` | Your reviewer fingerprint, author growth profile, and oversight density (approvals with comments vs. silent approvals) |
| 4 | `tricorder build OWNER/REPO --open` | Explorer for finding and screenshotting evidence |

Treat Tricorder output as **pointers, not verdicts**: follow each finding to the PR or comment
behind it and cite that. Its LLM-generated judgments are experimental and never go into the
document as fact.

**Privacy.** `learn` sends PR text, review comments and GitHub identities — your colleagues'
included — to the configured LLM provider. Confirm your employer's policy and the provider's
retention terms first, keep the named artifacts private, and quote only your own
contributions. See [PRIVACY.md](PRIVACY.md).

## Limits

- GitHub is not the whole job. Incidents, design reviews, mentoring and cross-team work often
  leave little trace; the "Not visible in GitHub" section tells you what to bring instead.
- Squash merges, pairing, and bots that open PRs for you distort counts. Tell the skill about
  them in the interview.
- Without `gh` or a token, review activity is invisible, and for senior roles that is often
  the strongest evidence. Get read access if you can.
