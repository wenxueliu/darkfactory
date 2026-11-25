# MADR 4.0 (bare) — template and field guide

MADR is a Markdown template for Architecture Decision Records. The "bare"
variant keeps only the sections that carry a decision; fill-in comments are
removed as soon as the ADR is written.

**Canonical template shipped by this skill:** [`../scripts/src/adrkit/templates/adr-template.md`](../scripts/src/adrkit/templates/adr-template.md)
(`adr-init` copies it to `<adr-dir>/template/adr-template.md`).

## Frontmatter

```yaml
---
status: proposed
date: 2026-01-02
decision-makers: [alice, bob]
consulted: [carol]
informed: [team-platform]
---
```

| Field | Required | Values / notes |
| --- | --- | --- |
| `status` | yes | `proposed`, `accepted`, `rejected`, `deprecated`, or `superseded by ADR-NNNN` |
| `date` | recommended | `YYYY-MM-DD` of the last update; invalid values are a warning (R1.7) |
| `decision-makers` | optional | people who own the decision |
| `consulted` | optional | two-way communication (subject-matter experts) |
| `informed` | optional | one-way communication |
| `source-commit` | generated | full SHA written by `adr-gen`; used to keep `--all-commits` idempotent |

`adr-check` also accepts a legacy `## Status` section (MADR 3.x / adr-tools) so
existing repositories do not need a migration.

## Body

```markdown
# <short title: solved problem + chosen solution>

## Context and Problem Statement

2–3 sentences (or a short story). State the scope: which components,
boundaries, or constraints are affected.

## Decision Drivers

- <quality, force, or constraint>

## Considered Options

- <option 1>
- <option 2>

## Decision Outcome

Chosen option: "<option 1>", because <specific justification>.

### Consequences

- Good, because <positive effect>
- Bad, because <accepted trade-off>

### Confirmation

How compliance is checked: review, test, or a mechanical gate. **Use this
section to point at the adr-drift rule or CI job that enforces the decision.**

## More Information

Links, assumptions, revisit date. Add `- Supersedes ADR-NNNN` here when this
decision replaces an earlier one.
```

The bare template keeps `## Pros and Cons of the Options` as a stub; delete it
when the rejected alternatives are not worth remembering. `adr-init` seeds
`status: proposed` (MADR's bare file leaves it blank) so a copied file starts
in a valid state.

## Rules of thumb

- **One decision per ADR.** If the title needs "and", split it.
- **Immutable once accepted.** Change the code or write a new ADR that
  supersedes it; do not rewrite history.
- **The title is the index line.** It must make sense without the body.
- **The ADR is not a design doc.** Link to the design instead of copying it.
- **Status is the human gate.** `adr-gen` always writes `proposed`; a human
  changes it to `accepted`.

## Numbering

`NNNN-kebab-slug.md`, four digits, lowercase ASCII, hyphen-separated words.
`adr-init`/`adr-gen` allocate `max(number) + 1`. Gaps are warned (R1.3) but not
fatal, because deleting a record is worse than leaving a gap.
