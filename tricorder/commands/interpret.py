"""
tricorder interpret — Level 4

Reads Level 3 artifacts and applies a discipline lens.
The lens provides domain-specific interpretation: which standards apply,
which authorities to cite, how to read the patterns for this repo type.

Writes: .tricorder/interpretations.json

Requires: LLM API key. Reads learnings.json from Level 3.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_TOKENS = 4096

VALID_LENSES = {
    "analytics-engineering",
    "agent-engineering",
    "product-engineering",
    "platform-engineering",
    "security",
}

# ---------------------------------------------------------------------------
# Lens definitions — authorities, standards, and framing per domain
# ---------------------------------------------------------------------------

LENS_CONTEXT: dict[str, str] = {
    "analytics-engineering": """\
Lens: analytics-engineering
Domain: dbt, SQL, data modeling, analytics pipelines (BigQuery / Snowflake / Redshift)

Authoritative standards for this lens:
- dbt Labs style guide — https://docs.getdbt.com/best-practices/how-we-style/0-how-we-style-our-dbt-projects
- dbt-project-evaluator check catalog — https://github.com/dbt-labs/dbt-project-evaluator
- SQLFluff rule catalog — https://docs.sqlfluff.com/en/stable/rules.html
- Kimball dimensional modeling techniques — https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/
- dbt Labs best practices: testing — https://docs.getdbt.com/best-practices/writing-custom-generic-tests

Key interpretation axes for analytics engineering:
- Grain clarity: is the grain of each model explicitly declared or inferable?
- Test coverage: are uniqueness, not-null, and FK tests present on key columns?
- Naming conventions: stagng/int/mart prefixes, snake_case, no reserved words
- Source freshness: are freshness thresholds configured?
- Incremental model safety: is_incremental() blocks, full-refresh safety
- Exposure contracts: are final mart models exposed and contracted?
- Documentation: model + column descriptions in schema.yml
- Macro complexity: are macros testable and documented?
- CI gate coverage: what is enforced by SQLFluff / dbt-project-evaluator vs. left to judgment?""",

    "product-engineering": """\
Lens: product-engineering
Domain: product software — web apps, APIs, mobile, backend services

Authoritative standards for this lens:
- Google Engineering Practices — https://google.github.io/eng-practices/review/
- DORA metrics — https://dora.dev/research/
- The Pragmatic Programmer (Hunt & Thomas)
- Clean Code (Martin)
- Accelerate (Forsgren, Humble, Kim)

Key interpretation axes for product engineering:
- Test coverage: unit, integration, and contract tests present?
- API contract stability: breaking changes flagged and versioned?
- Error handling: errors surfaced and handled explicitly?
- Observability: logging, tracing, and alerting hooks present?
- Security hygiene: secrets management, input validation, auth checks?
- Dependency management: pinned versions, supply chain awareness?
- Documentation: README, ADRs, inline docs for non-obvious decisions?
- PR hygiene: scope, description quality, linked issues?""",

    "platform-engineering": """\
Lens: platform-engineering
Domain: infrastructure, SRE, IaC, Kubernetes, CI/CD platforms

Authoritative standards for this lens:
- Google SRE book — https://sre.google/sre-book/table-of-contents/
- DORA metrics — https://dora.dev/research/
- AWS Well-Architected Framework — https://aws.amazon.com/architecture/well-architected/
- Terraform best practices — https://developer.hashicorp.com/terraform/language/style
- CIS Benchmarks

Key interpretation axes for platform engineering:
- Immutability: are resources defined declaratively and reproducible?
- Blast radius: are changes scoped to minimize failure domain?
- Observability: are SLOs, alerts, and runbooks referenced?
- Security posture: IAM least-privilege, secrets management, network policy?
- Change management: rollback plan, canary/blue-green patterns?
- Toil reduction: is manual work being automated or eliminated?
- Documentation: runbooks, architecture diagrams, incident playbooks?""",

    "security": """\
Lens: security
Domain: security engineering, appsec, infrastructure security

