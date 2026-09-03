"""Repository archetype detection and post-selection verification.

Detection is content-only: it takes a list of repo-relative paths (from a local
walk or the GitHub trees API) and scores every loaded lens from its signals
and counter-signals after dropping paths on the global ignore list. The
winner must clear its own ``min_score`` (else ``unknown``) and lead the
runner-up by ``min_margin`` (else ``mixed``). Lenses are never blended.

Two checks run after selection and before any paid phase:

- composition_check: observed language bytes against the lens's expected and
  unexpected languages.
- review_path_check: the share of inline review comments that fall on paths
  the lens can tag.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

from tricorder.lenses import (
    DEFAULT_MIN_MARGIN, DEFAULT_MIN_SCORE, DEFAULT_UNEXPECTED_LANGUAGE_SHARE,
    Lens, global_ignore_patterns, load_all,
)
from tricorder.lenses.globs import any_match, glob_match, normalize

# Extension -> language, used for local byte counting (Linguist-style, coarse).
EXT_LANGUAGE: dict[str, str] = {
    ".sql": "SQL", ".py": "Python", ".js": "JavaScript", ".mjs": "JavaScript",
    ".cjs": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".go": "Go", ".rb": "Ruby", ".java": "Java",
    ".tf": "HCL", ".tfvars": "HCL", ".rs": "Rust", ".sh": "Shell", ".bash": "Shell",
    ".zsh": "Shell", ".ps1": "PowerShell", ".swift": "Swift", ".m": "Objective-C",
    ".mm": "Objective-C", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".dart": "Dart", ".c": "C", ".h": "C", ".cpp": "C++", ".cc": "C++",
    ".hpp": "C++", ".cs": "C#", ".php": "PHP", ".css": "CSS", ".scss": "SCSS",
    ".html": "HTML", ".vue": "Vue", ".svelte": "Svelte", ".lua": "Lua",
    ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang", ".clj": "Clojure",
    ".r": "R", ".jl": "Julia", ".nix": "Nix", ".zig": "Zig",
}
# Linguist excludes data/prose languages from stats; we do the same.
NON_CODE_EXT = {".md", ".markdown", ".rst", ".txt", ".json", ".yml", ".yaml",
                ".toml", ".lock", ".csv", ".tsv", ".xml", ".svg", ".png", ".jpg",
                ".jpeg", ".gif", ".ico", ".pdf", ".woff", ".woff2", ".ttf"}
VENDORED_DIRS = {"node_modules", "vendor", "third_party", "dist", "build",
                 ".venv", "venv", "target", "__pycache__", ".git"}


@dataclass
class LensScore:
    name: str
    score: int = 0
    matched: list[dict] = field(default_factory=list)
    countered: list[dict] = field(default_factory=list)


@dataclass
class DetectionResult:
    state: str                      # selected | mixed | unknown
    selected: str | None
    runner_up: str | None
    margin: int
    scores: dict[str, int]
    details: dict[str, LensScore]
    min_score: int
    min_margin: int
    ignored_paths: int
    tooling_gates_present: list[dict] = field(default_factory=list)

    @property
    def archetype(self) -> str:
        return self.selected or "unknown"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["details"] = {k: asdict(v) for k, v in self.details.items()}
        return d


def filter_ignored(paths: Iterable[str], ignore: list[str]) -> tuple[list[str], int]:
    kept: list[str] = []
    dropped = 0
    for p in paths:
        p = normalize(p)
        if any(glob_match(pat, p) for pat in ignore):
            dropped += 1
        else:
            kept.append(p)
    return kept, dropped


def score_lens(lens: Lens, paths: list[str]) -> LensScore:
    ls = LensScore(name=lens.name)
    for sig in lens.signals:
        if any_match(sig["pattern"], paths):
            ls.score += int(sig["weight"])
            ls.matched.append({"pattern": sig["pattern"], "weight": int(sig["weight"])})
    for sig in lens.counter_signals:
        if any_match(sig["pattern"], paths):
            ls.score += int(sig["weight"])
            ls.countered.append({"pattern": sig["pattern"], "weight": int(sig["weight"])})
    return ls


def detect(paths: Iterable[str], lenses: dict[str, Lens] | None = None) -> DetectionResult:
    lenses = lenses if lenses is not None else load_all()
    all_paths = [normalize(p) for p in paths]
    kept, dropped = filter_ignored(all_paths, global_ignore_patterns(lenses.values()))

    details = {name: score_lens(lens, kept) for name, lens in lenses.items()}
    ranked = sorted(details.values(), key=lambda s: (-s.score, s.name))
    scores = {s.name: s.score for s in ranked}

    if not ranked or ranked[0].score <= 0:
        return DetectionResult("unknown", None, None, 0, scores, details,
                               DEFAULT_MIN_SCORE, DEFAULT_MIN_MARGIN, dropped)

    top = ranked[0]
    lens = lenses[top.name]
    second = ranked[1] if len(ranked) > 1 else None
    margin = top.score - (second.score if second else 0)
    runner = second.name if second and second.score > 0 else None

    if top.score < lens.min_score:
        state, selected = "unknown", None
    elif margin < lens.min_margin:
        state, selected = "mixed", top.name
    else:
        state, selected = "selected", top.name

    gates = []
    if selected:
        for g in lens.tooling_gates:
            if any_match(g["config_file"], all_paths):
                gates.append({"tool": g["tool"], "config_file": g["config_file"],
                              "enforces": list(g.get("enforces") or [])})

    return DetectionResult(state, selected, runner, margin, scores, details,
                           lens.min_score, lens.min_margin, dropped, gates)


# ---------------------------------------------------------------------------
# Path sources
# ---------------------------------------------------------------------------

def walk_local(root: Path) -> tuple[list[str], dict[str, int]]:
    """Repo-relative paths plus language byte counts (vendored dirs skipped)."""
    paths: list[str] = []
    lang_bytes: dict[str, int] = {}
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in VENDORED_DIRS]
        rel_dir = Path(dirpath).relative_to(root)
        for fname in filenames:
            rel = str(rel_dir / fname) if str(rel_dir) != "." else fname
            paths.append(rel)
            ext = Path(fname).suffix.lower()
            lang = EXT_LANGUAGE.get(ext)
            if lang and ext not in NON_CODE_EXT:
                try:
                    lang_bytes[lang] = lang_bytes.get(lang, 0) + (Path(dirpath) / fname).stat().st_size
                except OSError:
                    pass
    return paths, lang_bytes


def github_token() -> str | None:
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        return tok
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""),
             "-s", "github-tricorder-pat", "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def fetch_github(owner: str, repo: str, token: str | None = None) -> tuple[list[str], dict[str, int]]:
    """Paths from the default-branch tree plus GitHub's own language bytes."""
    import requests

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    base = f"https://api.github.com/repos/{owner}/{repo}"
    meta = requests.get(base, headers=headers, timeout=30)
    meta.raise_for_status()
    branch = meta.json().get("default_branch", "main")
    tree = requests.get(f"{base}/git/trees/{branch}?recursive=1", headers=headers, timeout=60)
    tree.raise_for_status()
    paths = [t["path"] for t in tree.json().get("tree", []) if t.get("type") == "blob"]
    langs = requests.get(f"{base}/languages", headers=headers, timeout=30)
    langs.raise_for_status()
    return paths, {k: int(v) for k, v in langs.json().items()}


