# How to use impact-advocate

`impact-advocate` turns **your own** GitHub record into a document for a self-review,
promotion case, or manager 1:1. It shows where you **exceed** and where you **meet** the
expectations of your role, and backs every claim with a link or a number.

Three steps: install, run, review. Setup happens inside the skill, which checks what you
already have and asks only what it can't find out. A styled version of this page is at
[dhk.github.io/tricorder/docs/impact-advocate/](https://dhk.github.io/tricorder/docs/impact-advocate/).
For how it works, see the [system spec](IMPACT-ADVOCATE-SPEC.md).

> **Private by design.** It runs inside your own Claude Code session with your own GitHub
> sign-in. No server, no telemetry, no API key. It reads your repositories and changes
> nothing in them. On an employer's repository, check that company policy lets your Claude
> plan read the code.

> **Only for yourself.** It assesses the person running it and declines to assess anyone
> else ([constitution §6](../CONSTITUTION.md#6-study-the-system-not-the-worth-of-the-people)).

## 1. Install

In Claude Code (v2.1.275 or later), run:

```text
/plugin install impact-advocate --marketplace dhk/tricorder
```

Confirm the marketplace, pick **Install for you**, and you're done. No clone, no Python.

<details>
<summary>Older Claude Code, or installing from your shell</summary>

```bash
claude plugin marketplace add dhk/tricorder
claude plugin install impact-advocate@tricorder
```

The second command installs it for the next session; in an open one, run `/reload-plugins`.

</details>

## 2. Run

Open Claude Code in a repository you work on (or anywhere) and type:

```text
/impact-advocate:impact-advocate
```

Typing `/impact` is enough to find it. You can also just ask, for example *"help me write my
self-review from GitHub"*.

The skill takes it from there. You'll always see where you are:

```text
Step 2 of 4: Confirm  ·  Next: build the document  ·  Undo: say "start over"
```

| Step | What happens | What you do |
|---|---|---|
| **1 Check** | It reads what's already set up: GitHub sign-in, your login and commit emails, local clones, incomplete (shallow) clones. Read-only. | Nothing |
| **2 Confirm** | It shows what it found, then asks only what it couldn't find out: time window, purpose and level, what to measure against, your proudest work. One question at a time, with a recommended answer. | Accept or change each answer |
| **3 Build** | It gathers the evidence, rates each expectation **Exceeds**, **Meets** or **Not visible in GitHub**, and writes the document. | Wait |
| **4 Review** | It tells you what to check before you share. | Ask for changes in plain words |

Your answers are saved to `impact-profile.md`, after you see them. Next time, setup is one
question. Edit that file to change an answer; delete it to start fresh.

**Not signed in to GitHub?** It still works from local git history, but reviews and PR
timing will be missing. The skill tells you when that's the case; run `gh auth login` and
say "re-check".

## 3. Review before you share

- [ ] Open every link. The skill never invents evidence, but your name is on the document.
- [ ] Re-run two or three commands from the methodology appendix and check the numbers.
- [ ] Check that no colleague is named, ranked, or quoted.
- [ ] Check that co-authored and AI-assisted commits are described the way you want; the
      document discloses them because anyone can see them in the log.
- [ ] Fill **Not visible in GitHub** with what you'll bring instead: design docs, incident
      records, peer feedback.

## Optional: make it stronger with tricorder

Counts flatten code review, which is often where senior impact shows. After the document is
written, the skill may offer [tricorder](../README.md), a separate tool that maps ownership,
expertise, and how you review. It names which of your ratings tricorder would help with and
installs it with one command if you agree. Skip it and the document is still complete.

## Undo and uninstall

| To | Do |
|---|---|
| Change an answer | Say "change the window to 12 months", or edit `impact-profile.md` |
| Start setup over | Say "start over", or delete `impact-profile.md` |
| Remove the document | Delete `impact-<login>-<start>-to-<end>.md`; nothing else was written |
| Uninstall the skill | `/plugin uninstall impact-advocate@tricorder` |
| Uninstall tricorder | `pipx uninstall tricorder` or `uv tool uninstall tricorder` |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `/plugin install … --marketplace` isn't recognized | Update Claude Code, or use the two shell commands under **Install** |
| `/impact` shows nothing | Run `/reload-plugins`, then check `claude plugin list` shows `impact-advocate@tricorder` |
| No review or PR timing data in the document | It had no GitHub access. Run `gh auth login`, then say "re-check" |
| Commit counts look low | It flags shallow clones and unknown emails in Step 1; accept its fix, or add the email to `impact-profile.md` |
| It won't assess a colleague | Working as designed: it only builds your own packet |

<details>
<summary>Other agents and Claude.ai</summary>

**Claude.ai.** Turn on code execution (Settings → Capabilities; on Team and Enterprise an
admin enables skills). Download [`skills/impact-advocate`](../skills/impact-advocate), zip it
so `impact-advocate/` is the top level, and upload it under Customize → Skills. Claude.ai
can't see your local clones, so it works only from GitHub data.
([Using skills in Claude](https://support.claude.com/en/articles/12512180-using-skills-in-claude))

**Any other agent.** Give it `skills/impact-advocate/SKILL.md` as instructions and the files
in `skills/impact-advocate/references/` as context.

</details>

## Limits

- GitHub isn't the whole job. Incidents, design reviews, mentoring and cross-team work often
  leave little trace there.
- Team comparisons need several contributors. In a solo repository the skill says there's no
  baseline and treats sole ownership as a scope claim.
- The skill has been evaluated on two scenarios, both on a single-contributor repository
  using git only. Results on multi-contributor repositories with GitHub access are untested.
