# tricorder — explorer

The [live explorer](https://dhk.github.io/tricorder/explorer/) contains sample data.
Do not publish a generated `data.js` until it has passed the privacy review in
[docs/PRIVACY.md](../docs/PRIVACY.md).

The interactive React artifact for a synthesis run. An orientation tab followed by
five data tabs over the output of `tricorder learn`, in priority order (maturity
pipeline is the action output, so it leads the data tabs):

| Tab | Reads | Shows |
|-----|-------|-------|
| Start Here | run summary fields | orientation: what tricorder is about, the four-step pipeline, how to read each tab, the maturity ladder, gap types, colour legend, caveats, and links back to the repo. Default tab on first load |
| Maturity Pipeline | `patterns[]` | read-only kanban, `judgment → guidance → convention → rule → deterministic`; the two actionable columns carry a cobalt tint |
| Pattern Coverage | `patterns[]` | reviewer × 9-dimension coverage grid (discrete cobalt steps, not a heat map); click a cell for quoted evidence |
| Team Gaps | `gaps[]` | coverage / knowledge / blind-spot panels, most-critical first |
| Reviewer Fingerprints | `reviewers[]` | Recharts radar over the 9 categories, focus areas, blind spots |
| Author Profiles `PRIVATE` | `authors[]` | strengths / growth areas / support; gated on `visibility` |

## Running it

No build step. Open `index.html` in a browser (or serve the folder).
React, Babel, and Recharts load from CDN; the JSX compiles in-browser.

```bash
cd explorer && python -m http.server 8000   # then open http://localhost:8000
```

## Wiring in a real run

All tabs are data-driven from one global, `window.TRICORDER_DATA`, defined in `data.js`.
The `tricorder build` step overwrites `data.js` (or injects the same global) with the
run's output. Shape:

```js
window.TRICORDER_DATA = {
  repo: "owner/name",
  window: "YYYY-MM-DD → YYYY-MM-DD",
  pr_count: 190,
  visibility: "private",                    // private -> Author Profiles render; team|public -> withheld notice
  lens: { name: "product-engineering-desktop", version: 1, status: "experimental", archetype: "product-engineering" },
                                            // null for runs that predate lens tracking; Start Here shows it

  // taxonomy — comes from the lens: every lens category is a coverage-grid column,
  // the radar uses the 9 core categories (correctness … dependencies, minus "other")
  CATEGORIES: [
    "correctness","security","testing","documentation","style","performance",
    "error-handling","maintainability","dependencies","other", /* + lens extensions */
  ],
  RADAR_CATEGORIES: [ /* the 9 core categories */ ],
  CATEGORY_GROUP: { grain: "data", naming: "pattern", testing: "tool", /* … */ }, // tag color family per category
                                                                                  // pattern=cobalt tool=purple data=teal team=orange

  patterns: [{
    signal, category, maturity,             // maturity ∈ judgment|guidance|convention|rule|deterministic
    standard_citation, reviewer, author,
    evidence: [{ pr, date, author, quote }] // drives coverage depth + the evidence drawer
  }],

  reviewers: [{
    login, review_style, signal_quality,    // signal_quality ∈ high|medium|low
    primary_focus_areas: [{ area, frequency }],
    apparent_blind_spots: [{ area, basis }],
    category_freq: { /* radar category slug -> 0..100 */ }
  }],

  authors: [{
    login, trajectory,                       // trajectory ∈ improving|stable|regressing
    strengths: [{ area, persistence }],
    growth_areas: [{ area, persistence, support_recommendation }]
  }],

  gaps: [{
    area, gap_type, criticality,             // gap_type ∈ coverage_gap|knowledge_gap|blind_spot; criticality 1 = most critical
    standard_citation, recommendation
  }]
};
```

Tag colors follow the content-type convention: patterns → cobalt, reviewers/tools →
purple, data/analysis → teal, team/gaps → orange.

The `data.js` currently checked in is a sample run against `cal-itp/data-infra` for
demo and visual regression.