Authoritative standards for this lens:
- OWASP Top 10 — https://owasp.org/www-project-top-ten/
- NIST Cybersecurity Framework — https://www.nist.gov/cyberframework
- CIS Controls — https://www.cisecurity.org/controls
- OWASP ASVS — https://owasp.org/www-project-application-security-verification-standard/

Key interpretation axes for security:
- Input validation: all user inputs validated and sanitized?
- Authentication and authorization: authz checks present and tested?
- Secrets management: no secrets in code, proper rotation patterns?
- Dependency vulnerabilities: known CVEs tracked and remediated?
- Logging and audit trail: security-relevant events logged?
- Least privilege: permissions scoped to minimum required?
- Threat modeling: is threat surface considered in design decisions?""",

    "agent-engineering": """\
Lens: agent-engineering
Domain: AI agent systems, skills/plugins, MCP servers, agentic pipelines, LLM-backed tools

Authoritative standards for this lens:
- Anthropic model documentation and prompt engineering guide — https://docs.anthropic.com
- Model Context Protocol specification — https://modelcontextprotocol.io/docs
- OpenAI Cookbook — agent and tool-use patterns — https://cookbook.openai.com
- "Building Effective Agents" (Anthropic) — https://www.anthropic.com/research/building-effective-agents
- Anthropic Claude Code SDK documentation — https://docs.anthropic.com/en/docs/claude-code/sdk
- OWASP LLM Top 10 — https://owasp.org/www-project-top-10-for-large-language-model-applications/

Key interpretation axes for agent engineering:
- Prompt quality: are system prompts clear, scoped, and explicit about output format?
  Do they specify what the agent should NOT do as well as what it should?
- Tool/skill design: are tool descriptions precise enough for a model to select them correctly?
  Are tool names unambiguous? Are parameters typed and documented?
- Context discipline: what goes into the context window and why?
  Are irrelevant details trimmed? Is context window pressure managed explicitly?
- Agentic loop safety: are stop conditions defined? Is there a max-iteration guard?
  Is escalation to human-in-the-loop handled?
- Error handling: do agents fail loudly and informatively, or silently?
  Are tool call failures caught and surfaced?
- Evaluation / evals: is there a test harness for agent behavior?
  Are golden traces or golden outputs defined?
- Observability: are agent decisions logged? Are tool calls and responses traced?
  Can a failure be replayed and debugged?
- Safety and guardrails: is there explicit handling for prompt injection, jailbreak attempts,
  and adversarial inputs? Are outputs validated before acting on them?
- Skill / plugin composability: are skills isolated and independently testable?
  Do they have clear input/output contracts?
- MCP server design (if present): are resources, tools, and prompts correctly separated?
  Are tool descriptions optimized for model selection? Is auth handled correctly?
- Model selection rationale: is the choice of model (Opus/Sonnet/Haiku or equivalent) justified
  by the task complexity and latency requirements?
- Prompt caching: are long, stable system prompts cached to reduce cost and latency?""",
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_INTERPRET = """\
You are a domain expert applying a discipline lens to a team's code review learnings.

You have been given:
1. The team's extracted patterns and gaps (from code review analysis)
2. A discipline lens with domain-specific standards and interpretation axes

Your job:
- Map each significant pattern and gap to the most relevant standard or authority for this lens
- Identify which gaps are highest priority for THIS domain (not generically)
- Identify which patterns are already well-aligned with domain best practices
- Identify which domain best practices are MISSING from the review record entirely
  (not just blind spots, but things this lens says are critical and the team never discusses)
- Produce prioritized, domain-specific recommendations

Be specific. Cite the exact standard or document. "Use dbt-project-evaluator fct_missing_primary_key_tests" is useful.
"Improve testing" is not.

Respond ONLY with valid JSON. No preamble. No markdown fences.

