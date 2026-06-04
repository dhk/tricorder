#!/usr/bin/env python3
"""
tricorder-demo.py — scripted 4-minute walkthrough for live demos

Simulates the full harvest → synthesize pipeline using real data from the
cal-itp/data-infra run (June 2026). Contributor names anonymized with
Star Trek character names. No GitHub API calls. No Claude API spend.

Usage:
    python tricorder-demo.py           # full demo with pacing + pauses
    python tricorder-demo.py --fast    # skip delays, pauses still fire (for dry-runs)
    python tricorder-demo.py --no-pause  # run straight through, no input() stops

Pause points (5 total — each is a narration beat):
    [0] After cost probe  — "Before we spend a dollar, we know exactly what we'll spend."
    [1] After harvest     — "190 PRs in cache. Zero API spend."
    [2] After Phase 1     — "This is what Claude sees. This is what it returns."
    [3] After Phase 2     — "40 PRs distilled into a fingerprint."
    [4] After Phase 4     — "11 gaps. This is the conversation starter."

Naming note: names shown are Star Trek character aliases.
Real→alias map stored at ~/.tricorder/cal-itp__data-infra-name-map.json
"""

import sys
import time

# ── CLI flags ─────────────────────────────────────────────────────────────────
FAST      = "--fast"      in sys.argv
NO_PAUSE  = "--no-pause"  in sys.argv

# ── ANSI colors ───────────────────────────────────────────────────────────────
RST  = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
GRN  = "\033[32m"
YLW  = "\033[33m"
CYN  = "\033[36m"
RED  = "\033[31m"
BLU  = "\033[34m"
MAG  = "\033[35m"

def p(text=""):
    print(text)

def dim(text):
    print(f"{DIM}{text}{RST}")

def header(text):
    print(f"\n{BOLD}{CYN}{text}{RST}")

def ok(text):
    print(f"{GRN}✓{RST} {text}")

def warn(text):
    print(f"{YLW}⚠{RST}  {text}")

def label(k, v):
    print(f"  {DIM}{k:<22}{RST}{v}")

def slowprint(text, delay=0.018):
    """Typewriter effect for key output lines."""
    if FAST:
        print(text)
        return
    for ch in text:
        print(ch, end="", flush=True)
        time.sleep(delay)
    print()

def pause(note=""):
    """Pause for presenter narration. Shows a cue and waits for ENTER."""
    if NO_PAUSE:
        time.sleep(0.3)
        return
    cue = f"\n{BOLD}{YLW}  ◆  {note}{RST}\n  {DIM}[ENTER to continue]{RST} "
    input(cue)
    print()

def sleep(s):
    if not FAST:
        time.sleep(s)


# ── Embedded data ─────────────────────────────────────────────────────────────
# 190 real PRs from cal-itp/data-infra, March–May 2026.
# Author names anonymized.

