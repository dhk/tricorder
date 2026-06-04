# How to run tricorder

Step-by-step from zero to a finished report. Assumes Python 3.9+ is installed. Nothing else required upfront.

---

## 1. Get the code

```bash
git clone https://github.com/dhk/tricorder.git
cd tricorder
pip install anthropic requests
```

---

## 2. Set up credentials

You need two credentials. Neither is stored in the repo.

### GitHub token

Tricorder uses the GitHub REST API to pull PR data. Create a classic PAT:

1. Go to https://github.com/settings/tokens → **Generate new token (classic)**
2. Name: `tricorder`
3. Scope: `public_repo` for public repos, `repo` for private
4. Copy the token (`ghp_...`)

Set it in your shell:
```bash
export GITHUB_TOKEN=ghp_your_token
```

To make it permanent (add to `~/.zshrc` or `~/.bashrc`):
```bash
echo 'export GITHUB_TOKEN=ghp_your_token' >> ~/.zshrc
```

Or store it in the macOS keychain and load on demand:
```bash
security add-generic-password -a "$USER" -s "github-tricorder-pat" -w "ghp_your_token"
export GITHUB_TOKEN=$(security find-generic-password -a "$USER" -s "github-tricorder-pat" -w)
```

### Anthropic API key

Tricorder calls Claude during synthesis. Get a key at https://console.anthropic.com.

Set it:
```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Or store in macOS keychain (tricorder checks this automatically):
```bash
security add-generic-password -a "$USER" -s "anthropic_api_key" -w "sk-ant-..."
```

---

## 3. Pick a repo to analyze

Tricorder works best on repos that:
- Have **30+ merged PRs** in your target window
- Have **active inline review comments** (not just LGTM approvals)
- Use **dbt and/or SQL** — the category taxonomy is calibrated for analytics engineering

It works less well when:
- Review happens in Slack rather than GitHub comments
- PRs are rubber-stamped with no inline discussion
- The repo is not dbt/SQL (output degrades — findings are generic)

Public or private repos both work. Private repos require `repo` scope on your PAT.

---

## 4. Check the cost first

Before spending any API credits, run the cost probe. It pulls a sample of real PRs, assembles the exact prompts, counts tokens, and prints a cost table — no Claude API spend.

```bash
python tricorder-cost-probe.py OWNER/REPO --limit 20
```

Read the output:
- **Per-PR cost** — typical: ~$0.015
- **Projected total** — shown for 30 / 60 / 90 / 150 / 300 PR windows
- **Warnings** — thin review signal, low description quality, etc.

If the projected cost looks right, proceed. If the per-PR cost is much higher than expected, check the warning section — very long PR descriptions or many inline comments will inflate it.

---

## 5. Harvest

Pull merged PRs from GitHub into a local cache. No Claude API spend.

```bash
python tricorder-harvest.py OWNER/REPO --since 2026-01-01
```

**Flags:**
- `--since YYYY-MM-DD` — only pull PRs merged on or after this date. A 90-day window (3 months) is a good starting point.
- `--limit N` — stop after N PRs (useful for a test run before committing)
- `--force` — re-fetch PRs that are already cached

**What it does:**
- Pulls PR metadata, descriptions, formal review threads, and inline diff comments
- Fetches repo context: `dbt_project.yml`, `.sqlfluff`, and the PR template
- Filters out bot PRs (Dependabot etc.)
- Marks which comments received replies (a proxy for substantive discussion)
- Writes everything to `~/.learn-from-work/cache/OWNER__REPO/`

**Incremental:** re-running without `--force` only fetches PRs newer than the last harvest. Safe to run on a schedule.

**Output:**
```
✓ Harvest complete
  PRs fetched (new):    142
  PRs cached (skipped): 0
  Total in cache:       142
  Contributors:         12
  Date range:           2026-01-01 → 2026-06-01