# ---------------------------------------------------------------------------
# Post-selection verification
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


def composition_check(lens: Lens, language_bytes: dict[str, int]) -> CheckResult:
    total = sum(language_bytes.values()) or 0
    if total == 0:
        return CheckResult("composition_check", True, "no language bytes available; skipped",
                           {"skipped": True})
    shares = {k: v / total for k, v in language_bytes.items()}
    problems: list[str] = []
    for lang in lens.languages_unexpected:
        share = shares.get(lang, 0.0)
        if share > DEFAULT_UNEXPECTED_LANGUAGE_SHARE:
            problems.append(f"{lang} is {share:.0%} of bytes but the lens does not expect it")
    if lens.languages_expected:
        present = [l for l in lens.languages_expected if shares.get(l, 0.0) > 0]
        if not present:
            problems.append(f"none of the expected languages ({', '.join(lens.languages_expected)}) are present")
    top = sorted(shares.items(), key=lambda kv: -kv[1])[:5]
    detail = "; ".join(problems) if problems else "language mix consistent with lens"
    return CheckResult("composition_check", not problems, detail,
                       {"top_languages": [{"language": k, "share": round(v, 3)} for k, v in top]})


def review_path_check(lens: Lens, comment_paths: Iterable[str]) -> CheckResult:
    paths = [p for p in comment_paths if p]
    if not paths:
        return CheckResult("review_path_check", True, "no inline comment paths; skipped",
                           {"skipped": True})
    tagged = sum(1 for p in paths if lens.file_tag(p) != "other")
    share = tagged / len(paths)
    ok = share >= lens.review_path_share
    detail = (f"{tagged}/{len(paths)} inline comments ({share:.0%}) fall on paths the lens tags; "
              f"threshold {lens.review_path_share:.0%}")
    return CheckResult("review_path_check", ok, detail,
                       {"tagged": tagged, "total": len(paths), "share": round(share, 3)})


def verify(lens: Lens, language_bytes: dict[str, int] | None,
           comment_paths: Iterable[str] | None) -> list[CheckResult]:
    out = []
    if language_bytes is not None:
        out.append(composition_check(lens, language_bytes))
    if comment_paths is not None:
        out.append(review_path_check(lens, list(comment_paths)))
    return out


def confidence_label(result: DetectionResult) -> str:
    if result.state != "selected":
        return "low"
    if result.margin >= 2 * result.min_margin and result.scores.get(result.selected, 0) >= 2 * result.min_score:
        return "high"
    return "medium"