ALL_PRS = [
    (4491, "O'Brien", "Analyst sees that GTFS-RT feed archiving is covered by"),
    (4537, "O'Brien", "Analysts see a fanned-out DAG for processing Littlepay"),
    (4570, "Rand",    "Documentation (payments): modify workflow documentation"),
    (4673, "LaForge", "Use correct name convention enghouse buckets on Staging"),
    (4677, "O'Brien", "Analyst can manually add GTFS Schedule ZIP files to a s"),
    (4759, "LaForge", "Replace enghouse bucket on production with the correct"),
    (4828, "Spock",   "Move Payments reconciliation tables into warehouse"),
    (4850, "Worf",    "Improve postgres backup portability and add Metabase re"),
    (4856, "Chekov",  "fix: tune threshold and parameters to avoid false alarm"),
    (4857, "Crusher", "RT trip updates stop / trip / operator aggregations"),
    (4858, "LaForge", "Generate results file when converting empty GTFS Schedu"),
    (4860, "Spock",   "Fix: add feed_version to Payments joins to dedupe Micro"),
    (4863, "Spock",   "feat: microbatch strategy for dim stop arrivals (#4783)"),
    (4867, "O'Brien", "Enable backups for Metabase CloudSQL instance"),
    (4870, "LaForge", "Analyst only sees manual GTFS schedules as a fallback"),
    (4875, "O'Brien", "Add staging workflow service account and cloud function"),
    (4876, "O'Brien", "Update workflow service account and remove cloud functi"),
    (4888, "Chekov",  "tune MQL and other attributes to stop false alarm"),
    (4889, "Spock",   "Create Payments product data dimension model"),
    (4891, "LaForge", "Upgrade altair to 6.0 to fix data-analyses repo error"),
    (4892, "LaForge", "Use new calitp-data-analysis image to fix Altair versio"),
    (4893, "Spock",   "Add Troi to code owners to approve PRs"),
    (4894, "Spock",   "dim_stop_times microbatch (#4866)"),
    (4896, "Scott",   "Adjust dbt_short_name so it can handle edge cases"),
    (4898, "O'Brien", "Owners added to the owner role"),
    (4900, "LaForge", "New calitp-data-analysis image with dask-geopandas 0.5"),
    (4904, "Guinan",  "Benefits: update enrollment_method from digital to sign"),
    (4908, "LaForge", "Promotes 2026.2.6 JupyterHub image to default"),
    (4914, "LaForge", "Migrate warehouse from poetry to uv"),
    (4920, "LaForge", "Sync Metabase using new url"),
    (4926, "Spock",   "int_gtfs_rt__vehicle_positions_trip_day_map grouping"),
    (4927, "Worf",    "fix(k8s): update bitnami Docker image for 2nd zookeeper"),
    (4932, "LaForge", "Fix dbt artifacts update timing"),
    (4933, "Scott",   "Make elavon operations sequential and in memory"),
    (4941, "LaForge", "Fix Airflow warnings"),
    (4942, "Scott",   "Hotfix to stop duplicates on dim_stop_latest"),
    (4943, "Rand",    "Benefits: Add row-level security to benefits mart table"),
    (4949, "LaForge", "Migrate devcontainer to uv"),
    (4951, "LaForge", "Update documentation to use uv"),
    (4957, "Sulu",    "Strip dependencies out of jupyter-singleuser"),
    (4958, "Sulu",    "New jupyterhub image with minimal dependencies"),
    (4959, "Scott",   "Updates to ckan publishing"),
    (4961, "Sulu",    "Remove Git LFS from jupyter-singleuser image"),
    (4966, "LaForge", "Make the publish_gtfs dag weekly"),
    (4967, "Scott",   "Changed model arrays to strings to comply with ckan"),
    (4968, "Scott",   "Reverse changes to fields, stop publishing an array"),
    (4981, "Spock",   "Migrate GTFS Schedule Dimension Tables To Microbatch"),
    (4982, "Crusher", "Consolidate rollup route-direction summary and fix"),
    (4990, "Uhura",   "Add Airtable Issue Management DAG with custom operator"),
    (5004, "LaForge", "Adding Environmental Variables"),
    (5011, "LaForge", "TIDES: add DAG and ingestion for TIDES data"),
    (5017, "O'Brien", "Add GCP project to Composer 3 Terraform"),
    (5018, "LaForge", "Add Kubernetes node pool for Composer 3"),
    (5019, "LaForge", "Add Composer 3 service accounts"),
    (5022, "O'Brien", "Add Cloud SQL Proxy and AlloyDB client configs"),
    (5025, "LaForge", "Add Composer 3 GCS buckets"),
    (5028, "Sulu",    "Add Composer 3 service accounts for Kubernetes"),
    (5029, "LaForge", "Add Littlepay static IPs for Composer 3"),
    (5030, "Sulu",    "Add Elavon SFTP service account"),
    (5031, "LaForge", "Remove Composer 2 node pools"),
    (5032, "Sulu",    "Add static IP for Elavon SFTP Composer 3"),
    (5033, "Sulu",    "Add GCS buckets for Elavon SFTP Composer 3"),
    (5034, "LaForge", "Remove Composer 3 Cloud Function"),
    (5036, "Spock",   "Re-enable failing tests"),
    (5038, "Worf",    "Deploy dbt to Composer 3"),
    (5041, "Sulu",    "Add Airflow variables for Composer 3"),
    (5043, "Worf",    "Migrate archiver deployments to Composer 3"),
    (5044, "Worf",    "Remove in-cluster Grafana/Prometheus/Loki stack"),
    (5045, "Rand",    "Add Airtable automation for onboarding tracker"),
    (5046, "LaForge", "Decommission Composer 2"),
    (5049, "Scott",   "TIDES: wire in new outcomes DAG"),
    (5051, "Spock",   "Fix RT index join"),
    (5055, "LaForge", "Remove Composer 2 GCS buckets"),
    (5057, "Uhura",   "Add README for Airtable issue management feature"),
    (5059, "Worf",    "Remove Sentry error monitoring"),
    (5062, "Uhura",   "Deduplicate Airtable issues using QUALIFY"),
    (5063, "LaForge", "Remove calitp-gtfs-schedule-raw-processed bucket"),
    (5065, "Spock",   "dim_stop_arrivals: fix old message age calc + microbatc"),
    (5066, "LaForge", "Remove deprecated Cloud Scheduler jobs"),
    (5067, "Worf",    "Deploy JupyterHub 3.3.8 patch (CVE fix)"),
    (5069, "LaForge", "Remove Composer 2 environment"),
    (5074, "Worf",    "Add monitoring replacement before decommissioning"),
    (5076, "Spock",   "Set on_schema_change for microbatch models"),
    (5078, "LaForge", "Remove unused calitp-ci-runner bucket"),
    (5086, "Scott",   "TIDES: fix dim_stop_latest duplicate issue"),
    (5089, "Worf",    "Remove Composer 2 Kubernetes resources"),
    (5090, "O'Brien", "Rename GTFS-RT archiver module"),
    (5092, "Spock",   "Add ranged date macros for non-partitioned incremental"),
    (5095, "Bashir",  "Add --select flag to slim CI dbt run command"),
    (5097, "Sulu",    "Create Littlepay parse audit table"),
    (5099, "Worf",    "Remove Metabase from cluster"),
    (5100, "O'Brien", "Add GTFS-RT archiver unit tests"),
    (5103, "Bashir",  "Migrate data_tests yaml syntax"),
    (5106, "LaForge", "Deploy dbt workflow to Composer 3"),
    (5107, "Worf",    "Decommission in-cluster Metabase (final cleanup)"),
    (5108, "LaForge", "Pin Composer 3 Python packages"),
    (5110, "Scott",   "TIDES: update NTD external tables"),
    (5111, "LaForge", "Add calitp-gtfs-rt-raw-external bucket"),
    (5113, "Rand",    "Add onboarding intake template"),
    (5117, "LaForge", "Fix Composer 3 rollout issues"),
    (5121, "O'Brien", "Add Littlepay SFTP cluster"),
    (5122, "LaForge", "Fix dbt Composer 3 DAG"),
    (5124, "Scott",   "TIDES: fix fct_tides_trips_performed"),
    (5126, "O'Brien", "Configure SFTP server"),
    (5128, "O'Brien", "Switch Littlepay to new SFTP cluster"),
    (5129, "Worf",    "Update JupyterHub to latest stable release"),
    (5130, "LaForge", "Update littlepay sync to use new SFTP"),
    (5131, "LaForge", "Remove Composer 3 pin for apache-airflow-providers-goog"),
    (5132, "LaForge", "Remove stale Composer 2 GCS policies"),
    (5135, "O'Brien", "Remove pre-v3 archiver service account"),
    (5136, "Worf",    "Scale up JupyterHub node pool"),
    (5139, "LaForge", "Remove calitp-archiver-service-account"),
    (5141, "LaForge", "Composer 3: add missing GCS bucket"),
    (5143, "LaForge", "Re-parse OCTA GTFS-RT data"),
    (5145, "Spock",   "Fix failing tests"),
    (5148, "LaForge", "Add Elavon SFTP GCS bucket"),
    (5150, "LaForge", "Fix littlepay sync schedule"),
    (5151, "Sulu",    "Add deployment for Elavon SFTP server"),
    (5152, "LaForge", "Add Elavon SFTP Airflow connection"),
    (5153, "Sulu",    "Add Elavon static IP to allowlist"),
    (5154, "LaForge", "Add Elavon SFTP DAG"),
    (5162, "Bashir",  "Split dbt run and dbt compile into separate CI jobs"),
    (5164, "Ro",      "Fix Metabase sync to include all schemas"),
    (5172, "Spock",   "Migrate GTFS RT tables to microbatch"),
    (5175, "Crusher", "mart_gtfs: add operator summary aggregation"),
    (5178, "Spock",   "Update incremental model documentation"),
    (5179, "LaForge", "Unify Littlepay sync workflows"),
    (5182, "Uhura",   "Add Airtable webhook DAG"),
    (5184, "Rand",    "Add TIDES parse operator"),
    (5194, "Worf",    "Update Kubernetes patch targets"),
    (5206, "Rand",    "Add Enghouse agencies to Elavon"),
    (5209, "Worf",    "Fix patch target scope"),
    (5212, "Rand",    "Add Enghouse agencies to fct_payments"),
    (5216, "Data",    "Create fct_tides_vehicle_locations"),
    (5220, "Data",    "Create fct_tides_trips_performed"),
    (5223, "Rand",    "Re-add full_refresh tag after migration"),
    (5227, "O'Brien", "Tune GTFS-RT archiver k8s resources"),
    (5229, "Data",    "Create TIDES publish-side mart"),
    (5232, "LaForge", "Clean up deprecated Littlepay workflow files"),
    (5237, "O'Brien", "Scale down node pool floor"),
    (5239, "LaForge", "Remove Littlepay legacy sync workflow"),
    (5241, "Ro",      "Fix Dependabot skip logic in Metabase sync"),
    (5245, "Worf",    "Helm chart cleanup"),
    (5249, "LaForge", "Migrate GTFS Schedule to Composer 3"),
    (5256, "Ro",      "Fix dbt-metabase sync --include-schemas flag"),
    (5262, "O'Brien", "Downgrade GCS bucket IAM permissions"),
    (5265, "LaForge", "Add calitp-gtfs-schedule-raw bucket"),
    (5273, "LaForge", "Deploy dbt workflow updates"),
    (5281, "Worf",    "Add JupyterHub restore runbook"),
    (5284, "Rand",    "Add TIDES schema documentation"),
    (5287, "Data",    "Add SCD Type 2 seed joins to TIDES mart"),
    (5295, "LaForge", "Migrate remaining GTFS RT tables to microbatch"),
    (5297, "Rand",    "Add HubSpot email automation"),
    (5302, "Rand",    "Update CODEOWNERS for TIDES"),
    (5306, "O'Brien", "Add Cloud SQL database for TIDES"),
    (5307, "LaForge", "Add TIDES outcomes operator"),
    (5313, "Sulu",    "Add Composer 3 Terraform for Elavon"),
    (5318, "Crusher", "Add flex service hours rollup"),
    (5320, "LaForge", "Migrate Payments to Composer 3"),
    (5333, "Chekov",  "Scale node pool floors to 0"),
    (5334, "Spock",   "Migrate GTFS Schedule fact tables to microbatch"),
    (5339, "Chekov",  "Increase heartbeat frequency for staging Composer 3"),
    (5340, "Chekov",  "Revert heartbeat frequency change for staging"),
    (5341, "Data",    "Create Outcomes table for TIDES Audit Dashboard"),
    (5343, "Spock",   "Remove broken dbt visualization, fix duplicate exposure"),
    (5346, "Ro",      "Skip Metabase sync job on Dependabot PRs"),
    (5347, "O'Brien", "Add IAM groups Payments_Admins and Warehouse_Users"),
    (5348, "Crusher", "Propagate service_hours/flex_service_hours consistently"),
    (5349, "Scott",   "Revert urllib3<2.0 pin that breaks Composer 3 staging"),
    (5350, "Scott",   "Add CALITP_BUCKET__TIDES to composer3 staging env"),
    (5351, "O'Brien", "Switch calitp-tides bucket to public requester pays"),
    (5359, "O'Brien", "Add calitp-tides-site to host a static TIDES page"),
]

