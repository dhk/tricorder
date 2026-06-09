from tricorder.focus_areas import FocusArea

FOCUS = FocusArea(
    name="skills",
    system_context="""\
FOCUS AREA — SKILL DEFINITIONS:
You are specifically looking for patterns related to Claude Code skills (SKILL.md files),
skill trigger phrases, skill invocation patterns, and skill quality signals.
Flag: missing trigger phrases, vague skill descriptions, poor SKILL.md structure,
invocation anti-patterns, skill scope creep, and skill discoverability issues.
When a review comment touches skill files or skill-adjacent patterns, weight it heavily.
""",
    keyword_filters=[
        "skill", "SKILL.md", "trigger", "invoke", "invocation",
        "slash command", "/", "skill definition", "skill file",
    ],
)
