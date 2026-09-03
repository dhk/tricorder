"""Unit tests for the lens package: loading, validation, globs, detection,
verification, and prompt assembly. No network, no LLM."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from tricorder.lenses import (
    DATA_DIR, LensError, load_all, load_lens, load_lens_file, validate,
)
from tricorder.lenses.detect import (
    composition_check, confidence_label, detect, review_path_check,
)
from tricorder.lenses.globs import glob_match
from tricorder.lenses.prompting import smoke_check, system_prompt, interpret_context


# Fingerprint of block/berd as collected 2026-09-02 (docs/research/repo-lens/handoff-prompt.md Part 3)
BERD_PATHS = [
    ".agents/skills/code-review/SKILL.md", ".github/workflows/ci.yml",
    ".github/PULL_REQUEST_TEMPLATE.md", "AGENTS.md", "CHANGELOG.md", "CLAUDE.md",
    "CODEOWNERS", "CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "DESIGN.md", "GOVERNANCE.md",
    "LAWS/README.md", "LICENSE", "PRODUCT.md", "README.md", "SECURITY.md", "TELEMETRY.md",
    "bb-cli/src/main.rs", "bin/stage-goosed.sh", "biome.json", "crates/acp/src/lib.rs",
    "distro/linux/build.sh", "docker/linux/Dockerfile", "docs/architecture.md",
    "index.html", "justfile", "lefthook.yml", "package.json", "playwright.config.ts",
    "pnpm-lock.yaml", "pnpm-workspace.yaml", "postcss.config.js", "public/icon.png",
    "renovate.json", "rust-toolchain.toml", "skills/buzz-handoff/SKILL.md",
    "src-tauri/Cargo.toml", "src-tauri/capabilities/default.json",
    "src-tauri/capabilities/session-window.json", "src-tauri/src/main.rs",
    "src-tauri/src/commands/fs.rs", "src-tauri/tauri.conf.json",
    "src-tauri/tauri.macos.conf.json", "src/App.tsx", "src/components/Chat.tsx",
    "src/lib/acp.ts", "src/styles/app.css", "tsconfig.json", "vite.config.ts",
    "vitest.config.ts", "tests/e2e/chat.spec.ts",
]
BERD_LANG_BYTES = {"TypeScript": 15308659, "Rust": 3781965, "JavaScript": 313787,
                   "PowerShell": 205723, "Shell": 173036, "CSS": 88839,
                   "Objective-C": 76479, "Swift": 28306, "HTML": 23999, "Python": 14831}
BERD_COMMENT_PATHS = (["src-tauri/src/x.rs"] * 168 + ["src/a.tsx"] * 131 + ["src/b.ts"] * 131
                      + ["bb-cli/src/main.rs"] * 26 + ["LAWS/one.md"] * 4
                      + ["scripts/build.sh"] * 4 + [".github/workflows/ci.yml"] * 2)

DBT_PATHS = [
    "README.md", "CLAUDE.md", "dbt_project.yml", ".sqlfluff", "profiles.yml",
    "packages.yml", "models/staging/stg_orders.sql", "models/staging/schema.yml",
    "models/marts/fct_orders.sql", "macros/cents_to_dollars.sql",
    "tests/assert_positive.sql", ".github/workflows/ci.yml", ".pre-commit-config.yaml",
    "scripts/load.py",
]
DBT_LANG_BYTES = {"SQL": 900000, "Python": 120000, "Shell": 4000}

BARE_PATHS = ["README.md", "LICENSE", "CLAUDE.md", "AGENTS.md", ".agents/skills/x/SKILL.md",
              "SECURITY.md", "notes.txt"]


class GlobTests(unittest.TestCase):
    def test_root_only_exact(self):
        self.assertTrue(glob_match("package.json", "package.json"))
        self.assertFalse(glob_match("package.json", "web/package.json"))

    def test_basename_wildcard_any_depth(self):
        self.assertTrue(glob_match("*.sql", "models/a/b.sql"))
        self.assertTrue(glob_match("*.sql", "b.sql"))
        self.assertFalse(glob_match("*.sql", "models/a/b.sqlx"))

    def test_dotfiles_survive_normalization(self):
        self.assertTrue(glob_match("**/.sqlfluff", ".sqlfluff"))
        self.assertTrue(glob_match(".sqlfluff", ".sqlfluff"))
        self.assertTrue(glob_match(".agents/**", "./.agents/skills/x/SKILL.md"))
        self.assertFalse(glob_match(".agents/**", "agents/x.py"))

    def test_double_star(self):
        self.assertTrue(glob_match("src-tauri/**/*.rs", "src-tauri/src/main.rs"))
        self.assertTrue(glob_match("src-tauri/**/*.rs", "src-tauri/main.rs"))
        self.assertTrue(glob_match("**/Dockerfile", "docker/linux/Dockerfile"))
        self.assertTrue(glob_match("**/Dockerfile", "Dockerfile"))
        self.assertTrue(glob_match(".agents/**", ".agents/skills/x/SKILL.md"))
        self.assertFalse(glob_match("src/**/*.tsx", "src-tauri/x.tsx"))

    def test_single_star_does_not_cross_slash(self):
        self.assertTrue(glob_match("src/*.ts", "src/a.ts"))
        self.assertFalse(glob_match("src/*.ts", "src/lib/a.ts"))


class LoaderTests(unittest.TestCase):
    def test_all_shipped_lenses_load(self):
        lenses = load_all()
        for name in ("analytics-engineering", "product-engineering", "product-engineering-desktop",
                     "platform-engineering", "security", "agent-engineering"):
            self.assertIn(name, lenses)
        desk = lenses["product-engineering-desktop"]
        self.assertEqual(desk.archetype, "product-engineering")
        self.assertEqual(len(desk.core_category_ids), 10)
        self.assertIn("other", desk.category_ids)

    def test_core_categories_identical_across_lenses(self):
        cores = {name: tuple(l.core_category_ids) for name, l in load_all().items()}
        self.assertEqual(len(set(cores.values())), 1, cores)

    def test_dangling_axis_category_fails(self):
        raw = copy.deepcopy(load_lens("product-engineering-desktop").raw)
        raw["axes"][0]["categories"] = ["no-such-category"]
        problems = validate(raw)
        self.assertTrue(any("no-such-category" in p for p in problems), problems)

    def test_missing_prompt_context_fails(self):
        raw = copy.deepcopy(load_lens("security").raw)
        del raw["prompt_context"]["phase4_team_gaps"]
        problems = validate(raw)
        self.assertTrue(any("phase4_team_gaps" in p for p in problems), problems)

    def test_lens_file_error_names_problem(self):
        raw = copy.deepcopy(load_lens("security").raw)
        raw["status"] = "gold"
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.yaml"
            p.write_text(yaml.safe_dump({"lens": raw}))
            with self.assertRaises(LensError) as ctx:
                load_lens_file(p)
            self.assertIn("status", str(ctx.exception))

    def test_repo_local_dir_shadows_package(self):
        raw = copy.deepcopy(load_lens("security").raw)
        raw["version"] = 99
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "security.yaml").write_text(yaml.safe_dump({"lens": raw}))
            self.assertEqual(load_lens("security", extra_dirs=[d]).version, 99)
        self.assertNotEqual(load_lens("security").version, 99)

    def test_file_tags_first_match_wins(self):
        desk = load_lens("product-engineering-desktop")
        self.assertEqual(desk.file_tag("src-tauri/capabilities/default.json"), "desktop-capabilities")
        self.assertEqual(desk.file_tag("src-tauri/src/main.rs"), "desktop-core-rust")
        self.assertEqual(desk.file_tag("src/App.tsx"), "ui-react")
        self.assertEqual(desk.file_tag("LAWS/one.md"), "docs")
        self.assertEqual(desk.file_tag("weird.bin"), "other")


class DetectionTests(unittest.TestCase):
    def test_berd_selects_desktop_with_margin(self):
        r = detect(BERD_PATHS)
        self.assertEqual(r.state, "selected", r.scores)
        self.assertEqual(r.selected, "product-engineering-desktop")
        self.assertGreaterEqual(r.scores["product-engineering-desktop"], 25)
        self.assertGreaterEqual(r.margin, 5)
        # the dbt lens is pushed negative by its counter-signals, never a contender
        self.assertLess(r.scores.get("analytics-engineering", 0), 0)
        # the AI-assistant files were ignored, not scored
        self.assertGreaterEqual(r.ignored_paths, 4)
        self.assertEqual(confidence_label(r), "high")
        gates = {g["tool"] for g in r.tooling_gates_present}
        self.assertIn("biome", gates)
        self.assertIn("lefthook", gates)
        self.assertNotIn("cargo-deny", gates)

    def test_agent_files_alone_do_not_select_agent_lens(self):
        r = detect(BARE_PATHS)
        self.assertEqual(r.state, "unknown")
        self.assertIsNone(r.selected)
        self.assertEqual(r.scores.get("agent-engineering", 0), 0)

    def test_dbt_repo_selects_analytics(self):
        r = detect(DBT_PATHS)
        self.assertEqual(r.selected, "analytics-engineering", r.scores)
        self.assertEqual(r.state, "selected")
        gates = {g["tool"] for g in r.tooling_gates_present}
        self.assertIn("sqlfluff", gates)

    def test_mixed_when_margin_thin(self):
        # a Tauri app that also carries a serious Terraform estate
        paths = BERD_PATHS + [f"infra/{i}.tf" for i in range(3)] + ["infra/prod.tfvars",
                                                                    "infra/helm/Chart.yaml", "infra/kustomization.yaml", "infra/Pulumi.yaml"]
        r = detect(paths)
        self.assertIn(r.state, ("mixed", "selected"))
        self.assertEqual(r.selected, "product-engineering-desktop")
        self.assertEqual(r.runner_up, "platform-engineering")
        self.assertTrue(r.details["platform-engineering"].score >= 20)


class VerificationTests(unittest.TestCase):
    def test_berd_passes_both_checks_under_desktop(self):
        desk = load_lens("product-engineering-desktop")
        c = composition_check(desk, BERD_LANG_BYTES)
        self.assertTrue(c.passed, c.detail)
        r = review_path_check(desk, BERD_COMMENT_PATHS)
        self.assertTrue(r.passed, r.detail)
        self.assertGreater(r.data["share"], 0.95)

    def test_berd_fails_composition_under_analytics(self):
        ana = load_lens("analytics-engineering")
        c = composition_check(ana, BERD_LANG_BYTES)
        self.assertFalse(c.passed, c.detail)
        self.assertIn("TypeScript", c.detail)

    def test_dbt_passes_under_analytics(self):
        ana = load_lens("analytics-engineering")
        self.assertTrue(composition_check(ana, DBT_LANG_BYTES).passed)
        r = review_path_check(ana, ["models/x.sql"] * 8 + ["README.md"] * 2)
        self.assertTrue(r.passed, r.detail)

    def test_no_data_is_skipped_not_failed(self):
        desk = load_lens("product-engineering-desktop")
        self.assertTrue(composition_check(desk, {}).passed)
        self.assertTrue(review_path_check(desk, []).passed)


class PromptTests(unittest.TestCase):
    def test_desktop_prompts_carry_lens_and_no_dbt(self):
        desk = load_lens("product-engineering-desktop")
        for phase in ("p1", "p2", "p3", "p4", "interpret"):
            sp = system_prompt(phase, desk, tooling_gates_present=[
                {"tool": "biome", "config_file": "biome.json", "enforces": ["style"]}])
            self.assertIn("LENS: product-engineering-desktop", sp)
            self.assertIn("MUST NOT", sp)
            self.assertNotIn("SQLFluff rule", sp)
            self.assertNotIn("Kimball dimensional", sp)
        p1 = system_prompt("p1", desk)
        self.assertIn("ipc-boundary", p1)
        self.assertIn("desktop-core-rust", p1)
        self.assertIn('"category": "correctness | security', p1)
        p4 = system_prompt("p4", desk, tooling_gates_present=[
            {"tool": "biome", "config_file": "biome.json", "enforces": ["style"]}])
        self.assertIn("TOOLING GATES present", p4)
        self.assertIn("absence from the review record is itself a blind_spot", p4)

    def test_analytics_prompt_still_cites_dbt(self):
        ana = load_lens("analytics-engineering")
        p4 = system_prompt("p4", ana)
        self.assertIn("dbt-project-evaluator", p4)
        self.assertIn("grain", p4)
        self.assertIn("Kimball", interpret_context(ana))

    def test_smoke_check_is_word_bounded(self):
        desk = load_lens("product-engineering-desktop")
        self.assertEqual(smoke_check(desk, {"gaps": [{"area": "no grain declaration"}]}), ["grain"])
        self.assertEqual(smoke_check(desk, "fine-grained permissions and technical debt"), [])
        self.assertIn("dbt", smoke_check(desk, "cite the dbt style guide"))
        self.assertEqual(smoke_check(desk, "capability scoping via tauri.conf.json"), [])


if __name__ == "__main__":
    unittest.main()
