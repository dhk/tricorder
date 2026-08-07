# Security policy

## Supported versions

Tricorder is under active development. Security fixes are applied to the current
default branch; older snapshots and legacy scripts do not receive separate support.

## Report a vulnerability privately

Do not open a public issue for suspected vulnerabilities, exposed credentials,
private review-data leaks, unsafe publication, or authorization bypasses. Use
[GitHub's private vulnerability reporting](https://github.com/dhk/tricorder/security/advisories/new)
for this repository. Include affected version/commit, impact, reproduction steps,
and suggested mitigation when available. Do not include real secrets or unrelated
private data; use redacted or synthetic evidence.

If private reporting is unavailable, contact the repository owner through a private
channel listed on their GitHub profile and disclose only enough to establish a safe
reporting path.

## Credential and data incidents

Revoke or rotate exposed GitHub and LLM credentials immediately. Stop serving or
sharing affected reports/explorers, restrict access to local caches and backups, and
follow the relevant provider and organization incident-response procedures. See
[Privacy and data flow](docs/PRIVACY.md) for locations that may contain sensitive
material.