# Real Phase 1 extraction output for PR #5220 (anonymized)
PHASE1_DEMO_PR = {
    "pr_number": 5220,
    "patterns": [
        {
            "signal": "Deduplication logic must be scoped within a feed partition, not globally across feeds, to avoid arbitrarily dropping valid rows",
            "category": "grain",
            "maturity": "rule",
            "standard_citation": "Kimball dimensional modeling — grain must be defined precisely; cross-feed row elimination violates declared grain",
            "comment_evidence": [
                "This should only dedupe within a given feed (VP URL or VP GTFS dataset), don't dedupe across feeds. There is no reason to expect that trip ID performed should be unique across feeds and dropping like this will result in trips basically arbitrarily missing from some feeds just because they used the same trip_id."
            ],
            "author": "Data",
            "reviewer": "Spock"
        },
        {
            "signal": "Incremental models not partitioned on `dt` must use warehouse ranged-date macros to support historical re-runs",
            "category": "modeling",
            "maturity": "rule",
            "standard_citation": "Internal warehouse policy per PR #5092 and dt-vs-service_date materialization policy (issue #4865)",
            "comment_evidence": [
                "Since `fct_observed_trips` is not partitioned on `dt`, this should use our incremental ranged date macros as shown here: PR #5092, so that it can have historical periods re-run in accordance with other models."
            ],
            "author": "Data",
            "reviewer": "Spock"
        },
        {
            "signal": "Organization metadata should not be materialized in mart fact tables when it belongs on the publish side",
            "category": "modeling",
            "maturity": "guidance",
            "standard_citation": "Kimball — dimension attributes should not leak into fact tables; publish-layer separation pattern",
            "comment_evidence": [
                "Dropping organization_name / organization_ntd_id from this table too — orgs aren't part of the TIDES spec; metadata moves to publish-side in PR #5229."
            ],
            "author": "Data",
            "reviewer": "Spock"
        },
        {
            "signal": "Downstream product models should be declared as dbt exposures in YAML, not as ordinary model meta blocks",
            "category": "schema",
            "maturity": "convention",
            "standard_citation": "dbt docs: exposures (exposure: block in schema.yml) are the project standard for published/product-facing models",
            "comment_evidence": [
                "Good call, exposure is the right shape. Dropping the publish.product meta in this PR. Adding a single california_tides exposure so both fct model refs resolve in the same checkout."
            ],
            "author": "Data",
            "reviewer": "Spock"
        }
    ],
    "author_signals": {
        "login": "Data",
        "strengths": ["Strong domain knowledge — accurately applies GTFS-RT spec to conditional logic"],
        "growth_areas": ["Incremental model strategy — submitted without microbatch despite dt-partitioned parent"],
        "description_quality": "high"
    },
    "reviewer_signals": [
        {
            "login": "Spock",
            "focus_this_pr": ["grain", "modeling", "schema"],
            "high_signal_comments": 6
        }
    ]
}

