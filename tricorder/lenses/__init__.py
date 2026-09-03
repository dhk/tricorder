"""Discipline lenses as data.

A lens is a YAML file (see ``data/*.yaml`` and
docs/research/repo-lens/handoff-prompt.md, Part 4) that carries everything the
pipeline needs to interpret one kind of repository: detection signals, file
tags, pattern categories, cited authorities, interpretation axes, per-phase
prompt context, prohibitions, and validation checks.

Lookup order: repo-local ``.tricorder/lenses/``, then ``~/.tricorder/lenses/``,
then the lenses shipped in this package. A later directory never overrides an
earlier one; the first file whose ``lens.name`` matches wins.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

from tricorder.lenses.globs import glob_match

DATA_DIR = Path(__file__).parent / "data"
USER_LENS_DIR = Path.home() / ".tricorder" / "lenses"

MATURITY_LEVELS = ("judgment", "guidance", "convention", "rule", "deterministic")
STATUSES = ("experimental", "validated")
PHASES = ("phase1_pr_extraction", "phase2_reviewer_fingerprint",
          "phase3_author_growth", "phase4_team_gaps", "interpret")
PROMPT_CONTEXT_MAX_WORDS = 220

# Colour family per core category (explorer convention: pattern=green,
# tool=purple, data=blue, team=orange). Domain-specific categories default to
# ``data`` unless the lens sets ``group`` on the category.
CORE_CATEGORY_GROUP = {
    "correctness": "pattern", "security": "tool", "testing": "tool",
    "documentation": "pattern", "style": "pattern", "performance": "data",
    "error-handling": "pattern", "maintainability": "pattern",
    "dependencies": "tool", "other": "pattern",
}

DEFAULT_MIN_SCORE = 10
DEFAULT_MIN_MARGIN = 5
DEFAULT_REVIEW_PATH_SHARE = 0.7
DEFAULT_UNEXPECTED_LANGUAGE_SHARE = 0.05


class LensError(Exception):
    """A lens file failed to load or validate."""


@dataclass
class Lens:
    raw: dict[str, Any]
    source: Path | None = None
    _tag_rules: list[tuple[str, str]] = field(default_factory=list, repr=False)

    # -- identity ---------------------------------------------------------
    @property
    def name(self) -> str:
        return self.raw["name"]

    @property
    def version(self) -> int:
        return int(self.raw.get("version", 1))

    @property
    def status(self) -> str:
        return self.raw.get("status", "experimental")

    @property
    def extends(self) -> str | None:
        return self.raw.get("extends")

    @property
    def archetype(self) -> str:
        """Top-level archetype: the parent lens if this is a sub-profile."""
        return self.extends or self.name

    @property
    def domain(self) -> str:
        return (self.raw.get("domain") or "").strip()

    # -- detection --------------------------------------------------------
    @property
    def detection(self) -> dict[str, Any]:
        return self.raw.get("detection") or {}

    @property
    def signals(self) -> list[dict]:
        return list(self.detection.get("signals") or [])

    @property
    def counter_signals(self) -> list[dict]:
        return list(self.detection.get("counter_signals") or [])

    @property
    def ignore_for_detection(self) -> list[str]:
        return list(self.detection.get("ignore_for_detection") or [])

    @property
    def min_score(self) -> int:
        return int(self.detection.get("min_score", DEFAULT_MIN_SCORE))

    @property
    def min_margin(self) -> int:
        return int(self.detection.get("min_margin", DEFAULT_MIN_MARGIN))

    @property
    def languages_expected(self) -> list[str]:
        return list((self.detection.get("composition_check") or {}).get("languages_expected") or [])

    @property
    def languages_unexpected(self) -> list[str]:
        return list((self.detection.get("composition_check") or {}).get("languages_unexpected") or [])

    @property
    def review_path_share(self) -> float:
        rp = self.detection.get("review_path_check") or {}
        return float(rp.get("min_share_of_comments_on_tagged_paths", DEFAULT_REVIEW_PATH_SHARE))

    # -- taxonomy ---------------------------------------------------------
    @property
    def file_tags(self) -> list[dict]:
        return list(self.raw.get("file_tags") or [])

    def file_tag(self, path: str) -> str:
        """First matching file tag, or ``other``."""
        if not path:
            return "other"
        for glob, tag in self._tag_rules:
            if glob_match(glob, path):
                return tag
        return "other"

    @property
    def categories(self) -> list[dict]:
        return list(self.raw.get("categories") or [])

    @property
    def category_ids(self) -> list[str]:
        return [c["id"] for c in self.categories]

    @property
    def core_category_ids(self) -> list[str]:
        return [c["id"] for c in self.categories if c.get("core")]

    def category_group(self, cat_id: str) -> str:
        for c in self.categories:
            if c["id"] == cat_id:
                if c.get("group"):
                    return c["group"]
                return CORE_CATEGORY_GROUP.get(cat_id, "pattern" if c.get("core") else "data")
        return "pattern"

    @property
    def authorities(self) -> list[dict]:
        return list(self.raw.get("authorities") or [])

    @property
    def axes(self) -> list[dict]:
        return list(self.raw.get("axes") or [])

    @property
    def tooling_gates(self) -> list[dict]:
        return list(self.raw.get("tooling_gates") or [])

    def prompt_context(self, phase: str) -> str:
        return ((self.raw.get("prompt_context") or {}).get(phase) or "").strip()

    @property
    def must_not(self) -> list[str]:
        return list(self.raw.get("must_not") or [])

    @property
    def validation(self) -> dict[str, Any]:
        return self.raw.get("validation") or {}

    @property
    def smoke_checks(self) -> list[str]:
        return list(self.validation.get("smoke_checks") or [])

    def summary(self) -> dict[str, Any]:
        """Small dict stamped into artifacts."""
        return {"name": self.name, "version": self.version, "status": self.status,
                "archetype": self.archetype}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

REQUIRED_TOP = ("name", "version", "status", "domain", "detection", "file_tags",
                "categories", "authorities", "axes", "prompt_context", "must_not")


def validate(raw: dict[str, Any]) -> list[str]:
    """Return a list of problems (empty means valid)."""
    errs: list[str] = []
    if not isinstance(raw, dict):
        return ["lens document is not a mapping"]
    for k in REQUIRED_TOP:
        if k not in raw:
            errs.append(f"missing required key: {k}")
    if errs:
        return errs

    name = raw["name"]
    if not isinstance(name, str) or name != name.lower() or " " in name:
        errs.append(f"name must be kebab-case: {name!r}")
    if raw["status"] not in STATUSES:
        errs.append(f"status must be one of {STATUSES}: {raw['status']!r}")

    det = raw["detection"] or {}
    if not det.get("signals"):
        errs.append("detection.signals must list at least one signal")
    for s in det.get("signals") or []:
        if "pattern" not in s or "weight" not in s:
            errs.append(f"signal missing pattern/weight: {s}")
        elif int(s["weight"]) <= 0:
            errs.append(f"signal weight must be positive: {s['pattern']}")
    for s in det.get("counter_signals") or []:
        if "pattern" not in s or "weight" not in s:
            errs.append(f"counter_signal missing pattern/weight: {s}")
        elif int(s["weight"]) >= 0:
            errs.append(f"counter_signal weight must be negative: {s['pattern']}")

    cats = raw["categories"] or []
    cat_ids = [c.get("id") for c in cats]
    if not cats:
        errs.append("categories must not be empty")
    if len(set(cat_ids)) != len(cat_ids):
        errs.append("duplicate category ids")
    if "other" not in cat_ids:
        errs.append("categories must include 'other'")
    for c in cats:
        if not c.get("description"):
            errs.append(f"category {c.get('id')} has no description")
        if not c.get("example_comment"):
            errs.append(f"category {c.get('id')} has no example_comment")

    auth_ids = [a.get("id") for a in raw["authorities"] or []]
    if len(set(auth_ids)) != len(auth_ids):
        errs.append("duplicate authority ids")
    for a in raw["authorities"] or []:
        for k in ("id", "name", "url", "kind"):
            if not a.get(k):
                errs.append(f"authority {a.get('id')} missing {k}")
        if a.get("kind") not in ("primary", "secondary"):
            errs.append(f"authority {a.get('id')} kind must be primary|secondary")
        for c in a.get("covers") or []:
            if c not in cat_ids:
                errs.append(f"authority {a.get('id')} covers unknown category {c!r}")

    axis_ids = [x.get("id") for x in raw["axes"] or []]
    if len(set(axis_ids)) != len(axis_ids):
        errs.append("duplicate axis ids")
    for x in raw["axes"] or []:
        if not x.get("question"):
            errs.append(f"axis {x.get('id')} has no question")
        if not x.get("categories"):
            errs.append(f"axis {x.get('id')} references no categories")
        if not x.get("authorities"):
            errs.append(f"axis {x.get('id')} references no authorities")
        for c in x.get("categories") or []:
            if c not in cat_ids:
                errs.append(f"axis {x.get('id')} -> unknown category {c!r}")
        for a in x.get("authorities") or []:
            if a not in auth_ids:
                errs.append(f"axis {x.get('id')} -> unknown authority {a!r}")
        mm = x.get("max_maturity")
        if mm and mm not in MATURITY_LEVELS:
            errs.append(f"axis {x.get('id')} max_maturity not in {MATURITY_LEVELS}: {mm!r}")
    for c in cats:
        for ax in c.get("axes") or []:
            if ax not in axis_ids:
                errs.append(f"category {c.get('id')} -> unknown axis {ax!r}")

    for g in raw.get("tooling_gates") or []:
        if not g.get("tool") or not g.get("config_file"):
            errs.append(f"tooling gate missing tool/config_file: {g}")
        for c in g.get("enforces") or []:
            if c not in cat_ids:
                errs.append(f"tooling gate {g.get('tool')} enforces unknown category {c!r}")

    pc = raw["prompt_context"] or {}
    for phase in PHASES:
        text = pc.get(phase)
        if not text:
            errs.append(f"prompt_context.{phase} missing")
        elif len(str(text).split()) > PROMPT_CONTEXT_MAX_WORDS:
            errs.append(f"prompt_context.{phase} exceeds {PROMPT_CONTEXT_MAX_WORDS} words")

    for t in raw.get("file_tags") or []:
        if not t.get("glob") or not t.get("tag"):
            errs.append(f"file_tag missing glob/tag: {t}")

    if raw["status"] == "validated" and not (raw.get("validation") or {}).get("test_repo"):
        errs.append("a validated lens must name validation.test_repo")
    return errs


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _read_lens_file(path: Path) -> Lens:
    try:
        doc = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise LensError(f"{path}: invalid YAML: {e}") from e
    raw = doc.get("lens") if isinstance(doc, dict) else None
    if raw is None:
        raise LensError(f"{path}: top-level key 'lens' missing")
    problems = validate(raw)
    if problems:
        raise LensError(f"{path}: " + "; ".join(problems))
    lens = Lens(raw=raw, source=path)
    lens._tag_rules = [(t["glob"], t["tag"]) for t in lens.file_tags]
    return lens


def lens_dirs(extra_dirs: Iterable[Path | str] = ()) -> list[Path]:
    dirs: list[Path] = [Path(d) for d in extra_dirs]
    env = os.environ.get("TRICORDER_LENS_DIR")
    if env:
        dirs.append(Path(env))
    dirs.append(USER_LENS_DIR)
    dirs.append(DATA_DIR)
    seen: set[Path] = set()
    out: list[Path] = []
    for d in dirs:
        d = d.expanduser()
        if d in seen or not d.is_dir():
            continue
        seen.add(d)
        out.append(d)
    return out


def load_all(extra_dirs: Iterable[Path | str] = ()) -> dict[str, Lens]:
    """All lenses by name; earlier directories shadow later ones."""
    lenses: dict[str, Lens] = {}
    for d in lens_dirs(extra_dirs):
        for path in sorted(d.glob("*.yaml")) + sorted(d.glob("*.yml")):
            lens = _read_lens_file(path)
            lenses.setdefault(lens.name, lens)
    return lenses


def list_names(extra_dirs: Iterable[Path | str] = ()) -> list[str]:
    return sorted(load_all(extra_dirs))


def load_lens(name: str, extra_dirs: Iterable[Path | str] = ()) -> Lens:
    lenses = load_all(extra_dirs)
    if name not in lenses:
        raise LensError(f"Unknown lens {name!r}. Available: {', '.join(sorted(lenses))}")
    return lenses[name]


def load_lens_file(path: Path | str) -> Lens:
    return _read_lens_file(Path(path))


def global_ignore_patterns(lenses: Iterable[Lens]) -> list[str]:
    """Union of every lens's ignore_for_detection list."""
    out: list[str] = []
    for lens in lenses:
        for p in lens.ignore_for_detection:
            if p not in out:
                out.append(p)
    return out
