// tricorder — cal-itp/data-infra synthesis (June 2026)
// Contributor names anonymized with Star Trek character names.
// Real-name mapping stored privately at ~/.tricorder/cal-itp__data-infra-name-map.json
window.TRICORDER_DATA = (function () {

  const CATEGORIES = [
    "grain", "naming", "testing", "documentation", "style",
    "performance", "modeling", "schema", "business-logic"
  ];
  const RADAR_CATEGORIES = CATEGORIES;

  const CATEGORY_GROUP = {
    grain: "data", naming: "pattern", testing: "tool", documentation: "pattern",
    style: "pattern", performance: "data", modeling: "data", schema: "data",
    "business-logic": "pattern"
  };

  // ── Patterns ──────────────────────────────────────────────────────────────
  // Representative patterns from 184 reviewed PRs. Evidence quotes are real.
  const patterns = [

    // grain
    { signal: "Dedup windows scoped across feeds instead of within a feed",
      category: "grain", maturity: "convention",
      standard_citation: "dbt best practice: dedup in staging CTEs before downstream joins; QUALIFY window function pattern",
      reviewer: "Spock", author: "Data",
      evidence: [
        { pr: "#5220", date: "2026-04-28", author: "Spock",
          quote: "This should only dedupe within a given feed — don't dedupe across feeds. There is no reason to expect that trip ID performed should be unique across feeds and dropping like this will result in trips basically arbitrarily missing from some feeds." },
        { pr: "#5216", date: "2026-04-27", author: "Data",
          quote: "Right, the partition was too coarse. Fixed: added vehicle_positions_gtfs_dataset_key to the partition so dedup happens within feed, not across feeds. Trips that share trip_id_performed across different feeds now both survive." }
      ]
    },

    { signal: "Non-degenerate dimensions included in fact tables — fan-out collapse too broad",
      category: "grain", maturity: "judgment",
      standard_citation: "Kimball dimensional modeling: fact tables should contain measures and foreign keys only",
      reviewer: "Data", author: "Data",
      evidence: [
        { pr: "#5220", date: "2026-04-28", author: "Data",
          quote: "Yeah agreed the fan-out collapse is doing more than it should. Going with your second framing: dropping organization_name / organization_ntd_id from both fact tables since orgs aren't part of the TIDES spec anyway." },
        { pr: "#5216", date: "2026-04-27", author: "Data",
          quote: "Both ordering columns were degenerate at this grain since location_timestamp and base64_url are components of the upstream key." }
      ]
    },

    // modeling
    { signal: "Microbatch incremental strategy missing on dt-partitioned models",
      category: "modeling", maturity: "convention",
      standard_citation: "dbt incremental models; project-specific warehouse pattern (issue #4865, PR #5092)",
      reviewer: "Spock", author: "Data",
      evidence: [
        { pr: "#5216", date: "2026-04-27", author: "Spock",
          quote: "Sorry meant to have a comment that this should be microbatch incremental strategy because both it and its immediate parent are partitioned on dt." },
        { pr: "#5287", date: "2026-05-08", author: "Spock",
          quote: "Since fct_observed_trips is not partitioned on dt, this should use our incremental ranged date macros as shown in PR #5092." }
      ]
    },

    { signal: "source_record_id vs. key confusion — versioned ID used where persistent ID required",
      category: "modeling", maturity: "guidance",
      standard_citation: "Project-specific data modeling convention for stable entity identifiers",
      reviewer: "Spock", author: "LaForge",
      evidence: [
        { pr: "#4860", date: "2026-03-15", author: "Spock",
          quote: "Just noting that key is a versioned identifier so this will only ever pull this version of the GTFS dataset. If you want the persistent identifier this should be source_record_id." },
        { pr: "#5287", date: "2026-05-08", author: "Spock",
          quote: "Again maybe specific — should this be source_record_id from dim_gtfs_datasets?" }
      ]
    },

    { signal: "Mart model depends directly on a source instead of going through staging",
      category: "modeling", maturity: "rule",
      standard_citation: "dbt-project-evaluator: marts_or_intermediate_dependent_on_source",
      reviewer: "LaForge", author: "Scott",
      evidence: [
        { pr: "#5307", date: "2026-05-14", author: "LaForge",
          quote: "Model/table should be in the intermediate or mart layer, not referencing source() directly — go through staging so lineage stays clean and dbt-project-evaluator doesn't flag this in CI." }
      ]
    },

    // schema
    { signal: "dbt exposures missing — non-standard publish.product meta used instead",
      category: "schema", maturity: "convention",
      standard_citation: "dbt docs: exposures (exposure: block in .yml) for tracking downstream use of models",
      reviewer: "Spock", author: "Data",
      evidence: [
        { pr: "#5216", date: "2026-04-27", author: "Spock",
          quote: "Don't think we use publish.product anywhere else, what is intent for that as meta? Can/should we be defining a dbt exposure? That is our standard for published items." },
        { pr: "#5220", date: "2026-04-28", author: "Data",
          quote: "Good call, exposure is the right shape. Dropping the publish.product meta in this PR. Adding a single california_tides exposure as part of PR #5220 so both fct model refs resolve in the same checkout." }
      ]
    },

    { signal: "on_schema_change config omitted from microbatch migration PRs",
      category: "schema", maturity: "convention",
      standard_citation: "dbt incremental models: on_schema_change config should be set explicitly for every incremental model",
      reviewer: "Spock", author: "Spock",
      evidence: [
        { pr: "#5076", date: "2026-04-05", author: "Spock",
          quote: "Follow-up PR needed to set on_schema_change behavior that should have been included in the original conversion PR #5065." }
      ]
    },

    { signal: "SCD Type 2 join uses _is_current flag instead of valid_to/valid_from range",
      category: "schema", maturity: "guidance",
      standard_citation: "SCD Type 2 pattern: valid_from / valid_to range join",
      reviewer: "Spock", author: "Data",
      evidence: [
        { pr: "#5287", date: "2026-05-08", author: "Spock",
          quote: "Instead this should join based on the record's valid_to/valid_from dates corresponding to the dt of the RT data — if it were transitioned to microbatch you wouldn't want this _is_current flag." },
        { pr: "#5287", date: "2026-05-08", author: "Data",
          quote: "Pulled the seed-filter + public-fixed-route check into a publication_dim_records CTE so the SCD Type 2 join is just the time-window match." }
      ]
    },

    // documentation
    { signal: "External table DAG docs misstate when create-tables job must re-run",
      category: "documentation", maturity: "guidance",
      standard_citation: "BigQuery external tables behavior",
      reviewer: "Spock", author: "Rand",
      evidence: [
        { pr: "#4570", date: "2026-03-02", author: "Spock",
          quote: "The external table only needs to be created once on top of the bucket. This DAG does not have to run for new data to appear. Only needs to run if the bucket path structure or columns are changing." },
        { pr: "#4570", date: "2026-03-02", author: "Spock",
          quote: "Can 'create external tables' have an asterisk or something because it doesn't actually need to run most of the time." }
      ]
    },

    { signal: "PR description links to prerequisite docs that don't exist yet",
      category: "documentation", maturity: "guidance",
      standard_citation: null,
      reviewer: "Spock", author: "LaForge",
      evidence: [
        { pr: "#5092", date: "2026-04-12", author: "Spock",
          quote: "What does 'to be created' mean here — should not link to a doc that doesn't exist yet." },
        { pr: "#5178", date: "2026-05-01", author: "Spock",
          quote: "Suggestion: link to the docs that outline how to complete these prereq steps here." }
      ]
    },

    // testing
    { signal: "dbt schema tests absent on new fact and mart models",
      category: "testing", maturity: "rule",
      standard_citation: "dbt best practices: every model should have not_null and unique tests on primary key",
      reviewer: "Spock", author: "Spock",
      evidence: [
        { pr: "#5036", date: "2026-04-24", author: "Spock",
          quote: "Re-enabling tests that were disabled. Uniqueness and not_null tests on grain keys must pass in all environments before a model is considered production-ready." },
        { pr: "#5145", date: "2026-04-29", author: "Spock",
          quote: "Still seeing a lingering unique test failure on stg_littlepay__product_data_v3 that hasn't been fully diagnosed." }
      ]
    },

    { signal: "Test fixtures use wrong file extension or path — don't match production DAG",
      category: "testing", maturity: "guidance",
      standard_citation: "Software testing principle: test fixtures must mirror production data contracts",
      reviewer: "Scott", author: "LaForge",
      evidence: [
        { pr: "#5307", date: "2026-05-14", author: "Scott",
          quote: "Test fixture file extension doesn't match the output format the operator actually produces. Fixture path also doesn't match the production DAG path — these will never actually exercise the real code path." }
      ]
    },

    // business-logic
    { signal: "Conditional logic for GTFS-RT foreign keys not validated against spec",
      category: "business-logic", maturity: "judgment",
      standard_citation: "GTFS-RT specification: VehiclePosition.trip.schedule_relationship",
      reviewer: "Data", author: "Data",
      evidence: [
        { pr: "#5220", date: "2026-04-28", author: "Data",
          quote: "Per the GTFS-RT spec the VP trip_id does reference the schedule whenever trip.schedule_relationship is one of the in-schedule values, so deriving trip_id_scheduled from that conditional is the right shape." }
      ]
    },

    // performance
    { signal: "Unbounded BigQuery view exposed to BI tool — full table scan on every query",
      category: "performance", maturity: "judgment",
      standard_citation: "BigQuery materialization best practices",
      reviewer: "Scott", author: "Data",
      evidence: [
        { pr: "#5307", date: "2026-05-14", author: "Scott",
          quote: "We need to optimize these new tables but let's merge and test it — noting that an unmaterialized view over a large fact table at Metabase query time creates real scan cost." }
      ]
    },

    // naming
    { signal: "Environment-prefixed naming violated — calitp-{env}-* pattern not followed",
      category: "naming", maturity: "rule",
      standard_citation: "dbt Labs style guide: consistent environment and resource naming conventions",
      reviewer: "Sulu", author: "LaForge",
      evidence: [
        { pr: "#4760", date: "2026-03-07", author: "LaForge",
          quote: "Bucket name doesn't follow the calitp-{env}-* pattern. This is the third time this month we've had to correct environment-specific names after the fact." },
        { pr: "#4673", date: "2026-03-03", author: "Sulu",
          quote: "Correcting the naming convention violation — all GCS resources must be prefixed with the environment tier." }
      ]
    },

    // style
    { signal: "Array-based deduplication used instead of QUALIFY window function",
      category: "style", maturity: "guidance",
      standard_citation: "BigQuery Standard SQL: QUALIFY with ROW_NUMBER() as preferred deduplication pattern",
      reviewer: "Spock", author: "Uhura",
      evidence: [
        { pr: "#5062", date: "2026-04-25", author: "Spock",
          quote: "You could potentially achieve the same thing with a QUALIFY statement instead of a group by + array_agg — simpler and more idiomatic for BigQuery." }
      ]
    }

  ];

  // ── Reviewers ─────────────────────────────────────────────────────────────
  // 5 reviewers shown — those with meaningful signal quality.
  // category_freq: 0-100 per category, drives radar charts.
  const reviewers = [

    { login: "Spock",
      review_style: "thorough", signal_quality: "high",
      primary_focus_areas: [
        { area: "Incremental model strategy — microbatch for dt-partitioned sources, ranged-date macros for non-partitioned", frequency: "often" },
        { area: "Deduplication correctness — partition scoped within feed, not across feeds", frequency: "often" },
        { area: "dbt exposures for published models — flags non-standard meta tags", frequency: "often" },
        { area: "Documentation clarity — prerequisite links, external table lifecycle, broken references", frequency: "often" },
        { area: "SCD Type 2 correctness — valid_to/valid_from range joins, not _is_current flags", frequency: "sometimes" },
        { area: "Row access policy / security macro application on new models", frequency: "sometimes" }
      ],
      apparent_blind_spots: [
        { area: "dbt schema test coverage on new models", basis: "No test-coverage comments across 40 PRs including multiple new mart models" },
        { area: "Column-level documentation in .yml files", basis: "No comments requesting column descriptions despite multiple new models introduced" },
        { area: "Performance/cost considerations for BigQuery scans", basis: "Despite close incremental model review, no partition or clustering key comments on new fact models" },
        { area: "Model naming conventions (stg_/int_/fct_/dim_ prefixes)", basis: "No naming convention comments across any of 40 reviewed PRs" }
      ],
      category_freq: { grain: 75, naming: 10, testing: 8, documentation: 72, style: 45, performance: 18, modeling: 88, schema: 72, "business-logic": 40 }
    },

    { login: "Data",
      review_style: "conversational", signal_quality: "medium",
      primary_focus_areas: [
        { area: "Dedup partition key granularity and CTE placement — catches cross-feed collapse", frequency: "always" },
        { area: "Fact table grain integrity — no non-degenerate dimensions, fan-out collapse scope", frequency: "always" },
        { area: "Spec-conformance of derived fields — GTFS-RT schedule_relationship semantics", frequency: "often" },
        { area: "dbt exposure definitions for published models", frequency: "often" },
        { area: "SCD Type 2 CTE structure and time-window predicate scope", frequency: "sometimes" }
      ],
      apparent_blind_spots: [
        { area: "Model testing coverage — dbt tests on new fact models", basis: "No test comments across 3 PRs introducing new fct_ models" },
        { area: "Column-level documentation", basis: "Comments on mart YAML focused on exposure structure, never column descriptions" },
        { area: "Incremental strategy configuration for large fact tables", basis: "No materialization choice comments in any reviewed PR" }
      ],
      category_freq: { grain: 95, naming: 10, testing: 8, documentation: 12, style: 20, performance: 12, modeling: 55, schema: 58, "business-logic": 78 }
    },

    { login: "LaForge",
      review_style: "conversational", signal_quality: "low",
      primary_focus_areas: [
        { area: "DAG task dependency structure and flow correctness in Airflow", frequency: "sometimes" },
        { area: "Model/table placement (mart vs intermediate vs staging)", frequency: "sometimes" },
        { area: "YAML documentation completeness for new or renamed dbt models", frequency: "sometimes" },
        { area: "CI/CD workflow job naming and dependency correctness", frequency: "sometimes" },
        { area: "Reusability of Airflow operators vs one-off implementations", frequency: "sometimes" }
      ],
      apparent_blind_spots: [
        { area: "SQL grain declaration and fanout/duplication risks", basis: "No grain comments across 41 PRs touching dbt SQL models" },
        { area: "dbt test coverage (uniqueness, not-null, referential integrity)", basis: "Only one passing mention of tests across all reviews" },
        { area: "Incremental model strategy correctness", basis: "Microbatch PRs approved without scrutiny of unique_key or event_time config" },
        { area: "Terraform resource naming conventions", basis: "Multiple Terraform PRs approved with no inline commentary on naming or structure" }
      ],
      category_freq: { grain: 8, naming: 22, testing: 12, documentation: 42, style: 18, performance: 10, modeling: 38, schema: 30, "business-logic": 15 }
    },

    { login: "Scott",
      review_style: "conversational", signal_quality: "low",
      primary_focus_areas: [
        { area: "Operational safety — paused jobs, staged rollouts, non-destructive changes before merge", frequency: "often" },
        { area: "Staging vs production environment correctness in Terraform", frequency: "sometimes" },
        { area: "Cost risk from unbounded queries exposed to BI tools", frequency: "sometimes" },
        { area: "README and documentation accuracy — schedules, paths, descriptions", frequency: "sometimes" },
        { area: "Merge conflicts and CI check status as a gate", frequency: "often" }
      ],
      apparent_blind_spots: [
        { area: "dbt grain declaration and incremental model correctness", basis: "Microbatch migrations approved with 'THERE'S A CHANGE A COMING' — no grain or unique_key scrutiny" },
        { area: "SQL logic and transformation correctness", basis: "No inline comments on SELECT logic, joins, or aggregations across any PR" },
        { area: "dbt source and model YAML schema accuracy", basis: "Schema mismatch noted once then dismissed as 'not a big deal'" },
        { area: "Security review of IAM permissions and service account scoping", basis: "Service account and IAM PRs receive one-line approvals with no least-privilege commentary" }
      ],
      category_freq: { grain: 5, naming: 10, testing: 15, documentation: 32, style: 8, performance: 35, modeling: 10, schema: 22, "business-logic": 12 }
    },

    { login: "O'Brien",
      review_style: "advisory", signal_quality: "low",
      primary_focus_areas: [
        { area: "Infrastructure approvals — Terraform, Kubernetes, GCP IAM, GitHub Actions workflows", frequency: "always" },
        { area: "Data pipeline approvals — Littlepay sync, GTFS processing, Airflow DAGs", frequency: "always" },
        { area: "Pairing acknowledgment — notes pair programming sessions as approval context", frequency: "sometimes" }
      ],
      apparent_blind_spots: [
        { area: "dbt model grain declaration and primary key documentation", basis: "No grain comments across 24 PRs despite multiple dbt model touches" },
        { area: "SQL correctness and join logic", basis: "PR fixing a dedup bug approved without comment on join correctness" },
        { area: "Test coverage for dbt models", basis: "None of 24 approvals contain any comment requesting dbt schema tests" },
        { area: "Security review depth on IAM changes", basis: "PR downgrading IAM permissions approved without least-privilege commentary" }
      ],
      category_freq: { grain: 5, naming: 8, testing: 5, documentation: 10, style: 5, performance: 10, modeling: 12, schema: 8, "business-logic": 10 }
    }

  ];

  // ── Authors ───────────────────────────────────────────────────────────────
  const authors = [

    { login: "Spock", trajectory: "improving",
      strengths: [
        { area: "Systematic incremental/microbatch migration — drives large-scale strategy changes with runbook documentation", persistence: "consistent" },
        { area: "Cross-domain ownership — Payments, GTFS Schedule, and GTFS RT model families", persistence: "consistent" },
        { area: "Bug identification and remediation — proactively catches data quality issues alongside migrations", persistence: "consistent" },
        { area: "dbt test coverage — restores disabled tests and fixes failing tests", persistence: "consistent" }
      ],
      growth_areas: [
        { area: "Pre-merge test validation — multiple PRs approved conditionally pending test passage", persistence: "consistent",
          support_recommendation: "Ensure CI runs dbt build --select state:modified+ on every PR as a required gate before merge. Walk through reading CI output with reviewer." },
        { area: "Schema change completeness — on_schema_change config omitted from microbatch migrations", persistence: "occasional",
          support_recommendation: "Add on_schema_change to the microbatch migration checklist as a mandatory step in every conversion PR." }
      ]
    },

    { login: "Data", trajectory: "improving",
      strengths: [
        { area: "Responsive and thorough in addressing feedback — detailed explanations and fixes across multiple rounds", persistence: "consistent" },
        { area: "Strong GTFS/GTFS-RT domain knowledge — accurately reasons about spec semantics when challenged", persistence: "consistent" },
        { area: "Self-corrects complex SQL — dedup partitioning, fan-out collapse, SCD Type 2 once issues are surfaced", persistence: "consistent" },
        { area: "Proactive documentation and metadata additions (exposures, YAML) once reminded of team standards", persistence: "emerging" }
      ],
      growth_areas: [
        { area: "Incremental model strategy — consistently submits without correct strategy for the warehouse pattern", persistence: "consistent",
          support_recommendation: "Before any new incremental model, document in the PR which upstream sources are involved, whether they're partitioned on dt, and which strategy applies. Provide a decision tree checklist." },
        { area: "Deduplication scoping — dedup windows initially too broad, collapsing across feeds", persistence: "consistent",
          support_recommendation: "Before writing SQL, write the intended grain as a comment and confirm partition columns match with a reviewer. Add checklist: 'Does the ROW_NUMBER partition fully identify the grain without collapsing across feeds?'" },
        { area: "Exposure metadata — uses non-standard meta tags instead of dbt exposures for published models", persistence: "consistent",
          support_recommendation: "Add standing PR template checklist: 'If this model is published externally, have you defined a dbt exposure in the relevant .yml file?'" }
      ]
    },

    { login: "Scott", trajectory: "stable",
      strengths: [
        { area: "Rapid iteration and hotfix delivery — targeted fixes with minimal blast radius", persistence: "consistent" },
        { area: "Cross-functional collaboration and live debugging — self-comments to surface issues proactively", persistence: "consistent" },
        { area: "Infrastructure and operations — Kubernetes, IAM, Composer, GCS with clean approval cycles", persistence: "consistent" }
      ],
      growth_areas: [
        { area: "Root cause analysis before merging — hotfixes land without diagnosed root cause or follow-up tickets", persistence: "consistent",
          support_recommendation: "Every hotfix PR must include a linked follow-up GitHub issue before merge. Hotfix checklist: root-cause investigation is a mandatory follow-up step." },
        { area: "Model layer placement — fact model placed as view in mart folder, exposing it to Metabase with scan risk", persistence: "occasional",
          support_recommendation: "Pre-PR checklist: Is this materialized correctly for its layer? Will it appear in Metabase? Does it create unbounded scan risk?" }
      ]
    },

    { login: "LaForge", trajectory: "improving",
      strengths: [
        { area: "Broad infrastructure ownership — ships across CI/CD, Terraform, Airflow, Docker, and dbt", persistence: "consistent" },
        { area: "Responsive to reviewer feedback — addresses comments within the same review cycle", persistence: "consistent" },
        { area: "Proactive deprecation and cleanup — removes legacy artifacts without being prompted", persistence: "consistent" },
        { area: "Pairs effectively with senior engineers and incorporates pairing output into merged PRs", persistence: "consistent" }
      ],
      growth_areas: [
        { area: "Test coverage and fixture accuracy — wrong file extension, path mismatches, incorrect return types in test fixtures", persistence: "consistent",
          support_recommendation: "Pre-PR checklist: run tests locally and confirm fixture file names, paths, and return types exactly match the operator's production logic before marking ready for review." },
        { area: "YAML source definition accuracy — source fields don't match actual schema outputs", persistence: "occasional",
          support_recommendation: "When defining new sources, use dbt run-operation generate_source or manually diff the schema YAML against real data before opening the PR." }
      ]
    },

    { login: "O'Brien", trajectory: "improving",
      strengths: [
        { area: "Incremental, safe infrastructure rollout — pausing, staging-first, phased deployment patterns", persistence: "consistent" },
        { area: "Clean-up discipline — proactively removes stale or deprecated resources as part of related PRs", persistence: "consistent" },
        { area: "Infrastructure-as-code hygiene — consistent Terraform for GCP resources, narrowly scoped PRs", persistence: "consistent" }
      ],
      growth_areas: [
        { area: "Stakeholder alignment before production changes — dismissed reviews citing lack of migration plan", persistence: "consistent",
          support_recommendation: "Co-author a migration plan with stakeholders specifying: parallel-run window (≥2 weeks), success criteria, rollback steps, and sign-off. Link it in the PR description." },
        { area: "PR descriptions lack context — reviewers express uncertainty and partial comprehension on approval", persistence: "consistent",
          support_recommendation: "PR description template: (1) problem being solved, (2) summary + non-obvious decisions, (3) expected Terraform plan highlights, (4) testing steps or verification evidence." }
      ]
    },

    { login: "Rand", trajectory: "improving",
      strengths: [
        { area: "Documentation authorship — comprehensive workflow and onboarding docs consistently rated 'really good'", persistence: "consistent" },
        { area: "Responsive to review feedback — addresses inline comments and updates PRs promptly", persistence: "consistent" },
        { area: "Operational throughput — ships clusters of related PRs in tight windows with clean approvals", persistence: "consistent" }
      ],
      growth_areas: [
        { area: "Field-level schema documentation precision — unnecessary/incorrect fields in dbt YAML, not validated against data contracts", persistence: "consistent",
          support_recommendation: "Before touching _model_.yml, cross-reference each documented column against the upstream source schema and open bugs. Checklist: Is this field currently populated? Is there an open issue about it? Has the data type been verified?" },
        { area: "External table and DAG run semantics — documentation misstated when create-tables job must re-run", persistence: "consistent",
          support_recommendation: "Knowledge-share session specifically on BigQuery external table lifecycle: create once vs. run on schedule. Update documentation independently afterward and request targeted review." }
      ]
    },

    { login: "Uhura", trajectory: "improving",
      strengths: [
        { area: "Layered model building — staging → mart → fact follows dbt's recommended layering pattern", persistence: "consistent" },
        { area: "Receptiveness to reviewer feedback — adopts suggestions promptly and articulates reasoning", persistence: "consistent" },
        { area: "Self-review and proactive code quality improvement — suggests cleaner alternatives unprompted", persistence: "emerging" }
      ],
      growth_areas: [
        { area: "Airflow DAG task dependency structuring — looping approach when chaining + partial() was appropriate", persistence: "occasional",
          support_recommendation: "Review Airflow documentation on functools.partial with operators and dynamic task mapping. Pairing session on DAG design patterns in the existing repo." },
        { area: "SQL deduplication patterns — required external input to discover QUALIFY over array-based deduplication", persistence: "occasional",
          support_recommendation: "Add a SQL patterns reference doc on deduplication idioms (QUALIFY, ROW_NUMBER, DISTINCT ON) used in the warehouse." }
      ]
    },

    { login: "Sulu", trajectory: "stable",
      strengths: [
        { area: "Incremental, focused PRs — work consistently broken into single-purpose changes", persistence: "consistent" },
        { area: "Cross-functional delivery — ships infrastructure, DAG, and image-layer changes across the stack", persistence: "consistent" },
        { area: "Clean approval signal — all PRs approved, often with minimal revision cycles", persistence: "consistent" }
      ],
      growth_areas: [
        { area: "Environment parity in Terraform — parallel environment blocks not updated alongside targeted resource", persistence: "occasional",
          support_recommendation: "Before opening infra PRs, scan the full file for parallel environment definitions (e.g., c2 vs c3) and either update them or explicitly note why they're intentionally excluded." },
        { area: "PR descriptions are sparse — truncated titles, no rollback or deployment context", persistence: "consistent",
          support_recommendation: "Lightweight PR description template (What, Why, How to verify). Two to three sentences per section would materially improve reviewability." }
      ]
    },

    { login: "Worf", trajectory: "stable",
      strengths: [
        { area: "Infrastructure decommissioning — focused, well-scoped PRs removing components cleanly without scope creep", persistence: "consistent" },
        { area: "Rapid self-correction — identifies and fixes issues immediately in follow-up PRs", persistence: "consistent" },
        { area: "Security and operational hygiene — proactively applies patches, sets up monitoring before decommissioning", persistence: "consistent" }
      ],
      growth_areas: [
        { area: "Reviewer comprehension gaps — multiple approvers note they don't understand the change but approve anyway", persistence: "consistent",
          support_recommendation: "PR description template: plain-language summary of what changed and why, relevant background links, expected observable outcome. Team norm: reviewers should request clarification rather than approving without understanding." },
        { area: "Reviewer diversity — vast majority of PRs reviewed by a single reviewer", persistence: "consistent",
          support_recommendation: "For infrastructure decommissioning or migration PRs, require a second reviewer assignment. Rotate review responsibility on a scheduled basis." }
      ]
    },

    { login: "Chekov", trajectory: "stable",
      strengths: [
        { area: "Iterative problem-solving — addresses recurring false-alarm/threshold issues with targeted parameter tuning", persistence: "consistent" },
        { area: "Safe, incremental deployments — uses staging environments before promoting changes", persistence: "emerging" },
        { area: "Responsive to reviewer feedback — acts quickly on requested changes including reverts", persistence: "consistent" }
      ],
      growth_areas: [
        { area: "PR description precision — 'Resolves' keyword used incorrectly, can auto-close issues still in progress", persistence: "occasional",
          support_recommendation: "PR template: distinguish 'Resolves #X' (closes ticket) from 'Working towards #X' (partial progress)." },
        { area: "Root cause documentation — threshold tuning PRs lack rationale for specific values chosen", persistence: "consistent",
          support_recommendation: "Pair with a senior engineer to co-author a short ADR for one tuning PR, establishing the habit of documenting 'why this value' alongside 'what changed'." }
      ]
    }

  ];

  // ── Gaps ─────────────────────────────────────────────────────────────────
  // 11 gaps identified in team gap analysis (Phase 4).
  // criticality: 1 = highest, 3 = lowest (drives sort order in UI)
  const gaps = [

    { area: "LGTM approvals on high-risk SQL changes — no inline technical scrutiny",
      gap_type: "coverage_gap", criticality: 1,
      standard_citation: "The Checklist Manifesto: breaking changes warrant checklist-driven review covering grain, tests, and downstream impact",
      recommendation: "Add a PR checklist template for fct_ model changes requiring explicit sign-off on: join logic, grain definition, filter correctness, and downstream model impact. Gate merge on at least one inline technical comment for PRs labeled 'breaking change' or touching fct_ models." },

    { area: "dbt model config review — materialization strategy, incremental strategy, unique_key correctness",
      gap_type: "blind_spot", criticality: 1,
      standard_citation: "dbt Labs style guide: incremental models require explicit unique_key and incremental_strategy; dbt-project-evaluator: fct_missing_primary_key_tests",
      recommendation: "Add a CI gate using dbt-project-evaluator checks (missing_primary_key_tests, model_fanout). Include materialization/incremental strategy review as a mandatory checklist item for any PR touching model configs." },

    { area: "Referential integrity and upstream/downstream lineage impact analysis",
      gap_type: "coverage_gap", criticality: 2,
      standard_citation: "dbt-project-evaluator: direct_join_to_source, downstream_models_not_null checks",
      recommendation: "Require reviewers to cite dbt lineage graph output in PR descriptions for any model addition or rename. Add dbt-project-evaluator direct_join_to_source as a CI check." },

    { area: "Defined rollback plan and success criteria before merging live pipeline changes",
      gap_type: "knowledge_gap", criticality: 1,
      standard_citation: "The Checklist Manifesto: define rollback criteria and monitoring thresholds before merging live pipeline changes",
      recommendation: "Create a formal 'data pipeline change' PR template with required fields: success criteria, rollback procedure, monitoring thresholds. Treat 'merge and watch' as a non-compliant review pattern." },

    { area: "Test pyramid coverage — integration and end-to-end tests for data-critical pipeline code",
      gap_type: "knowledge_gap", criticality: 2,
      standard_citation: null,
      recommendation: "Document the expected test pyramid for each pipeline category (infrastructure change, dbt model, Airflow DAG). Add a CI gate requiring at least one integration test result linked in PRs touching production data feeds." },

    { area: "Reviewer approval with self-acknowledged partial comprehension",
      gap_type: "coverage_gap", criticality: 2,
      standard_citation: null,
      recommendation: "Team norm: partial-comprehension approvals must be labeled 'conditional' and require a second reviewer with domain expertise before merge. Add to the contributing guide and PR template." },

    { area: "Formal SLA and reliability requirements for real-time data pipelines",
      gap_type: "blind_spot", criticality: 3,
      standard_citation: null,
      recommendation: "Define and document SLA requirements (uptime, latency, data freshness) for RT archiving pipelines in a dedicated ADR or runbook before any migration PR is opened. Require a link in migration PRs." },

    { area: "Independent verification of Terraform plan outputs by reviewers",
      gap_type: "knowledge_gap", criticality: 2,
      standard_citation: null,
      recommendation: "Require Terraform plan output pasted or linked in the PR body. Add a CI step that generates and archives terraform plan output as a required status check so reviewers can inspect it independently." },

    { area: "dbt source freshness and data recency testing",
      gap_type: "blind_spot", criticality: 2,
      standard_citation: "dbt Labs style guide: define source freshness checks on all sources; dbt-project-evaluator: missing_source_freshness",
      recommendation: "Add dbt-project-evaluator missing_source_freshness as a CI check. Include 'source freshness thresholds defined?' as a checklist item for any PR adding or modifying dbt sources." },

    { area: "SQL style consistency enforcement — aliasing, CTE structure, trailing commas",
      gap_type: "blind_spot", criticality: 3,
      standard_citation: "SQLFluff rules: L011 (implicit aliasing), L022 (blank lines around CTEs), L036 (single column per SELECT line)",
      recommendation: "Integrate SQLFluff with the dbt Labs dialect into CI as a required linting gate. Block merges on lint failures." },

    { area: "Breaking change communication and downstream consumer notification",
      gap_type: "knowledge_gap", criticality: 2,
      standard_citation: "dbt Labs style guide: document breaking changes in CHANGELOG; communicate schema changes to downstream consumers",
      recommendation: "Require a CHANGELOG entry and downstream consumer list as mandatory fields in the PR template for any PR tagged 'breaking change'. Add a review checklist item to verify this is complete." }

  ];

  return {
    repo: "cal-itp/data-infra",
    window: "2026-03-02 → 2026-05-30",
    pr_count: 190,
    prs_with_reviews: 184,
    contributors: 15,
    visibility: "demo",
    CATEGORIES,
    RADAR_CATEGORIES,
    CATEGORY_GROUP,
    patterns,
    reviewers,
    authors,
    gaps
  };
})();
