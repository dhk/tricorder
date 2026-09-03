# Findings for `repo-lens`

One file per independent source. Do not read another source's findings before writing your own.

## Naming

- `<source-slug>-findings.md` — the narrative findings document. Examples: `perplexity-findings.md`, `claude-findings.md`, `dhk-findings.md`.
- `<source-slug>-lenses/` — the YAML lens files that source produced, one per archetype, plus `detection-rubric.yaml` if used. Example: `perplexity-lenses/product-engineering-desktop.yaml`.

## Format rules

Follow [TEMPLATE.md](TEMPLATE.md) exactly. Two rules are not negotiable:

1. **Verdict is a closed set.** Every table row's Verdict cell is exactly one of `adopt/reference`, `differentiate`, or `ignore`. No other labels, no qualifiers, no rationale in the cell. Rationale goes in the Notes block under the table.
2. **No empty tables.** A question with no findings gets one row whose Entry is `none found`, with the reason in Notes. Silence is not a result.

Citations carry title, publisher or authors, URL, retrieval date, and the claim supported. Mark each as `primary` or `secondary` per the source rules in the handoff prompt.

## Submitting

- **With repository write access:** add your files here and commit on the working branch. Do not edit another source's files.
- **Without repository write access:** paste the findings document and the YAML files back to the person who sent you the handoff prompt. They will commit them under your source slug unchanged.
