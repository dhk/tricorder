# How to use impact-advocate

`impact-advocate` is an agent skill that mines **your own** GitHub record and writes a
Markdown document for a self-review, promotion packet, or manager 1:1. It rates your work
against your role and level, shows where you **exceed** and where you **meet** expectations,
and backs every claim with a link or a number. Tricorder adds evidence that raw counts miss:
ownership, expertise, and the quality of your code review.

This guide takes you from nothing installed to a finished document in seven steps. It
assumes you're comfortable with a terminal and git. A styled version of this page is at
[dhk.github.io/tricorder/docs/impact-advocate/](https://dhk.github.io/tricorder/docs/impact-advocate/).

> **No API key needed for the core workflow.** The skill runs on your Claude plan in Claude
> Code, and GitHub access is a sign-in (`gh auth login`). Of tricorder's commands, only
> `learn`, `interpret` and `improve` call an AI provider, and the explorer (`build`) needs
> `learn`'s output. Everything else in this guide works without a key.

> **Scope.** The skill assesses only the person running it. Tricorder's
> [constitution §6](../CONSTITUTION.md#6-study-the-system-not-the-worth-of-the-people) rules out
> performance-review use, with one narrow exception: you run it on yourself, you own the
> output, and no colleague is ranked. The skill declines requests to assess anyone else.

**Contents**

1. [Check prerequisites](#1-check-prerequisites)
2. [Install tricorder](#2-install-tricorder)
3. [Configure access](#3-configure-access)
4. [Install the skill](#4-install-the-skill)
5. [Gather your inputs](#5-gather-your-inputs)
6. [Run the skill](#6-run-the-skill)
7. [Strengthen the case with tricorder](#7-strengthen-the-case-with-tricorder)
8. [Review before you share](#8-review-before-you-share)
9. [Troubleshooting](#troubleshooting)

---

## 1. Check prerequisites

| You need | Check with | Required? |
|---|---|---|
| Python 3.9+ | `python3 --version` | For tricorder |
| git | `git --version` | Yes |
| GitHub CLI, signed in | `gh auth status` | Strongly recommended: without it, PR and review data are invisible |
| An agent that runs skills: Claude Code, or Claude.ai with code execution on | `claude --version` | Yes (or paste the skill into any LLM chat). Runs on your Claude plan; no API key |
| An Anthropic or Gemini API key | `echo $ANTHROPIC_API_KEY` | No. Optional, for `tricorder learn` and the explorer (step 7) |

## 2. Install tricorder

Clone the repository rather than installing from a package URL. The skill lives in the
repository, and `tricorder build` writes its explorer data into the install directory.

```bash
git clone https://github.com/dhk/tricorder.git
cd tricorder
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .
tricorder --version
```

`tricorder --version` should print a version number. The virtual environment keeps tricorder
out of your system Python; run `source .venv/bin/activate` again in each new terminal.
Don't use `npm install dhk/tricorder` unless you want npm to run `pip install` in whatever
Python environment it finds (see [HOWTO.md](../HOWTO.md#npm-bridge)).

## 3. Configure access

### GitHub (for the skill and for `tricorder analyze`)

The simplest route is the GitHub CLI. Both the skill and tricorder use it:

```bash
gh auth login
gh auth status
```

If you'd rather use a token, create a
[fine-grained personal access token](https://github.com/settings/personal-access-tokens)
with **read-only** access to Contents, Pull requests, Issues and Metadata on the repositories
you'll analyze, then:

```bash
export GITHUB_TOKEN=...            # never commit it
```

Tricorder checks `GITHUB_TOKEN` first, then `gh auth token`. For a private or SSO-protected
organization, the token or `gh` identity must be authorized for that organization.

### Optional: AI provider key (for `tricorder learn` and the explorer)

Skip this unless you want step 7's optional half. If you do, set exactly one key:

```bash
export ANTHROPIC_API_KEY=...       # or GEMINI_API_KEY=...
```

Optionally write a config file that pins the provider for every repository:

```bash
tricorder config --init --global   # writes ~/.tricorder/config.yml
```

It holds `llm.provider` (`anthropic` or `gemini`), an optional `llm.model`, an `output.dir`
for reports, and reviewer allow/deny lists. Keys stay in environment variables, never in the
file.

**Before you run `learn` on an employer repository**, confirm that your employer's policy and
the provider's data-retention terms allow sending review text and colleagues' GitHub
identities to that provider. See [PRIVACY.md](PRIVACY.md).

### Keep artifacts out of git

Tricorder writes to `.tricorder/` inside the repository you analyze, and those files can name
your colleagues. Add it to that repository's ignore list:

```bash
echo ".tricorder/" >> .git/info/exclude    # local only, nothing to commit
```

## 4. Install the skill

**Claude Code.** Copy the skill folder into your personal skills directory so it works in
every project:

```bash
mkdir -p ~/.claude/skills
cp -rf skills/impact-advocate ~/.claude/skills/
```

Run this from the tricorder clone. To scope it to one repository instead, copy it to that
repository's `.claude/skills/`. Claude Code picks up new skills without a restart; if you
created `~/.claude/skills` for the first time while a session was open, run `/reload-skills`.
([Claude Code skills docs](https://code.claude.com/docs/en/skills))

**Claude.ai.** Turn on code execution first: on Free, Pro and Max plans it's under
Settings → Capabilities; on Team and Enterprise an admin enables skills for the organization.
Then zip the folder so `impact-advocate/` is the zip's top level, and upload it under
Customize → Skills → Upload a skill.
([Using skills in Claude](https://support.claude.com/en/articles/12512180-using-skills-in-claude))

```bash
cd skills && zip -r ../impact-advocate.zip impact-advocate && cd ..
```

Claude.ai can't read your local clones, so it only works from GitHub data you give it. Use
Claude Code if you want the git-history half of the evidence.

**Any other agent.** Give it `skills/impact-advocate/SKILL.md` as instructions and the four
files in `skills/impact-advocate/references/` as context.

## 5. Gather your inputs

The skill interviews you before it runs anything. Having these ready makes that take a few
minutes instead of a back-and-forth:

- [ ] **Lookback window**: usually the date of your last review to today.
- [ ] **Every GitHub login and commit email** you used in that window. Check with
      `git log --format='%ae' | sort -u` in each repository.
- [ ] **Repositories**, cloned locally with **full history**. A shallow clone silently
      undercounts; check with `git rev-parse --is-shallow-repository` and fix with
      `git fetch --unshallow`.
- [ ] **Level to assess against**: your current level for a self-review, the next one for a
      promotion case.
- [ ] **Leveling guide or career ladder** (a file path or pasted text). If you don't have one,
      the skill offers to use a public ladder you choose and labels every rating with it.
- [ ] **KPIs or OKRs** for the window, with targets.
- [ ] **The 2–4 pieces of work you're proudest of**, in rough notes.
- [ ] **Conventions that skew counts**: squash merges, stacked PRs, pairing, bots or AI agents
      that open PRs for you.

## 6. Run the skill

Start Claude Code in a working directory outside the repositories you're analyzing (the
document is written there):

```bash
mkdir -p ~/impact && cd ~/impact
claude
```

Then ask in your own words, or invoke the skill directly:

```text
/impact-advocate
```

```text
Review season is coming up. Help me pull together my self-review from GitHub for the last six months.
```

What happens next:

1. **Interview.** Three short rounds of questions: scope and yardstick, what mattered, then
   context the repository can't show. Nothing runs until you say "go". To skip the interview,
   put your answers from step 5 in the first message and say so; the skill lists every
   assumption at the top of the document instead.
2. **Harvest.** It reads `gh` and local git history and logs the command behind every number.
3. **Rating.** Each expectation gets **Exceeds**, **Meets**, or **Not visible in GitHub**.
   There's no "below": a repository shows that evidence exists far better than it shows that
   a behavior is missing.
4. **Document.** It writes `impact-<login>-<start>-to-<end>.md` with a headline, scorecard,
   where you exceed, where you meet, contribution to goals, numbers, what isn't visible in
   GitHub, the next-level gap (promotion cases), tricorder suggestions, and a methodology
   appendix.

## 7. Strengthen the case with tricorder

Counts flatten review work, which is often where senior impact lives. Tricorder fills that
gap. Run these from inside a repository you're analyzing, with the virtual environment
active, and inspect `.tricorder/` after each step before granting more access.

### Without an API key

| Step | Command | Access | What it adds to your case |
|---|---|---|---|
| 1 | `tricorder discover --history` | Local only | Contributors, hotspots, timeline: evidence for the areas you own |
| 2 | `tricorder analyze OWNER/REPO --since 2026-04-01` | GitHub sign-in | Review observations, an expertise map, and a local copy of every review and inline comment in the window |

Replace the `--since` date with the start of your window; `analyze` fetches PRs merged on or
after it. It excludes AI reviewers (Copilot, CodeRabbit and others) by default, so the review
evidence is human.

Then let the skill do the reading. In the same Claude Code session, ask:

```text
Read .tricorder/OWNER__REPO/expertise-map.json and my reviews and inline comments under
.tricorder/OWNER__REPO/.raw/reviews/ and .raw/comments/. Characterize how I review: which
areas, what I consistently push for, how often my approvals carry comments. Cite PRs.
```

This covers most of what `learn` would tell you about your own reviewing, with every point
traced to a PR you can link. It runs on your Claude plan, and nothing goes to a separate AI
provider.

### With an API key (optional)

| Step | Command | Access | What it adds |
|---|---|---|---|
| 3 | `tricorder learn OWNER/REPO --dry-run` | None (prints the prompts) | Shows exactly what would be sent to the provider |
| 4 | `tricorder learn OWNER/REPO --visibility private` | AI provider key | Reviewer fingerprint, author growth profile, and the computed oversight-density table |
| 5 | `tricorder build OWNER/REPO --open` | Needs step 4's output | Explorer at `http://localhost:7372` for browsing and screenshots |

Worth it mainly for the explorer and for team-level patterns. Tell the skill what you found
so it can trace each finding back to the PR or comment and cite that. Tricorder's
LLM-written judgments are experimental and never go into the document as fact; they're
pointers to evidence, not the evidence itself.

## 8. Review before you share

- [ ] Open every link. The skill is told never to fabricate, but you're accountable for the
      document.
- [ ] Re-run two or three commands from the methodology appendix and check the numbers match.
- [ ] Check that no colleague is named, ranked, or quoted.
- [ ] Check that co-authored and AI-assisted commits are described the way you want; the
      document discloses them because anyone can see the trailers in the log.
- [ ] Fill the **Not visible in GitHub** section with what you'll bring instead: design docs,
      incident records, dashboards, peer quotes.
- [ ] Keep `.tricorder/` and any `--visibility private` report to yourself. They name people.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `tricorder: command not found` | Activate the virtual environment: `source .venv/bin/activate` in the tricorder clone. |
| Commit counts look low | The clone is shallow, or a commit email is missing. Run `git fetch --unshallow` and add every email from `git log --format='%ae' \| sort -u`. |
| The document has no review or PR timing data | The skill had no GitHub access. Run `gh auth login` and ask it to re-harvest. |
| `No GitHub token found` from tricorder | Set `GITHUB_TOKEN` or run `gh auth login`. |
| `review-observations.json not found` | Run `tricorder analyze` for the same repository before `learn`. |
| `learnings.json not found` from `build` | The explorer needs `tricorder learn` output, which needs an API key. Skip it, or run `learn` first. |
| `learn` refuses to pick a provider | Both API keys are set. Pass `--provider anthropic` or `--provider gemini`. |
| The skill doesn't trigger | Invoke it directly with `/impact-advocate`, or check that `~/.claude/skills/impact-advocate/SKILL.md` exists. |
| Claude.ai rejects the upload | The zip's top level must be the `impact-advocate/` folder, not its contents or a parent folder. |
| The skill won't assess a colleague | Working as designed. Use `tricorder learn` for team-level analysis instead. |

## Limits

- GitHub isn't the whole job. Incidents, design reviews, mentoring and cross-team work often
  leave little trace there.
- Without `gh` or a token, review activity is invisible, and for senior roles that's often
  the strongest evidence.
- Team comparisons only make sense in repositories with several contributors. In a solo
  repository the skill says there's no baseline and treats sole ownership as a scope claim.
- The skill has been evaluated on two scenarios, both on a single-contributor repository
  using git only. Results on multi-contributor repositories with GitHub access are untested.