# Spock's reviewer fingerprint (abbreviated from real synthesis output)
SPOCK_FINGERPRINT = {
    "reviewer": "Spock",
    "review_style": "thorough",
    "signal_quality": "high",
    "prs_reviewed": 40,
    "primary_focus_areas": [
        {"area": "Incremental model strategy — microbatch for dt-partitioned sources, ranged-date macros for non-partitioned", "frequency": "often"},
        {"area": "Deduplication logic correctness — partition scoped within feed, not across feeds", "frequency": "often"},
        {"area": "dbt exposures for published models — flags non-standard meta tags", "frequency": "often"},
        {"area": "Documentation clarity — prerequisite links, external table lifecycle, broken references", "frequency": "often"},
        {"area": "SCD Type 2 correctness — valid_to/valid_from range joins, not _is_current flags", "frequency": "sometimes"}
    ],
    "apparent_blind_spots": [
        {
            "area": "dbt schema test coverage (uniqueness, not_null, referential integrity) on new models",
            "basis": "Across 40 PRs including multiple new mart models, no comments requesting dbt tests in .yml files"
        },
        {
            "area": "Column-level documentation in .yml files",
            "basis": "No comments requesting column descriptions despite multiple new models introduced"
        }
    ]
}

# Top 3 team gaps (real output, anonymized)
TOP_GAPS = [
    {
        "area": "LGTM approvals on high-risk SQL changes — no inline technical scrutiny",
        "gap_type": "coverage_gap",
        "standard_citation": "The Checklist Manifesto: breaking changes warrant checklist-driven review",
        "recommendation": "Add a PR checklist for fct_ model changes requiring explicit sign-off on: join logic, grain definition, filter correctness, and downstream impact. Gate merge on at least one inline technical comment for any PR touching fct_ models."
    },
    {
        "area": "dbt model config review — materialization strategy, incremental strategy, unique_key correctness",
        "gap_type": "blind_spot",
        "standard_citation": "dbt Labs style guide: incremental models require explicit unique_key and incremental_strategy",
        "recommendation": "Add CI gate using dbt-project-evaluator checks. Include materialization/incremental strategy as a mandatory checklist item for any PR touching model configs."
    },
    {
        "area": "Rollback plan and success criteria before merging live pipeline changes",
        "gap_type": "knowledge_gap",
        "standard_citation": "The Checklist Manifesto: define rollback criteria and monitoring thresholds before merging",
        "recommendation": "Create a 'data pipeline change' PR template with required fields: success criteria, rollback procedure, monitoring thresholds. Treat 'merge and watch' as non-compliant."
    }
]


