"""Lens-keyed synthesis cache.

Phase outputs are produced under one lens's prompts and category enum, so they
are only valid for that lens. The cache directory is therefore keyed by lens
name and version, every cached file is stamped with the lens that produced it,
and a stamped file from a different lens is never loaded.

Layout (legacy cache and v2 ``.raw/`` alike)::

    <root>/synthesis/
      current.json                      -> which sub-directory the last run used
      product-engineering-desktop-v1/   -> pr/, reviewers/, authors/, team-gaps.json, lens.json
      analytics-engineering-v2/

A pre-existing flat layout (``<root>/synthesis/pr`` directly) is moved into a
sub-directory on first use: named from its ``lens.json`` when present, else
``pre-lens`` so it is kept for reference but never reused.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tricorder.lenses import Lens

FLAT_ENTRIES = ("pr", "reviewers", "authors", "team-gaps.json", "lens.json")
PRE_LENS_KEY = "pre-lens"


def lens_key(lens: Lens | dict) -> str:
    if isinstance(lens, dict):
        return f"{lens.get('name', 'unknown')}-v{lens.get('version', 1)}"
    return f"{lens.name}-v{lens.version}"


def migrate_flat(root: Path) -> str | None:
    """Move a flat ``root/pr`` layout into a keyed sub-directory. Returns the key used, or None."""
    root = Path(root)
    if not (root / "pr").is_dir():
        return None
    info = {}
    lens_file = root / "lens.json"
    if lens_file.exists():
        try:
            info = json.loads(lens_file.read_text())
        except Exception:
            info = {}
    key = lens_key(info) if info.get("name") else PRE_LENS_KEY
    target = root / key
    if target.exists():
        # never clobber; park the flat layout under a timestamp instead
        key = f"{key}-flat-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        target = root / key
    target.mkdir(parents=True)
    for name in FLAT_ENTRIES:
        src = root / name
        if src.exists():
            shutil.move(str(src), str(target / name))
    # any other loose team-gaps-*.json / ai-diff files travel too
    for extra in list(root.glob("team-gaps-*.json")) + list(root.glob("ai-diff*.json")):
        shutil.move(str(extra), str(target / extra.name))
    if info.get("name") and not (root / "current.json").exists():
        (root / "current.json").write_text(json.dumps(
            {"lens_key": key, **{k: info.get(k) for k in ("name", "version", "status", "archetype")},
             "updated_at": datetime.now(timezone.utc).isoformat(), "migrated_from_flat_layout": True}, indent=2))
    return key


def synthesis_dir(root: Path, lens: Lens, create: bool = True) -> Path:
    """The cache directory for this lens under ``root`` (``.../synthesis``), migrating a flat layout first."""
    root = Path(root)
    moved = migrate_flat(root)
    if moved:
        print(f"  Moved pre-existing synthesis cache into synthesis/{moved}/ (cache is now keyed by lens)")
    d = root / lens_key(lens)
    if create:
        for sub in ("pr", "reviewers", "authors"):
            (d / sub).mkdir(parents=True, exist_ok=True)
    return d


def write_current(root: Path, lens: Lens, extra: dict | None = None) -> None:
    Path(root).mkdir(parents=True, exist_ok=True)
    doc = {"lens_key": lens_key(lens), **lens.summary(),
           "updated_at": datetime.now(timezone.utc).isoformat()}
    if extra:
        doc.update(extra)
    (Path(root) / "current.json").write_text(json.dumps(doc, indent=2))


def read_current(root: Path) -> dict | None:
    p = Path(root) / "current.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def current_dir(root: Path) -> Path | None:
    """Directory of the most recent run, or the flat layout for caches that predate keying."""
    root = Path(root)
    cur = read_current(root)
    if cur and (root / cur.get("lens_key", "")).is_dir():
        return root / cur["lens_key"]
    if (root / "pr").is_dir():
        return root
    return None


def stamp(obj: dict, lens: Lens) -> dict:
    obj["_lens"] = {"name": lens.name, "version": lens.version}
    return obj


def load_cached(path: Path, lens: Lens) -> dict | None:
    """A cached phase output, or None if absent, errored, or produced under a different lens."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text())
    except Exception:
        return None
    if not isinstance(obj, dict) or obj.get("_error"):
        return None
    st = obj.get("_lens")
    if st and (st.get("name") != lens.name or int(st.get("version", 1)) != lens.version):
        return None
    return obj


def save_cached(path: Path, obj: dict, lens: Lens) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stamp(obj, lens), indent=2))