OUTPUT SCHEMA:
{
  "lens": "lens-name",
  "standard_mappings": [
    {
      "pattern_or_gap": "description of the pattern or gap from learnings",
      "standard": "specific standard or rule name",
      "authority": "source document or framework",
      "authority_url": "url or null",
      "alignment": "well-aligned | needs-work | missing",
      "priority": "high | medium | low",
      "recommendation": "specific, actionable next step"
    }
  ],
  "domain_blind_spots": [
    {
      "practice": "best practice name",
      "authority": "source",
      "why_critical": "why this matters for this domain",
      "suggested_action": "how to address it"
    }
  ],
  "quick_wins": [
    {
      "action": "specific action",
      "effort": "low | medium",
      "impact": "high | medium",
      "rationale": "one sentence"
    }
  ],
  "lens_summary": "2-3 sentences: how well does this team's review practice align with domain standards, and what is the single most important thing to improve?"
}"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _call_llm(client: Any, system: str, user: str, retries: int = 2) -> dict:
    for attempt in range(retries + 1):
        try:
            text = _strip_fences(client.generate(system, user, MAX_TOKENS))
            return json.loads(text)
        except json.JSONDecodeError as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
            else:
                return {"_error": f"JSON parse failed: {e}", "_raw": text[:500]}
        except Exception as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
            else:
                return {"_error": str(e)}
    return {"_error": "unknown"}


def _load_lens_from_profile(tri_dir: Path) -> str | None:
    profile_path = tri_dir / "repository-profile.yml"
    if not profile_path.exists():
        return None
    try:
        import yaml
        profile = yaml.safe_load(profile_path.read_text())
        return profile.get("lens", {}).get("selected")
    except Exception:
        return None


def _infer_repo_from_remote() -> str | None:
    import subprocess
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        url = result.stdout.strip()
        for prefix in ("git@github.com:", "https://github.com/", "http://github.com/"):
            if url.startswith(prefix):
                slug = url[len(prefix):].removesuffix(".git")
                if "/" in slug:
                    return slug
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Status block
# ---------------------------------------------------------------------------

