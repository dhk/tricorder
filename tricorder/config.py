"""
tricorder config — central config loader and per-repo path resolver.

Config file: .tricorder/config.yml  (in cwd, or --tricorder-dir)
Global fallback: ~/.tricorder/config.yml

Schema:
  llm:
    provider: anthropic | gemini
    model: optional model override
  output:
    dir: ~/reports/tricorder   # default --out dir
  reviewer_deny: [login, ...]
  reviewer_allow: [login, ...]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


_SENTINEL = object()


def _load_yaml(path: Path) -> dict:
    try:
        import yaml  # type: ignore
        return yaml.safe_load(path.read_text()) or {}
    except ImportError:
        # Fallback: minimal key: value parser (no nesting)
        result: dict = {}
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                k, _, v = line.partition(":")
                result[k.strip()] = v.strip()
        return result
    except Exception:
        return {}


def load_config(tricorder_dir: Path | None = None) -> dict:
    """Load config from .tricorder/config.yml, falling back to ~/.tricorder/config.yml."""
    base = tricorder_dir or (Path.cwd() / ".tricorder")
    local = base / "config.yml"
    global_ = Path.home() / ".tricorder" / "config.yml"

    cfg: dict = {}
    if global_.exists():
        cfg = _deep_merge(cfg, _load_yaml(global_))
    if local.exists():
        cfg = _deep_merge(cfg, _load_yaml(local))
    return cfg


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def get(cfg: dict, *keys: str, default: Any = None) -> Any:
    node = cfg
    for k in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(k, _SENTINEL)
        if node is _SENTINEL:
            return default
    return node


def repo_dir(tricorder_dir: Path, repo_slug: str) -> Path:
    """Return the per-repo subdirectory inside .tricorder/."""
    safe = repo_slug.replace("/", "__")
    return tricorder_dir / safe


def set_current_repo(tricorder_dir: Path, repo_slug: str) -> None:
    """Persist current_repo to .tricorder/config.yml after a successful analyze."""
    config_path = tricorder_dir / "config.yml"
    tricorder_dir.mkdir(parents=True, exist_ok=True)

    # Read existing content as raw text to preserve comments
    existing = config_path.read_text() if config_path.exists() else ""

    if "current_repo:" in existing:
        import re
        updated = re.sub(r"^current_repo:.*$", f"current_repo: {repo_slug}", existing, flags=re.MULTILINE)
        config_path.write_text(updated)
    else:
        config_path.write_text(f"current_repo: {repo_slug}\n" + existing)


def resolve_repo(tri_base: Path, cli_repo: str | None, git_remote_fn) -> tuple[str | None, str]:
    """
    Resolve the repo slug from: CLI arg → git remote → config current_repo.
    Returns (slug, source) where source is one of: 'arg', 'git', 'config'.
    """
    if cli_repo:
        return cli_repo, "arg"

    remote = git_remote_fn()
    if remote:
        return remote, "git"

    cfg = load_config(tri_base)
    current = get(cfg, "current_repo")
    if current:
        return current, "config"

    return None, "none"


def write_default_config(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("""\
# tricorder config
# https://github.com/dhk/tricorder

llm:
  provider: anthropic       # anthropic | gemini
  # model: claude-sonnet-4-5  # uncomment to pin a model

output:
  # dir: ~/reports/tricorder  # default --out directory for markdown reports

# Reviewer filter (applied during `tricorder analyze`)
# reviewer_deny: []   # logins to always exclude
# reviewer_allow: []  # if set, only these logins are included
""")
