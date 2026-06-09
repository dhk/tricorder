from tricorder.focus_areas import FocusArea

FOCUS = FocusArea(
    name="security",
    system_context="""\
FOCUS AREA — SECURITY:
You are specifically looking for security-related review patterns:
authentication, authorization, injection vulnerabilities, secrets management,
dependency vulnerabilities, data exposure, input validation, and OWASP Top 10.
Flag: missing security review coverage, reviewers who never raise security concerns,
security issues caught late (after merge), and patterns that indicate security blind spots.
Weight security-adjacent comments heavily even if they are phrased as style feedback.
""",
    keyword_filters=[
        "security", "auth", "injection", "xss", "csrf", "secret", "token",
        "password", "permission", "access control", "vulnerability", "CVE",
        "sanitize", "validate", "exposure", "leak", "encrypt",
    ],
)
