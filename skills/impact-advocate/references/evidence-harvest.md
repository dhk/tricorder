# Evidence harvest

Collect within the window, for all of the person's identities. Log the command behind every
number. Prefer `gh` (or the GitHub API); fall back to local git where noted.

## Signals

| Signal | What to measure | Source |
|---|---|---|
| **Delivery** | PRs authored, merged, closed-unmerged; median and p90 open→merge time; size distribution. Lines changed may be reported but never lead. | `gh`; git fallback: PR numbers from merge/squash subjects |
| **Breadth / reach** | Distinct repos, top-level directories, services touched; first contributions to a repo; cross-team PRs | `gh search prs`, `git log --name-only` |
| **Ownership** | Areas where they are top or second committer (by directory); CODEOWNERS entries; hotspots they own | git; `tricorder discover --history` |
| **Quality** | Tests added alongside code; reverts or follow-up fixes of their changes (a low rate is a claimable strength); CI and flaky-test fixes | git (`--name-only`, `revert` subjects) |
| **Review & leverage** | Reviews given; reviews with comments vs. bare approvals; inline comments; repos reviewed but not authored in; time-to-first-review given | `gh` only — not visible from git |
| **Design & direction** | RFCs, ADRs, design docs, READMEs, architecture changes landed; issues filed that others implemented | git (`*.md`, `docs/`), `gh` |
| **Unblocking others** | Reviews that unblocked releases; issues triaged/closed; dependency and tooling upgrades | `gh`, git |
| **Goal linkage** | PRs/issues mapped to a stated OKR/KPI by label, milestone, linked issue, or title | `gh` |

## Commands

Set these first:

```bash
SINCE=2026-04-01            # window start
UNTIL=2026-10-01            # window end
LOGIN=octocat               # repeat queries per login
AUTHORS='--author=me@work.com --author=me@personal.com'   # every commit email
```

### With gh

```bash
# PRs authored in the window (all repos)
gh search prs --author "$LOGIN" --created "$SINCE..$UNTIL" --limit 1000 \
  --json repository,number,title,state,createdAt,closedAt,url

# PRs reviewed (not authored)
gh search prs --reviewed-by "$LOGIN" --created "$SINCE..$UNTIL" --limit 1000 \
  --json repository,number,title,author,url

# Merge time + size for one repo
gh pr list -R OWNER/REPO --author "$LOGIN" --state merged --limit 1000 \
  --search "merged:$SINCE..$UNTIL" \
  --json number,createdAt,mergedAt,additions,deletions,changedFiles,url

# Review depth: approvals with vs. without a body, inline comment counts
gh api "repos/OWNER/REPO/pulls/NUMBER/reviews" --paginate
gh api "repos/OWNER/REPO/pulls/NUMBER/comments" --paginate

# Issues opened / closed
gh search issues --author "$LOGIN" --created "$SINCE..$UNTIL" --json repository,number,title,state,url
```

`gh search` caps at 1,000 results per query; split the window if you hit it.

### Git only (per local clone)

```bash
# Commits and active days
git log $AUTHORS --since=$SINCE --until=$UNTIL --no-merges --format='%h %ad %s' --date=short

# PR numbers referenced by squash ("(#123)") or merge ("Merge pull request #123") subjects
git log $AUTHORS --since=$SINCE --until=$UNTIL --format=%s | grep -oE '#[0-9]+' | sort -u

# Directory ownership: their share of commits per top-level dir vs. everyone's
git log --since=$SINCE --until=$UNTIL --no-merges --format='@%ae' --name-only \
  | awk '/^@/{a=$0;next} NF{split($0,p,"/"); print a, p[1]}' | sort | uniq -c

# Tests shipped with code
git log $AUTHORS --since=$SINCE --until=$UNTIL --no-merges --name-only --format='@%h' \
  | grep -cE '(^|/)(tests?|spec|__tests__)/|_test\.|\.test\.|test_'

# Reverts of their commits
git log --since=$SINCE --grep='^Revert' --format='%h %s'

# Co-authored work
git log $AUTHORS --since=$SINCE --until=$UNTIL --format='%h %(trailers:key=Co-authored-by,valueonly,separator=%x2C )' \
  | awk 'NF>1'
```

On a shallow clone, deepen first (`git fetch --shallow-since=$SINCE origin main`) or the
counts will be silently short. Check with `git rev-parse --is-shallow-repository`.

## Team baseline

Compute the same metric for all contributors in the same repos and window, and report the
median and p75 as an anonymous distribution. Exclude bots (`[bot]` logins, `github-actions`).
If the person is the only human contributor, say so: there is no baseline, and "sole
maintainer of N repos" is itself a scope claim worth making.
