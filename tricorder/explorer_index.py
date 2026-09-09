"""The explorer's data index: one entry per rendered repository.

The explorer page loads ``data/index.js`` first, then the data file named by
``?repo=<slug>`` in the URL, falling back to the index default. Both the
legacy render script and ``tricorder build`` call :func:`update_index` after
writing a data file so the page and the files on disk never disagree.

Files, both under ``explorer/data/``:

- ``index.json`` — source of truth, edited only through this module
- ``index.js``   — ``window.TRICORDER_INDEX = {...};`` for the page
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

INDEX_JSON = "index.json"
INDEX_JS = "index.js"


def slug_for(repo: str) -> str:
    """``owner/name`` -> ``owner__name`` (the cache and data-file naming)."""
    return repo.replace("/", "__")


def data_path(explorer_dir: Path, repo: str) -> Path:
    return explorer_dir / "data" / f"{slug_for(repo)}.js"


def load_index(explorer_dir: Path) -> dict:
    p = explorer_dir / "data" / INDEX_JSON
    if p.exists():
        idx = json.loads(p.read_text())
    else:
        idx = {}
    idx.setdefault("default", None)
    idx.setdefault("entries", [])
    return idx


def update_index(explorer_dir: Path, entry: dict, *, make_default: bool = False) -> dict:
    """Upsert ``entry`` (keyed by ``slug``) and rewrite index.json and index.js.

    The first entry ever written becomes the default; after that the default
    changes only with ``make_default``. Entries stay sorted by repo name so
    the picker order is stable across renders.
    """
    if "slug" not in entry:
        entry = {**entry, "slug": slug_for(entry["repo"])}
    entry = {**entry, "rendered": entry.get("rendered") or datetime.now().strftime("%Y-%m-%d %H:%M")}
    idx = load_index(explorer_dir)
    idx["entries"] = [e for e in idx["entries"] if e.get("slug") != entry["slug"]] + [entry]
    idx["entries"].sort(key=lambda e: e.get("repo", ""))
    if make_default or not idx["default"] or idx["default"] not in {e["slug"] for e in idx["entries"]}:
        idx["default"] = entry["slug"]
    write_index(explorer_dir, idx)
    return idx


def write_index(explorer_dir: Path, idx: dict) -> None:
    d = explorer_dir / "data"
    d.mkdir(parents=True, exist_ok=True)
    (d / INDEX_JSON).write_text(json.dumps(idx, indent=2) + "\n")
    (d / INDEX_JS).write_text(
        "// tricorder — explorer data index. Generated; edit through tricorder.explorer_index.\n"
        "window.TRICORDER_INDEX = " + json.dumps(idx, indent=2) + ";\n"
    )
