# tricorder — explorer

The interactive React artifact for a synthesis run. Five tabs over the output of
`tricorder synthesize`:

| Tab | Reads | Shows |
|-----|-------|-------|
| Pattern Heatmap | `patterns[]` | reviewer × category comment frequency; click a cell for quoted evidence |
| Maturity Pipeline | `patterns[]` | read-only kanban, `judgment → guidance → convention → rule → deterministic` |
| Author Profiles | `authors[]` | strengths, growth areas, support recommendation, trajectory |
| Team Gaps | `gaps[]` | coverage / knowledge / blind-spot panels, most-critical first |
| Reviewer Fingerprints | `reviewers[]` | Recharts radar over the 9 main categories, focus areas, blind spots |

## Running it

No build step. Open `index.html` in a browser (or serve the folder).
React, Babel, and Recharts load from CDN; the JSX compiles in-browser.

```bash
cd explorer && python -m http.server 8000   # then open http://localhost:8000
```

## Wiring in a real run

All five tabs are data-driven from one global, `window.TRICORDER_DATA`, defined in
`data.js`. The synthesize step should overwrite `data.js` (or inject the same global)
with the run's output. Shape:

```js
window.TRICORDER_DATA = {
  repo: "owner/name",
  window: "YYYY-MM-DD → YYYY-MM-DD",
  pr_count: 87,

  // taxonomy — controls heatmap columns + radar axes
  CATEGORIES: [ /* 15 category slugs, X-axis of the heatmap */ ],
  RADAR_CATEGORIES: [ /* 9 main category slugs, radar axes */ ],
  CATEGORY_GROUP: { grain: "data", naming: "pattern", /* … */ }, // tag color family per category

  patterns: [{
    signal, category, maturity,            // maturity ∈ judgment|guidance|convention|rule|deterministic
    standard_citation, reviewer, author,
    evidence: [{ pr, date, author, quote }] // drives heatmap intensity + the evidence drawer
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

Tag colors follow the content-type convention: patterns → green, tools/reviewers →
purple, data/analysis → blue, team/gaps → orange.

The `data.js` currently checked in is a sample run against `cal-itp/data-infra` for
demo and visual regression.
