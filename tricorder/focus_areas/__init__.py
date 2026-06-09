"""Focus area registry for tricorder learn --focus-on."""
from __future__ import annotations

from typing import NamedTuple


class FocusArea(NamedTuple):
    name: str
    system_context: str  # appended to each phase's system prompt
    keyword_filters: list[str]  # patterns → only keep if body matches any


def get(name: str) -> FocusArea | None:
    from tricorder.focus_areas import skills, security
    registry = {
        "skills": skills.FOCUS,
        "security": security.FOCUS,
    }
    return registry.get(name.lower())


def list_names() -> list[str]:
    return ["skills", "security"]
