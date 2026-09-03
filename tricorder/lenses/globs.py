"""Glob matching for lens detection signals and file tags.

Rules (documented in docs/research/repo-lens/handoff-prompt.md and DESIGN.md):

- A pattern containing ``/`` is matched against the full repo-relative path.
  ``**`` matches zero or more directory segments; ``*`` and ``?`` never cross ``/``.
- A pattern without ``/`` that contains a wildcard (``*.sql``, ``Chart.yam?``)
  is matched against the basename at any depth.
- A pattern without ``/`` and without wildcards (``package.json``) matches only
  at the repository root. Write ``**/Dockerfile`` to match at any depth.
"""

from __future__ import annotations

import re
from functools import lru_cache


def normalize(path: str) -> str:
    """Drop a leading ``./`` or ``/`` without touching dotfiles."""
    p = path.strip()
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def _segment_to_regex(seg: str) -> str:
    out = []
    for ch in seg:
        if ch == "*":
            out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(ch))
    return "".join(out)


@lru_cache(maxsize=4096)
def compile_glob(pattern: str) -> re.Pattern:
    pattern = normalize(pattern)
    has_wild = any(c in pattern for c in "*?")
    if "/" not in pattern:
        if not has_wild:
            return re.compile("^" + re.escape(pattern) + "$")
        # basename match at any depth
        return re.compile("^(?:.*/)?" + _segment_to_regex(pattern) + "$")

    parts = pattern.split("/")
    regex = ["^"]
    for i, seg in enumerate(parts):
        last = i == len(parts) - 1
        if seg == "**":
            regex.append(".*" if last else "(?:.*/)?")
        else:
            regex.append(_segment_to_regex(seg))
            if not last:
                regex.append("/")
    regex.append("$")
    return re.compile("".join(regex))


def glob_match(pattern: str, path: str) -> bool:
    return bool(compile_glob(pattern).match(normalize(path)))


def any_match(pattern: str, paths) -> bool:
    rx = compile_glob(pattern)
    return any(rx.match(normalize(p)) for p in paths)