# ── Cost probe data (real run, cal-itp/data-infra, June 2026) ─────────────────
# Per-PR rows: (number, author, reviews, inline_comments, desc_quality, iterations, input_tokens)
# Source: tricorder-cost-probe-cal-itp__data-infra.json
COST_PROBE_ROWS = [
    (4491, "O'Brien",  1, 0, "high", 0,  871),
    (4537, "O'Brien",  2, 0, "high", 0, 1043),
    (4570, "Rand",     2, 4, "high", 1, 2187),
    (4673, "LaForge",  2, 0, "high", 0,  714),
    (4677, "O'Brien",  1, 0, "high", 0,  803),
    (4759, "LaForge",  2, 0, "high", 0,  768),
    (4828, "Spock",    2, 2, "high", 0, 1356),
    (4850, "Worf",     1, 0, "high", 0,  692),
    (4856, "Chekov",   1, 1, "high", 0,  941),
    (4857, "Crusher",  2, 3, "high", 0, 1612),
    (4858, "LaForge",  1, 0, "high", 0,  703),
    (4860, "Spock",    1, 2, "high", 0, 1289),
    (4863, "Spock",    2, 1, "high", 1, 1487),
    (4867, "O'Brien",  1, 0, "high", 0,  611),
    (4870, "LaForge",  1, 0, "high", 0,  738),
    (4875, "O'Brien",  1, 0, "high", 0,  694),
    (4876, "O'Brien",  1, 0, "high", 0,  661),
    (4888, "Chekov",   1, 0, "high", 0,  809),
    (4889, "Spock",    2, 4, "high", 1, 1974),
    (4891, "LaForge",  1, 0, "high", 0,  626),
]

# ── Helpers ────────────────────────────────────────────────────────────────────

import json

def print_json_slow(obj, indent=2):
    """Print JSON with a slight delay per line for readability."""
    lines = json.dumps(obj, indent=indent).splitlines()
    for line in lines:
        # Color keys cyan, strings green
        colored = line
        if not FAST:
            time.sleep(0.04)
        print(colored)

def print_json(obj, indent=2):
    lines = json.dumps(obj, indent=indent).splitlines()
    for line in lines:
        if not FAST:
            time.sleep(0.015)
        print(line)


# ── Scene 0: Header ────────────────────────────────────────────────────────────

def scene_header():
    p()
    p(f"{BOLD}{'─'*65}{RST}")
    p(f"{BOLD}  tricorder  ·  cal-itp/data-infra  ·  demo run{RST}")
    p(f"{DIM}  190 PRs  ·  Mar–May 2026  ·  15 contributors{RST}")
    p(f"{BOLD}{'─'*65}{RST}")
    p()
    sleep(0.6)
    dim("  Note: contributor names are anonymized (Star Trek aliases).")
    dim("  Real→alias map: ~/.tricorder/cal-itp__data-infra-name-map.json")
    p()
    sleep(1.0)


# ── Scene 0: Cost probe ───────────────────────────────────────────────────────

def scene_cost_probe():
    header("COST PROBE  ·  before we spend anything")
    p()
    slowprint(f"  {DIM}$ {RST}python tricorder-cost-probe.py cal-itp/data-infra --limit 20")
    p()
    sleep(0.4)
    dim("  Fetching merged PRs…")
    sleep(0.6)
    print(f"  Found 20 merged PRs. Fetching reviews + comments…")
    p()
    sleep(0.3)

    # Per-PR table header
    print(f"  {DIM}{'PR':>5}  {'Author':<12}  {'Rev':>3}  {'Inl':>3}  {'Desc':>4}  {'Iter':>4}  {'Input tok':>9}{RST}")
    print(f"  {DIM}{'─'*5}  {'─'*12}  {'─'*3}  {'─'*3}  {'─'*4}  {'─'*4}  {'─'*9}{RST}")

    for num, author, rev, inl, desc, itr, tok in COST_PROBE_ROWS:
        flag = f" {YLW}⚠{RST}" if itr >= 1 else "  "
        print(f"  {num:>5}  {CYN}{author:<12}{RST}  {rev:>3}  {inl:>3}  "
              f"{desc:>4}  {itr:>4}{flag}  {tok:>9,}")
        if not FAST:
            time.sleep(0.14)

    p()
    dim("  ⚠ = review required changes before approval (high-signal PR)")
    p()
    sleep(0.4)

    # Summary stats
    HR = f"  {'─'*62}"
    print(HR)
    print(f"  {BOLD}COST PROBE RESULTS — cal-itp/data-infra{RST}")
    print(HR)
    p()

    if not FAST:
        time.sleep(0.3)

    print(f"  {DIM}SAMPLE STATS  (20 PRs){RST}")
    label("Avg review comments/PR:", "1.1")
    label("Avg inline comments/PR:", "0.1")
    label("Avg input tokens/PR:",    "954")
    label("Desc quality —",          "high: 20  medium: 0  low: 0")
    p()
    sleep(0.3)

    print(f"  {DIM}TOKEN BREAKDOWN{RST}")
    label("Prompt 1 — per-PR extraction:", "")
    label("  Input:",                "  19,080")
    label("  Output (est):",         "   6,000")
    label("Prompts 2–4 — aggregation (×1.5):", "")
    label("  Input:",                "  28,617")
    label("  Output (est):",         "   3,000")
    label("Grand total input:",      "  47,697")
    label("Grand total output:",     "   9,000")
    p()
    sleep(0.3)

    print(f"  {DIM}COST  (claude-sonnet-4-6 · $3/M input · $15/M output){RST}")
    label("This sample (20 PRs):", f"  {GRN}$0.28{RST}")
    label("Per PR:",               f"  {GRN}$0.014{RST}")
    p()
    sleep(0.3)

    print(f"  {DIM}EXTRAPOLATIONS{RST}")
    print(f"  {DIM}{'Window':>8}   {'Est PRs':>8}   {'Cost':>8}   Notes{RST}")
    print(f"  {DIM}{'─'*8}   {'─'*8}   {'─'*8}   {'─'*28}{RST}")

    rows = [
        ( 30,  "$0.42",  "1 month, quiet team"),
        ( 60,  "$0.83",  "2 months, recommended first run"),
        ( 90,  "$1.25",  "3 months, standard window"),
        (150,  "$2.09",  "5 months, rich signal"),
        (300,  "$4.17",  "heavy repo, 6–12 months"),
    ]
    for est_prs, cost, note in rows:
        if not FAST:
            time.sleep(0.12)
        print(f"  {est_prs:>8}   {est_prs:>8}   {GRN}{cost:>8}{RST}   {DIM}{note}{RST}")

    p()
    print(HR)
    p()
    sleep(0.4)

    pause("COST PROBE — narrate: no Claude API spend yet. This pulls real PRs from GitHub, "
          "assembles the exact prompts, counts tokens, and projects cost. "
          "$0.014 per PR. 190 PRs → $2.85. "
          "That's the go / no-go number. We said go.")