def _print_status(repo: str, lens: str, out_dir: Path, result: dict) -> None:
    n_mappings = len(result.get("standard_mappings", []))
    n_blind = len(result.get("domain_blind_spots", []))
    n_wins = len(result.get("quick_wins", []))
    summary = result.get("lens_summary", "")

    print()
    print("Tricorder — Lens Interpretation")
    print()
    print("Access used")
    print(f"  ✓ LLM API  (Level 3 artifacts + {lens} lens)")
    print(f"  — No GitHub API calls")
    print()
    print("Completed")
    print(f"  ✓ Interpretations  → {out_dir}/interpretations.json")
    print()
    print("Findings")
    print(f"  Lens:              {lens}")
    print(f"  Standard mappings: {n_mappings}")
    print(f"  Domain blind spots: {n_blind}")
    print(f"  Quick wins:        {n_wins}")
    if summary:
        print()
        # Wrap the summary at ~72 chars
        words = summary.split()
        line = "  "
        for word in words:
            if len(line) + len(word) + 1 > 74:
                print(line)
                line = "  " + word + " "
            else:
                line += word + " "
        if line.strip():
            print(line)
    print()
    print("Not yet unlocked")
    print("  ○ Improvement Plan  →  tricorder improve")
    print()
    print("Next")
    if repo:
        print(f"  tricorder improve {repo}")
    else:
        print(f"  tricorder improve")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(args: list[str]) -> int:
    import argparse
    from tricorder.llm import build_llm_provider

    parser = argparse.ArgumentParser(
        prog="tricorder interpret",
        description="Level 4: apply a discipline lens to Level 3 learnings.",
    )
    parser.add_argument("repo", nargs="?", default=None,
                        help="OWNER/REPO (default: inferred from git remote)")
    parser.add_argument("--lens", default=None, metavar="NAME",
                        help=f"Discipline lens to apply. Choices: {', '.join(sorted(VALID_LENSES))}. "
                             "Default: read from repository-profile.yml (set by discover).")
    parser.add_argument("--provider", choices=["anthropic", "gemini"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--api-key-env", dest="api_key_env", default=None)
    parser.add_argument("--tricorder-dir", default=None, metavar="DIR",
                        help="Path to .tricorder/ directory (default: .tricorder/ in cwd)")

    parsed = parser.parse_args(args)

    repo = parsed.repo or _infer_repo_from_remote()

    tri_dir = Path(parsed.tricorder_dir).expanduser().resolve() if parsed.tricorder_dir \
        else Path.cwd() / ".tricorder"

    # Require Level 3 artifacts
    learnings_path = tri_dir / "learnings.json"
    if not learnings_path.exists():
        print(f"learnings.json not found in {tri_dir}", file=sys.stderr)
        print("Run tricorder learn first.", file=sys.stderr)
        return 1

    # Resolve lens
    lens = parsed.lens
    if lens and lens not in VALID_LENSES:
        print(f"Unknown lens '{lens}'. Valid options: {', '.join(sorted(VALID_LENSES))}", file=sys.stderr)
        return 1

    if not lens:
        lens = _load_lens_from_profile(tri_dir)

    if not lens or lens == "unknown":
        print("No lens selected and none detected from repository-profile.yml.", file=sys.stderr)
        print(f"Run `tricorder discover` first, or pass --lens <name>.", file=sys.stderr)
        print(f"Available lenses: {', '.join(sorted(VALID_LENSES))}", file=sys.stderr)
        return 1

    if lens not in VALID_LENSES:
        print(f"Lens '{lens}' detected but not yet fully designed.", file=sys.stderr)
        print(f"Proceeding with generic interpretation. Override with --lens <name>.", file=sys.stderr)

    # Load Level 3 artifacts
    learnings = json.loads(learnings_path.read_text())
    standards_path = tri_dir / "standards-candidates.json"
    standards = json.loads(standards_path.read_text()) if standards_path.exists() else {}

    # Build LLM client
    client = build_llm_provider(
        provider=parsed.provider,
        model=parsed.model,
        api_key_env=parsed.api_key_env,
    )

    print(f"\ntricorder interpret — {repo or '(local)'}")
    print(f"  Lens:    {lens}")
    print(f"  LLM:     {client.config.provider} / {client.config.model}")
    print()

    # Build user prompt
    lens_ctx = LENS_CONTEXT.get(lens, f"Lens: {lens}\n(No specific context defined for this lens.)")

    user_lines = [
        lens_ctx,
        "",
        "--- TEAM LEARNINGS ---",
        "",
        f"Pattern count: {learnings.get('pattern_count', 0)}",
        f"Reviewer profiles: {len(learnings.get('reviewer_profiles', []))}",
        f"Author profiles: {len(learnings.get('author_profiles', []))}",
        "",
        "Patterns:",
        json.dumps(learnings.get("patterns", [])[:60], indent=2)[:6000],
        "",
        "Team gaps:",
        json.dumps(learnings.get("gaps", []), indent=2)[:3000],
        "",
        "Team strengths:",
        json.dumps(learnings.get("team_strengths", []), indent=2)[:2000],
        "",
        "Institutionalization candidates:",
        json.dumps(standards.get("candidates", []), indent=2)[:2000],
        "",
        "Review culture observations:",
        learnings.get("review_culture_observations", "(none)"),
    ]

    print("Running lens interpretation …", flush=True)
    result = _call_llm(client, SYSTEM_INTERPRET, "\n".join(user_lines))

    if result.get("_error"):
        print(f"LLM error: {result['_error']}", file=sys.stderr)
        raw = result.get("_raw", "")
        if raw:
            print(f"Raw output: {raw[:300]}", file=sys.stderr)
        return 1

    # Stamp metadata
    result["lens"] = lens
    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["tricorder_level"] = 4

    (tri_dir / "interpretations.json").write_text(json.dumps(result, indent=2))

    _print_status(repo or "", lens, tri_dir, result)
    return 0