```

---

## 6. Synthesize

Run the four-phase Claude analysis. This is where the API spend happens.

```bash
python tricorder-synthesize.py OWNER/REPO --visibility private
```

**Flags:**
- `--visibility private|team|public` — controls what appears in the output report. `private` includes author growth profiles by name. `team` redacts them. `public` anonymizes everything. Default: `private`.
- `--out PATH` — directory to write the Markdown report. Default: `~/Documents/dev/adventures-in-ai/tricorder/` if it exists, otherwise `./output/`.

**What the four phases do:**

| Phase | One call per | What it returns |
|-------|-------------|-----------------|
| 1 | PR | Patterns extracted, evidence quotes, author signals, reviewer signals |
| 2 | Reviewer | Focus fingerprint: primary areas, blind spots, signal quality |
| 3 | Author | Growth profile: strengths, recurring gaps, trajectory |
| 4 | Team (aggregate) | Team gaps, institutionalization candidates, review culture observation |

**How long it takes:**
- ~15–20 seconds per PR for Phase 1 (the bulk of the time)
- Phases 2–4 are fast aggregate calls
- 100 PRs ≈ 25–30 minutes total

**Resume-safe:** if synthesis is interrupted, re-running skips already-completed phases. The intermediate JSON is cached in `~/.learn-from-work/cache/OWNER__REPO/synthesis/`.

**Output:**
```
✓ Report written to: ./output/2026-06-01-owner__repo.md
```

---

## 7. View your results

### Markdown report

The report is at the path printed at the end of synthesis. Open it on GitHub or any Markdown viewer. Sections:

1. **Patterns ready to institutionalize** — table of candidates with current maturity, next step, and target maturity
2. **Reviewer focus fingerprints** — per-reviewer narrative: what they consistently catch, what they consistently miss
3. **Author growth profiles** — per-author narrative: strengths, growth areas, trajectory, support recommendations
4. **Team gap analysis** — team strengths, gaps by type, institutionalization candidates, review culture observation

### Interactive explorer

Generate and open the local explorer:

```bash
python tricorder-render-explorer.py OWNER/REPO
open explorer/index.html
```

Or, if you've pushed the repo to GitHub with Pages enabled, the live URL is:
`https://YOURUSERNAME.github.io/tricorder/explorer/`

---

## 8. Anonymize for sharing (optional)

If you want to share results without exposing contributor names, create a name map before rendering:

**Create `~/.tricorder/OWNER__REPO-name-map.json`:**
```json
{
  "mapping": {
    "real-github-login": "Alias",
    "another-login": "AnotherAlias"
  }
}
```

Then re-render:
```bash
python tricorder-render-explorer.py OWNER/REPO
```

The renderer auto-detects the map and applies it to all names in `data.js`. Push `explorer/data.js` to GitHub and Pages updates automatically.

---

## 9. Run from Codespaces

The repo includes a devcontainer. Open it in Codespaces or VS Code:

1. Open the repo in Codespaces (or locally with Dev Containers)
2. Set secrets in GitHub repo settings → **Secrets → Codespaces**:
   - `GITHUB_TOKEN`
   - `ANTHROPIC_API_KEY`
3. Run synthesis as normal — credentials are available as env vars

Use `--out ./output` since the default output path (`~/Documents/dev/adventures-in-ai/tricorder/`) won't exist in a Codespace:

```bash
python tricorder-synthesize.py OWNER/REPO --out ./output
```

---

## Troubleshooting

**`GITHUB_TOKEN not set`**
```bash
export GITHUB_TOKEN=$(security find-generic-password -a "$USER" -s "github-tricorder-pat" -w)
```

**`No harvest cache found`**
Run `tricorder-harvest.py` first. Synthesis requires the cache.

**Synthesis stops mid-run**
Re-run the same command. It skips completed phases and picks up from where it stopped.

**`credit balance too low`**
Top up at https://console.anthropic.com. Then delete any errored synthesis files and re-run:
```bash
# Remove error files from Phase 1
for f in ~/.learn-from-work/cache/OWNER__REPO/synthesis/pr/*.json; do
  python3 -c "import json,sys; d=json.load(open('$f')); sys.exit(0 if not d.get('_error') else 1)" 2>/dev/null || rm "$f"
done
# Re-run
python tricorder-synthesize.py OWNER/REPO
```

**Explorer shows only rule/deterministic patterns in pipeline**
Re-render — an older version of the renderer had a sorting bug. Fixed in v1.2+:
```bash
python tricorder-render-explorer.py OWNER/REPO
```

---

## Quick reference

```bash
# 1. Install
git clone https://github.com/dhk/tricorder && cd tricorder
pip install anthropic requests
export GITHUB_TOKEN=ghp_...
export ANTHROPIC_API_KEY=sk-ant-...

# 2. Cost check
python tricorder-cost-probe.py OWNER/REPO --limit 20

# 3. Harvest
python tricorder-harvest.py OWNER/REPO --since 2026-01-01

# 4. Synthesize
python tricorder-synthesize.py OWNER/REPO

# 5. View
python tricorder-render-explorer.py OWNER/REPO
open explorer/index.html
```

---

## What each file does

| File | Purpose |
|------|---------|
| `tricorder-harvest.py` | Pull PRs from GitHub → local cache |
| `tricorder-cost-probe.py` | Estimate token cost before synthesis |
| `tricorder-synthesize.py` | Run 4-phase Claude analysis → Markdown report |
| `tricorder-render-explorer.py` | Generate explorer/data.js from synthesis cache |
| `tricorder-demo.py` | Scripted 4-minute live demo (no API spend) |
| `explorer/` | Interactive HTML explorer |
| `DESIGN.md` | Architecture and design decisions |
| `SKILL.md` | Claude skill spec |
| `DEMO.md` | Presenter guide for live demos |
