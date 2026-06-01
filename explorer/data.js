// tricorder — synthesis run output (sample data)
// Wired in as a global const for the explorer to read.
window.TRICORDER_DATA = (function () {

  // The 15 categories shown on the heatmap X-axis.
  const CATEGORIES = [
    "grain", "naming", "testing", "documentation", "style",
    "performance", "modeling", "schema", "business-logic", "incremental",
    "exposure-contract", "source-freshness", "macro-complexity", "test-pyramid", "other"
  ];

  // The 9 "main" categories used on the reviewer radar charts.
  const RADAR_CATEGORIES = [
    "grain", "naming", "testing", "documentation", "modeling",
    "performance", "incremental", "source-freshness", "test-pyramid"
  ];

  // Category -> content-type tag color family.
  // patterns -> green, tools/reviewers -> purple, data/analysis -> blue, team/gaps -> orange
  const CATEGORY_GROUP = {
    grain: "data", naming: "pattern", testing: "data", documentation: "pattern",
    style: "pattern", performance: "data", modeling: "data", schema: "data",
    "business-logic": "pattern", incremental: "data", "exposure-contract": "team",
    "source-freshness": "data", "macro-complexity": "tool", "test-pyramid": "data",
    other: "pattern"
  };

  const patterns = [
    { signal: "Grain not declared on fact models", category: "grain", maturity: "convention",
      standard_citation: "dbt Labs style guide §2.1", reviewer: "ohrite", author: "vevetron",
      evidence: [
        { pr: "#4821", date: "2026-03-09", author: "vevetron", quote: "What's the grain here? fct_payments looks like it's one row per payment-attempt but the name implies one row per payment. Please declare it in the model docs." },
        { pr: "#4990", date: "2026-04-02", author: "jparr", quote: "Same as last time — add the grain to the config block so downstream folks aren't guessing." }
      ] },
    { signal: "Inconsistent grain between staging and mart layers", category: "grain", maturity: "guidance",
      standard_citation: "dbt Labs style guide §2.3", reviewer: "lauriemerrell", author: "tihuang02",
      evidence: [
        { pr: "#4877", date: "2026-03-18", author: "tihuang02", quote: "stg_trips is one row per trip but dim_trips fans out per stop — this changes the grain silently. Either rename or collapse upstream." }
      ] },
    { signal: "Missing primary key tests on staging models", category: "test-pyramid", maturity: "rule",
      standard_citation: "dbt-project-evaluator: fct_model_has_primary_key_tests", reviewer: "erikamov", author: "tihuang02",
      evidence: [
        { pr: "#4830", date: "2026-03-11", author: "tihuang02", quote: "Every staging model needs a unique+not_null on its PK. dbt-project-evaluator will flag this in CI — let's not merge red." },
        { pr: "#4905", date: "2026-03-24", author: "vevetron", quote: "PK test missing on stg_gtfs_routes. Add unique_combination_of_columns if it's a compound key." },
        { pr: "#5012", date: "2026-04-15", author: "jparr", quote: "Still no PK test here. Blocking until it's added." }
      ] },
    { signal: "Incremental predicates not scoped to partition column", category: "incremental", maturity: "guidance",
      standard_citation: "dbt Labs incremental models guide", reviewer: "ohrite", author: "jparr",
      evidence: [
        { pr: "#4858", date: "2026-03-15", author: "jparr", quote: "The is_incremental() filter scans the whole table — scope it to the partition column (service_date) or this gets expensive fast." }
      ] },
    { signal: "Snake_case violated in column aliases", category: "naming", maturity: "rule",
      standard_citation: "dbt Labs style guide §1.2", reviewer: "lauriemerrell", author: "vevetron",
      evidence: [
        { pr: "#4844", date: "2026-03-13", author: "vevetron", quote: "totalAmount -> total_amount please. We keep all identifiers snake_case." },
        { pr: "#4970", date: "2026-03-29", author: "tihuang02", quote: "Same — camelCase slipped in on a couple aliases here." }
      ] },
    { signal: "Boolean columns not prefixed with is_/has_", category: "naming", maturity: "convention",
      standard_citation: "dbt Labs style guide §1.4", reviewer: "ohrite", author: "tihuang02",
      evidence: [
        { pr: "#4912", date: "2026-03-25", author: "tihuang02", quote: "`active` should be `is_active` — booleans get the is_/has_ prefix so the type is obvious in BI tools." }
      ] },
    { signal: "schema.yml missing column descriptions", category: "documentation", maturity: "guidance",
      standard_citation: "dbt-project-evaluator: documentation_coverage", reviewer: "erikamov", author: "jparr",
      evidence: [
        { pr: "#4889", date: "2026-03-21", author: "jparr", quote: "New columns have no descriptions in schema.yml — coverage drops below our 90% threshold. Can you fill these in?" },
        { pr: "#5031", date: "2026-04-19", author: "vevetron", quote: "Docs coverage check is failing — three undocumented columns on the new mart." }
      ] },
    { signal: "Model lacks a description / purpose doc", category: "documentation", maturity: "convention",
      standard_citation: "dbt-project-evaluator: documentation_coverage", reviewer: "lauriemerrell", author: "tihuang02",
      evidence: [
        { pr: "#4933", date: "2026-03-27", author: "tihuang02", quote: "What does this model actually do? Add a one-paragraph description so the catalog is useful." }
      ] },
    { signal: "CTE not named after its purpose", category: "style", maturity: "guidance",
      standard_citation: "dbt Labs style guide §3.1", reviewer: "lauriemerrell", author: "jparr",
      evidence: [
        { pr: "#4901", date: "2026-03-23", author: "jparr", quote: "`cte1`, `cte2` — name CTEs for what they hold (e.g. `filtered_trips`, `daily_totals`). It reads like prose then." }
      ] },
    { signal: "SELECT * used in a non-staging model", category: "style", maturity: "rule",
      standard_citation: "dbt Labs style guide §3.4", reviewer: "ohrite", author: "vevetron",
      evidence: [
        { pr: "#4951", date: "2026-03-28", author: "vevetron", quote: "SELECT * in a mart hides schema drift. Enumerate columns explicitly here." }
      ] },
    { signal: "Window function over full table scan", category: "performance", maturity: "judgment",
      standard_citation: "internal: warehouse-cost runbook", reviewer: "ohrite", author: "jparr",
      evidence: [
        { pr: "#4978", date: "2026-04-04", author: "jparr", quote: "This ROW_NUMBER() over the entire fct table will be slow and pricey. Can we partition or pre-aggregate?" }
      ] },
    { signal: "Join exploding row count unexpectedly", category: "performance", maturity: "judgment",
      standard_citation: "internal: warehouse-cost runbook", reviewer: "charlie-costanzo", author: "tihuang02",
      evidence: [
        { pr: "#5002", date: "2026-04-12", author: "tihuang02", quote: "Row count jumped 8x after this join — likely a fan-out on a non-unique key. Worth a relationships test." }
      ] },
    { signal: "Business logic duplicated across two models", category: "business-logic", maturity: "guidance",
      standard_citation: "dbt Labs modeling guide", reviewer: "charlie-costanzo", author: "vevetron",
      evidence: [
        { pr: "#4925", date: "2026-03-26", author: "vevetron", quote: "The fare-recovery calc is copy-pasted here and in fct_revenue. Pull it into an intermediate model so it can't drift." }
      ] },
    { signal: "Hardcoded date filter instead of var()", category: "business-logic", maturity: "convention",
      standard_citation: "dbt Labs Jinja & macros guide", reviewer: "erikamov", author: "jparr",
      evidence: [
        { pr: "#4960", date: "2026-03-29", author: "jparr", quote: "'2024-01-01' is hardcoded — make it a var() so backfills and tests don't surprise us." }
      ] },
    { signal: "Intermediate model doing two unrelated things", category: "modeling", maturity: "guidance",
      standard_citation: "dbt Labs modeling guide", reviewer: "ohrite", author: "tihuang02",
      evidence: [
        { pr: "#4940", date: "2026-03-27", author: "tihuang02", quote: "int_trips_enriched both enriches AND aggregates — split these so each step is testable on its own." }
      ] },
    { signal: "Mart depends directly on a source", category: "modeling", maturity: "rule",
      standard_citation: "dbt-project-evaluator: marts_or_intermediate_dependent_on_source", reviewer: "lauriemerrell", author: "vevetron",
      evidence: [
        { pr: "#4995", date: "2026-04-08", author: "vevetron", quote: "Mart references source() directly — go through a staging model so lineage stays clean. Evaluator flags this." }
      ] },
    { signal: "source freshness blocks missing on new source", category: "source-freshness", maturity: "convention",
      standard_citation: "dbt source freshness docs", reviewer: "erikamov", author: "tihuang02",
      evidence: [
        { pr: "#4982", date: "2026-04-05", author: "tihuang02", quote: "New GTFS-RT source has no freshness block — add warn_after/error_after so we catch stale feeds." }
      ] },
    { signal: "Freshness thresholds set unrealistically tight", category: "source-freshness", maturity: "judgment",
      standard_citation: "dbt source freshness docs", reviewer: "charlie-costanzo", author: "jparr",
      evidence: [
        { pr: "#5020", date: "2026-04-17", author: "jparr", quote: "1-hour error_after on a daily feed will page us every night. Loosen to match the actual cadence." }
      ] },
    { signal: "Macro with deeply nested conditional logic", category: "macro-complexity", maturity: "judgment",
      standard_citation: "dbt Labs Jinja & macros guide", reviewer: "ohrite", author: "vevetron",
      evidence: [
        { pr: "#5008", date: "2026-04-14", author: "vevetron", quote: "Three levels of nested {% if %} in this macro — hard to follow and untested. Can we flatten or break it up?" }
      ] },
    { signal: "Singular test could be a generic test", category: "testing", maturity: "guidance",
      standard_citation: "dbt testing best practices", reviewer: "erikamov", author: "vevetron",
      evidence: [
        { pr: "#4948", date: "2026-03-28", author: "vevetron", quote: "This singular test is really an accepted_values check — use the generic so it's reusable and shows in the catalog." }
      ] },
    { signal: "No test on a critical revenue metric", category: "testing", maturity: "rule",
      standard_citation: "dbt-project-evaluator: test_coverage", reviewer: "lauriemerrell", author: "tihuang02",
      evidence: [
        { pr: "#5040", date: "2026-04-21", author: "tihuang02", quote: "total_fare_revenue has zero tests. For a revenue-facing column we need at least a not_null and a sane-range check." }
      ] },
    { signal: "Exposure missing description and owner", category: "exposure-contract", maturity: "convention",
      standard_citation: "dbt-project-evaluator: check_exposure_has_description", reviewer: "charlie-costanzo", author: "jparr",
      evidence: [
        { pr: "#5018", date: "2026-04-16", author: "jparr", quote: "This exposure has no owner or description — if it breaks, nobody knows who to ping. Fill in the contract." }
      ] },
    { signal: "Schema change without a deprecation note", category: "schema", maturity: "guidance",
      standard_citation: "internal: breaking-change policy", reviewer: "ohrite", author: "tihuang02",
      evidence: [
        { pr: "#5026", date: "2026-04-18", author: "tihuang02", quote: "Renaming this column is breaking for the Metabase dashboards — add a deprecation alias for one release cycle." }
      ] },
    { signal: "Unused column carried through every layer", category: "other", maturity: "judgment",
      standard_citation: "dbt-project-evaluator: unused_columns", reviewer: "charlie-costanzo", author: "vevetron",
      evidence: [
        { pr: "#5034", date: "2026-04-20", author: "vevetron", quote: "raw_blob_payload is selected the whole way up but never used downstream. Drop it at staging to save scan cost." }
      ] }
  ];

  // Reviewers: focus areas, blind spots, style, signal quality,
  // plus per-category frequency (0-100) used by the radar charts.
  const reviewers = [
    { login: "ohrite", review_style: "blocking", signal_quality: "high",
      primary_focus_areas: [
        { area: "Grain declaration", frequency: "always" },
        { area: "Incremental logic", frequency: "often" },
        { area: "Modeling boundaries", frequency: "often" }
      ],
      apparent_blind_spots: [
        { area: "Documentation coverage", basis: "never comments on schema.yml completeness across 22 PRs" },
        { area: "Source freshness", basis: "no freshness-related comments observed" }
      ],
      category_freq: { grain: 95, naming: 55, testing: 40, documentation: 10, modeling: 80, performance: 65, incremental: 90, "source-freshness": 5, "test-pyramid": 45 } },
    { login: "erikamov", review_style: "advisory", signal_quality: "medium",
      primary_focus_areas: [
        { area: "Test pyramid", frequency: "often" },
        { area: "Source freshness", frequency: "sometimes" },
        { area: "Documentation", frequency: "sometimes" }
      ],
      apparent_blind_spots: [
        { area: "Performance / query optimization", basis: "no comments on query patterns across 14 PRs" },
        { area: "Grain declaration", basis: "defers grain questions to other reviewers" }
      ],
      category_freq: { grain: 20, naming: 40, testing: 85, documentation: 70, modeling: 35, performance: 5, incremental: 30, "source-freshness": 75, "test-pyramid": 90 } },
    { login: "lauriemerrell", review_style: "blocking", signal_quality: "high",
      primary_focus_areas: [
        { area: "Naming conventions", frequency: "always" },
        { area: "Documentation", frequency: "often" },
        { area: "Modeling layering", frequency: "often" }
      ],
      apparent_blind_spots: [
        { area: "Performance / cost", basis: "rarely flags query cost; defers to ohrite" }
      ],
      category_freq: { grain: 60, naming: 95, testing: 50, documentation: 85, modeling: 75, performance: 15, incremental: 35, "source-freshness": 30, "test-pyramid": 60 } },
    { login: "charlie-costanzo", review_style: "advisory", signal_quality: "medium",
      primary_focus_areas: [
        { area: "Query performance", frequency: "often" },
        { area: "Exposure contracts", frequency: "sometimes" },
        { area: "Source freshness tuning", frequency: "sometimes" }
      ],
      apparent_blind_spots: [
        { area: "Naming conventions", basis: "no style/naming comments across 11 PRs" },
        { area: "Test coverage", basis: "leaves testing feedback to erikamov" }
      ],
      category_freq: { grain: 30, naming: 10, testing: 35, documentation: 40, modeling: 55, performance: 90, incremental: 50, "source-freshness": 70, "test-pyramid": 30 } }
  ];

  const authors = [
    { login: "vevetron", trajectory: "improving",
      strengths: [
        { area: "SQL style consistency", persistence: "consistent" },
        { area: "Responsive to grain feedback", persistence: "emerging" }
      ],
      growth_areas: [
        { area: "Grain documentation on fact models", persistence: "consistent", support_recommendation: "Add grain declaration to PR template checklist" },
        { area: "Macro readability", persistence: "occasional", support_recommendation: "Review the Jinja style section before next macro PR" }
      ] },
    { login: "tihuang02", trajectory: "stable",
      strengths: [
        { area: "PR description quality", persistence: "consistent" },
        { area: "Documentation discipline", persistence: "consistent" }
      ],
      growth_areas: [
        { area: "Primary key test coverage", persistence: "consistent", support_recommendation: "Pair on dbt-project-evaluator setup" },
        { area: "Schema-change communication", persistence: "occasional", support_recommendation: "Adopt the deprecation-alias pattern from the breaking-change policy" }
      ] },
    { login: "jparr", trajectory: "improving",
      strengths: [
        { area: "Incremental model design", persistence: "emerging" },
        { area: "Cost awareness", persistence: "emerging" }
      ],
      growth_areas: [
        { area: "Documentation coverage on new columns", persistence: "consistent", support_recommendation: "Enable the docs-coverage pre-commit hook locally" },
        { area: "Hardcoded values vs. vars", persistence: "occasional", support_recommendation: "Skim the Jinja & macros guide on var() usage" }
      ] }
  ];

  const gaps = [
    // coverage_gap
    { area: "Source freshness thresholds", gap_type: "coverage_gap", criticality: 3,
      standard_citation: "dbt source freshness docs",
      recommendation: "Add freshness blocks to all source definitions" },
    { area: "Primary key tests on staging layer", gap_type: "coverage_gap", criticality: 2,
      standard_citation: "dbt-project-evaluator: fct_model_has_primary_key_tests",
      recommendation: "Backfill unique+not_null tests across staging models" },
    { area: "Revenue metric test coverage", gap_type: "coverage_gap", criticality: 1,
      standard_citation: "dbt-project-evaluator: test_coverage",
      recommendation: "Define range and not_null tests on all revenue-facing columns" },
    // knowledge_gap
    { area: "Incremental model best practices", gap_type: "knowledge_gap", criticality: 2,
      standard_citation: "dbt Labs incremental models guide",
      recommendation: "Run an internal brown-bag on partition-scoped incremental predicates" },
    { area: "Jinja & macro hygiene", gap_type: "knowledge_gap", criticality: 3,
      standard_citation: "dbt Labs Jinja & macros guide",
      recommendation: "Document approved macro patterns in the team wiki" },
    { area: "Query cost / warehouse tuning", gap_type: "knowledge_gap", criticality: 1,
      standard_citation: "internal: warehouse-cost runbook",
      recommendation: "Share the cost runbook in onboarding; only ohrite & charlie-costanzo flag cost today" },
    // blind_spot
    { area: "Exposure contract validation", gap_type: "blind_spot", criticality: 1,
      standard_citation: "dbt-project-evaluator: check_exposure_has_description",
      recommendation: "Add dbt-project-evaluator check to CI" },
    { area: "Documentation coverage", gap_type: "blind_spot", criticality: 2,
      standard_citation: "dbt-project-evaluator: documentation_coverage",
      recommendation: "No reviewer consistently owns docs; assign a rotating docs-gate reviewer" },
    { area: "Performance review on staging PRs", gap_type: "blind_spot", criticality: 3,
      standard_citation: "internal: warehouse-cost runbook",
      recommendation: "Cost feedback concentrated in 2 reviewers; spread via pairing" }
  ];

  return {
    repo: "cal-itp/data-infra",
    window: "2026-03-01 → 2026-05-31",
    pr_count: 87,
    CATEGORIES,
    RADAR_CATEGORIES,
    CATEGORY_GROUP,
    patterns,
    reviewers,
    authors,
    gaps
  };
})();