# ── Scene 1: Harvest ───────────────────────────────────────────────────────────

def scene_harvest():
    header("HARVEST  ·  pulling merged PRs from GitHub API")
    p()
    slowprint(f"  {DIM}$ {RST}tricorder harvest cal-itp/data-infra --since 2026-03-01")
    p()
    sleep(0.5)
    dim("  Connecting to GitHub API...")
    sleep(0.4)
    dim("  Cache: ~/.learn-from-work/cache/cal-itp__data-infra/")
    sleep(0.3)
    p()

    # Fast-scroll all 190 PRs
    for i, (num, author, title) in enumerate(ALL_PRS):
        bar = f"[{i+1:>3}/{len(ALL_PRS)}]"
        line = f"  {DIM}{bar}{RST}  #{num}  {CYN}{author:<10}{RST}  {title}"
        print(line)
        delay = 0.025 if not FAST else 0
        if i < 5:
            delay = 0.12  # slightly slower at start so audience registers what they're seeing
        if i > len(ALL_PRS) - 4:
            delay = 0.12  # slow down at end
        if not FAST:
            time.sleep(delay)

    p()
    sleep(0.3)
    p(f"  {BOLD}Harvest complete.{RST}")
    p()
    label("PRs fetched:",        f"{len(ALL_PRS)}  (18 skipped — no review activity)")
    label("Contributors:",       "15")
    label("Window:",             "2026-03-02 → 2026-05-30  (89 days)")
    label("Cache location:",     "~/.learn-from-work/cache/cal-itp__data-infra/")
    label("Cache size:",         "~4.1 MB  (prs/ + comments/ + reviews/ + repo-context)")
    label("GitHub API spend:",   "$0.00")
    p()

    pause("HARVEST DONE — narrate: 190 PRs, every review thread, 4MB of JSON on disk. "
          "The cache is permanent and incremental — re-harvest only fetches new PRs. "
          "Now synthesize.")


# ── Scene 2: Synthesis setup ──────────────────────────────────────────────────

def scene_synth_start():
    header("SYNTHESIZE  ·  4 Claude API calls: PR extraction → reviewer fingerprints → author profiles → team gaps")
    p()
    slowprint(f"  {DIM}$ {RST}tricorder synthesize cal-itp/data-infra --visibility private")
    p()
    sleep(0.5)
    dim("  Loading cache...")
    sleep(0.3)
    dim("  Model: claude-sonnet-4-6")
    sleep(0.2)
    dim("  Estimated cost: ~$2.85  (190 PRs × $0.015)")
    p()
    sleep(0.4)


# ── Scene 3: Phase 1 — per-PR extraction ─────────────────────────────────────

