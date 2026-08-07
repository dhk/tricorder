# tricorder — explorer

The [live explorer](https://dhk.github.io/tricorder/explorer/) contains sample data.
Do not publish a generated `data.js` until it has passed the privacy review in
[docs/PRIVACY.md](../docs/PRIVACY.md).

The interactive React artifact for a synthesis run. Five tabs over the output of
`tricorder learn`, in priority order (maturity pipeline is the action output, so
it leads):

| Tab | Reads | Shows |
|-----|-------|-------|
| Maturity Pipeline | `patterns[]` | read-only kanban, `judgment → guidance → convention → rule → deterministic`; the two actionable columns carry a green wash |
| Pattern Coverage | `patterns[]` | reviewer × 9-dimension coverage grid (discrete green steps, not a heat map); click a cell for quoted evidence |
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

  // taxonomy — the 9 categories drive BOTH the coverage grid columns and the radar axes
  CATEGORIES: [
    "grain","naming","testing","documentation","style",
    "performance","modeling","schema","business-logic"
  ],
  RADAR_CATEGORIES: [ /* same 9, or a subset */ ],
  CATEGORY_GROUP: { grain: "data", naming: "pattern", testing: "tool", /* … */ }, // tag color family per category
                                                                                  // pattern=green tool=purple data=blue team=orange

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

Tag colors follow the content-type convention: patterns → green, reviewers/tools →
purple, data/analysis → blue, team/gaps → orange.

The `data.js` currently checked in is a sample run against `cal-itp/data-infra` for
demo and visual regression.
