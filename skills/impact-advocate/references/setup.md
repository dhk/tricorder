# Setup

The person should never need a checklist. Find out what you can yourself, ask only what you
can't, and let them accept each answer in a word. Setup should take about two minutes.

Four rules hold throughout:

1. **Check before you ask.** Never ask for something a read-only command can tell you.
2. **One question at a time, recommended answer first.** Use the host's structured-question
   tool (e.g. AskUserQuestion) when there is one, with the recommended option first and
   marked "(Recommended)". Otherwise ask in plain text and say which answer you recommend.
   Skip any question the person has already answered. Exactly one question per message: no
   "also" questions tacked on the end. If a guardrail fires (no GitHub access, a shallow
   clone), that is the question; identity waits for the next message.
3. **Show where they are.** End every setup message with the status line (below).
4. **Nothing is written without a preview.** Show the profile before saving it. Setup writes
   one file, the profile, and changes nothing else on their machine.

## Status line

End each message in setup and in the run with one line in this shape:

```text
Step 2 of 4: Confirm  ·  Next: build the document  ·  Undo: say "start over"
```

The four steps are **1 Check**, **2 Confirm**, **3 Build**, **4 Review**. Use the undo that
fits the moment: "start over" during setup; "change <answer>" once the profile exists;
"delete impact-profile.md" to forget the setup completely.

## Step 1: Check (automatic, read-only)

Tell the person in one line that you're checking what's already set up and that nothing is
changed. Then run only read-only commands:

| Find out | Command | If it fails |
|---|---|---|
| git present | `git --version` | Stop. Say git is required and link https://git-scm.com/downloads |
| GitHub access | `gh auth status`, else `test -n "$GITHUB_TOKEN"` | Carry on with git only. Say once that reviews will be marked "Not visible" and that `gh auth login` fixes it |
| GitHub login | `gh api user --jq .login` | Ask for it in step 2 |
| Saved profile | `impact-profile.md` in the current directory, then `~/impact/` | No profile: first run |
| Local clones | the current directory if it's a repo, else `find . -maxdepth 2 -name .git -type d` | None is fine when `gh` works: `gh search` finds their repos |
| Commit emails | `git config user.email`, then in each clone `git log --format='%ae' --author="<name or login>" \| sort -u` | Ask in step 2 |
| Shallow clones | `git rev-parse --is-shallow-repository` per clone | Flag it (see guardrails) |
| Squash merges | share of `git log --merges` among recent commits per clone | Note it; changes how PRs are counted |
| Co-authored commits | `git log --grep='Co-Authored-By' -i --author=... \| wc -l` | Note the count |

If a saved profile exists, show it in a short table and ask one question: **use it as is
(Recommended), change something, or start over.** On "use it", go straight to Build.

Then report what you found in five lines or fewer, marking each item ✓ found, ⚠ needs
attention or ✗ missing. Example:

```text
✓ GitHub: signed in as octocat
✓ Emails: octo@work.com, octo@personal.dev
✓ Repos: 3 local clones, plus anything gh finds
⚠ acme/api is a shallow clone, so counts would be low
✗ Leveling guide: none found (I'll ask)
```

## Step 2: Confirm (a few questions, one at a time)

Ask only what Step 1 left open, in this order. Each question has a recommended answer.

1. **Does this look right?** The findings above (identities, repos). Recommended: yes. A
   "no" opens a follow-up about only the item that's wrong.
2. **Lookback window.** Recommended: since their last review, if they say a date, else the
   last 6 months. Offer 3 / 6 / 12 months or a custom range.
3. **What is this for?** Recommended: a self-review at their current level. Other options:
   a promotion case (assess against the next level), a manager 1:1. This sets the level,
   tone and length. Ask for the title and level in the same question.
4. **What to measure against.** Recommended: their leveling guide, as a file path or pasted
   text. Other options: role description only, a public ladder they name, or skip (rate
   against general expectations for the title and say so on every rating). Ask for KPIs or
   OKRs in the same question as an optional add-on.
5. **Proudest work (optional).** The 2–4 pieces of work they'd most like the document to
   cover, in rough notes. Recommended: skip; you'll find the strongest work yourself and
   they can steer later.

Don't ask about anything else up front. Conventions that distort counts (squash merges,
stacked PRs, bots opening PRs) and AI co-authorship were detected in Step 1; mention them in
the profile and let the person correct them there.

## Save the profile

Show the profile, then ask: **save and build (Recommended), edit first, or build without
saving.** On save, write `impact-profile.md` in the output folder (the current directory, or
`~/impact/` when the current directory is a repo being analyzed):

```markdown
# impact-advocate profile

Window: 2026-04-01 to 2026-10-01
Logins: octocat
Emails: octo@work.com, octo@personal.dev
Repos: all found by gh search; local clones: ~/src/api, ~/src/web
Excluded repos: none
Purpose: self-review, first person
Level: Senior Engineer (assess at current level)
Yardstick: ~/Documents/ladder.pdf
KPIs/OKRs: none given
Proudest work: (skipped)
Conventions: acme/api squash-merges; 14 commits carry Co-Authored-By (AI assistant)
Output folder: ~/impact
```

The person can edit this file by hand at any time. On the next run, Step 1 finds it and
setup is a single question.

## Guardrails

These stop the common ways a run goes wrong. Each one is a check, not a question, unless it
fires.

- **Read-only on their repos.** Setup and the harvest never write inside a repository you
  are analyzing. The document and profile go in the output folder, which must not be one of
  those repos; if the current directory is one, propose `~/impact` instead. The optional
  Tricorder step is the one exception, and the person opts into it (see `tricorder.md`).
- **Shallow clone.** Undercounts silently. Offer `git fetch --unshallow` (it only downloads
  history), or skip that clone and rely on `gh`. Ask before running it.
- **Missing identity.** If the window shows commits whose author name matches theirs but
  whose email isn't in the profile, ask whether to add the email.
- **No GitHub access.** Say once, plainly, what's lost (reviews, PR timing) and how to get
  it back (`gh auth login`, then say "re-check"). Never infer review activity from git.
- **Someone else's record.** If a login or email clearly belongs to another person, stop and
  explain the self-only scope (SKILL.md).
- **The person says "skip setup".** Use the recommended answer for every open question and
  list each assumption at the top of the document.