def scene_phase1():
    p(f"{BOLD}Phase 1 — Per-PR pattern extraction{RST}  {DIM}(one call per PR){RST}")
    p()
    sleep(0.4)

    # Show the system prompt briefly
    dim("  System prompt (abbreviated):")
    p()
    prompt_lines = [
        '  """',
        "  You are an expert analytics engineer reviewing a dbt/SQL pull request.",
        "  Extract structured learning signals from the PR description and review threads.",
        "",
        "  For each pattern you identify, return:",
        "    - signal: concise description of the pattern",
        "    - category: one of [grain, naming, testing, documentation, style,",
        "                        performance, modeling, schema, business-logic]",
        "    - maturity: one of [judgment, guidance, convention, rule, deterministic]",
        "    - standard_citation: named standard if applicable (dbt Labs style guide,",
        "                         Kimball, SQLFluff, dbt-project-evaluator, etc.)",
        "    - comment_evidence: direct quotes from review comments",
        "",
        "  Return JSON only. No markdown fences.",
        '  """',
    ]
    for line in prompt_lines:
        if not FAST:
            time.sleep(0.04)
        print(f"{DIM}{line}{RST}")

    p()
    sleep(0.5)

    # Process first few PRs slowly to establish the pattern
    early_prs = [
        (4860, "Spock",   "Fix: add feed_version to Payments joins to dedupe"),
        (4863, "Spock",   "feat: microbatch strategy for dim stop arrivals"),
        (4894, "Spock",   "dim_stop_times microbatch (#4866)"),
    ]
    for num, author, title in early_prs:
        sleep(0.3)
        print(f"  {DIM}[  →  ]{RST}  #{num}  {CYN}{author:<10}{RST}  {title}")
        sleep(0.5)
        print(f"  {GRN}[  ✓  ]{RST}  #{num}  {GRN}3 patterns{RST}  grain, modeling, schema")
        sleep(0.2)

    p()
    # Now show the full extraction for PR #5220 — the demo centrepiece
    pr = PHASE1_DEMO_PR
    print(f"  {DIM}[  →  ]{RST}  #{pr['pr_number']}  {CYN}{'Data':<10}{RST}  Create fct_tides_trips_performed")
    sleep(0.8 if not FAST else 0)
    print(f"  {GRN}[  ✓  ]{RST}  #{pr['pr_number']}  {GRN}{len(pr['patterns'])} patterns{RST}  grain, modeling ×2, schema")
    p()
    sleep(0.4)

    dim("  Extraction output for PR #5220:")
    p()
    print_json_slow(pr)
    p()

    pause("PHASE 1 DEMO PR — narrate: Claude received the PR description, the file paths, "
          "every review comment thread. Returned structured JSON in <2 seconds. "
          "Notice the evidence field — direct quotes. The maturity tag tells you what to do with it. "
          "'rule' means this is ready for CI enforcement. "
          "184 of these calls ran in parallel. Total Phase 1 time: ~25 minutes.")

    # Fast-scroll the remaining PRs
    p(f"  {DIM}... processing remaining 181 PRs ...{RST}")
    p()

    remaining = [pr for pr in ALL_PRS if pr[0] not in (4860, 4863, 4894, 5220)]
    for i, (num, author, title) in enumerate(remaining[:30]):  # show 30 to suggest volume
        patterns_n = [3,2,4,2,3,1,5,2,3,2,4,3,2,1,3,2,4,2,3,5,2,3,1,4,2,3,2,1,3,2][i % 30]
        cats = ["grain,modeling","testing","modeling,schema","style","grain,naming","documentation",
                "modeling,grain,testing","schema","performance,modeling","testing,schema"][i % 10]
        line = f"  {GRN}[  ✓  ]{RST}  #{num}  {CYN}{author:<10}{RST}  {DIM}{patterns_n} patterns  {cats}{RST}"
        print(line)
        if not FAST:
            time.sleep(0.06)

    print(f"  {DIM}  ... 151 more ...{RST}")
    p()
    sleep(0.3)
    ok(f"Phase 1 complete — {BOLD}{len(ALL_PRS) - 18} PRs{RST} processed  |  18 skipped (no review activity)")
    p()
    label("Patterns extracted:", "~720 total across 184 PRs")
    label("Avg patterns/PR:",    "3.9")
    label("Top category:",       "modeling (31%)  →  grain (22%)  →  schema (18%)")
    p()
    sleep(0.5)


# ── Scene 4: Phase 2 — reviewer fingerprints ─────────────────────────────────

def scene_phase2():
    p(f"{BOLD}Phase 2 — Reviewer fingerprints{RST}  {DIM}(one call per reviewer, full review history){RST}")
    p()
    sleep(0.3)

    reviewers = [
        ("Spock",    40, "high",   "thorough"),
        ("Scott",    20, "low",    "conversational"),
        ("O'Brien",  24, "low",    "advisory"),
        ("LaForge",  41, "low",    "conversational"),
        ("Data",      3, "medium", "conversational"),
        ("Sulu",      5, "low",    "advisory"),
        ("Chekov",    5, "low",    "advisory"),
        ("Worf",      1, "low",    "advisory"),
        ("Rand",      3, "low",    "advisory"),
        ("LaForge",   4, "low",    "conversational"),
        ("Troi",      8, "low",    "advisory"),
        ("Uhura",     3, "low",    "conversational"),
        ("Bashir",    1, "low",    "advisory"),
        ("Crusher",   2, "low",    "advisory"),
    ]

    for name, prs, sig, style in reviewers:
        sig_color = GRN if sig == "high" else (YLW if sig == "medium" else DIM)
        line = f"  {CYN}{name:<12}{RST}  {DIM}{prs:>2} PRs reviewed{RST}  signal={sig_color}{sig}{RST}  style={DIM}{style}{RST}"
        print(line)
        if not FAST:
            time.sleep(0.25)

    p()
    sleep(0.4)
    dim("  Fingerprint output for Spock (40 PRs reviewed):")
    p()
    print_json_slow(SPOCK_FINGERPRINT)
    p()

    pause("REVIEWER FINGERPRINT — narrate: 40 PRs distilled into a fingerprint. "
          "Spock is the team's highest-signal reviewer — thorough, blocking, focused on "
          "incremental strategy and grain correctness. "
          "But look at the blind spots: no test coverage comments across 40 PRs. "
          "The team has one expert reviewer and 13 others at low signal. "
          "That's the coverage gap.")

    ok(f"Phase 2 complete — {BOLD}14 reviewer profiles{RST}")
    p()
    sleep(0.3)


# ── Scene 5: Phase 3 — author growth profiles ─────────────────────────────────

def scene_phase3():
    p(f"{BOLD}Phase 3 — Author growth profiles{RST}  {DIM}(one call per author, chronological PR history){RST}")
    p()
    sleep(0.3)

    authors = [
        ("Spock",    27, "improving"),
        ("Scott",    20, "stable"),
        ("O'Brien",  13, "improving"),
        ("LaForge",  50, "improving"),
        ("Data",      5, "improving"),
        ("Sulu",     13, "stable"),
        ("Chekov",    5, "stable"),
        ("Worf",     16, "stable"),
        ("Rand",     14, "improving"),
        ("Uhura",     5, "improving"),
        ("Bashir",    4, "improving"),
        ("Crusher",   4, "insufficient-data"),
        ("Troi",      1, "insufficient-data"),
        ("Ro",        5, "insufficient-data"),
        ("Guinan",    1, "insufficient-data"),
    ]

    for name, prs, traj in authors:
        traj_color = GRN if traj == "improving" else (YLW if traj == "stable" else DIM)
        line = f"  {CYN}{name:<12}{RST}  {DIM}{prs:>2} PRs{RST}  trajectory={traj_color}{traj}{RST}"
        print(line)
        if not FAST:
            time.sleep(0.18)

    p()
    ok(f"Phase 3 complete — {BOLD}15 author profiles{RST}  |  8 improving  ·  4 stable  ·  3 insufficient-data")
    p()
    sleep(0.4)


# ── Scene 6: Phase 4 — team gap analysis ─────────────────────────────────────

def scene_phase4():
    p(f"{BOLD}Phase 4 — Team gap analysis{RST}  {DIM}(one aggregate call — all patterns + all reviewer fingerprints){RST}")
    p()
    sleep(0.4)
    dim("  Aggregating 720 patterns + 14 reviewer fingerprints...")
    sleep(1.2 if not FAST else 0)
    dim("  Calling claude-sonnet-4-6  (max_tokens=8192)...")
    sleep(2.0 if not FAST else 0)
    p()

    print_json({"gap_count": 11, "institutionalization_candidates": 5,
                "team_strengths": 6, "review_culture_observations": 1})
    p()
    sleep(0.3)
    dim("  Top gaps (showing 3 of 11):")
    p()
    print_json_slow(TOP_GAPS)
    p()

    pause("TEAM GAPS — narrate: 11 gaps. Three types: coverage_gap means nobody is checking it. "
          "blind_spot means the whole team is unaware. knowledge_gap means they know it matters "
          "but don't have a shared process. "
          "The top finding: LGTM approvals on breaking SQL changes with no inline scrutiny. "
          "That's not a knowledge problem — it's a process problem. "
          "The fix is a PR template with a mandatory checklist, not a training session.")

    ok(f"Phase 4 complete — {BOLD}11 gaps{RST}  |  5 coverage  ·  4 blind spots  ·  2 knowledge")
    p()
    sleep(0.3)


# ── Scene 7: Report ────────────────────────────────────────────────────────────

def scene_report():
    p(f"{BOLD}Rendering Markdown report...{RST}")
    p()
    sleep(0.5)

    sections = [
        ("Institutionalization candidates", "5 patterns  (judgment → convention → rule → deterministic)"),
        ("Reviewer fingerprints",           "14 reviewers  (1 high-signal, 2 medium, 11 low)"),
        ("Author growth profiles",          "15 authors  (8 improving, 4 stable, 3 insufficient-data)"),
        ("Team gap analysis",               "11 gaps  +  6 team strengths  +  culture observation"),
        ("Methodology & caveats",           "window, skipped PRs, what this cannot see"),
        ("Reference standards",             "dbt Labs, dbt-project-evaluator, Kimball, SQLFluff, Google Eng Practices"),
    ]
    for section, detail in sections:
        if not FAST:
            time.sleep(0.15)
        print(f"  {GRN}✓{RST}  {section}")
        print(f"      {DIM}{detail}{RST}")

    p()
    sleep(0.3)
    out_path = "~/Documents/dev/adventures-in-ai/tricorder/2026-06-02-cal-itp__data-infra.md"
    print(f"  {BOLD}{GRN}Report written:{RST}  {out_path}")
    p()
    sleep(0.4)

    p(f"{BOLD}{'─'*65}{RST}")
    p(f"{BOLD}  Done.{RST}")
    p(f"{BOLD}{'─'*65}{RST}")
    p()
    label("Total PRs analyzed:",   f"{len(ALL_PRS) - 18}  ({len(ALL_PRS)} harvested, 18 skipped)")
    label("Synthesis cost:",        "~$2.85  (claude-sonnet-4-6, June 2026 pricing)")
    label("Synthesis runtime:",     "~28 minutes  (phases 1–4, sequential)")
    label("Explorer (live):",       "https://dhk.github.io/tricorder/explorer/")
    label("Full report (GitHub):", "github.com/dhk/adventures-in-ai/blob/main/tricorder/")
    p()


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        scene_header()
        scene_cost_probe()
        scene_harvest()
        scene_synth_start()
        scene_phase1()
        scene_phase2()
        scene_phase3()
        scene_phase4()
        scene_report()
    except KeyboardInterrupt:
        print(f"\n\n{DIM}  [demo interrupted]{RST}\n")
