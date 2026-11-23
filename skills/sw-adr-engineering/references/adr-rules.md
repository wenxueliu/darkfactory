# adr-check — R1/R2 rule reference

`adr-check` validates the record set itself. It never reads source code; code
drift is adr-drift's job (see [`adr-drift.md`](adr-drift.md)).

```bash
adr-check --dir docs/adr            # errors fail, warnings do not
adr-check --dir docs/adr --strict   # warnings fail too
adr-check --dir docs/adr --json     # machine-readable report
```

Exit codes: `0` clean, `1` violations (or warnings with `--strict`), `2` bad
usage / missing directory.

## R1 — structure

| Rule | Level | Check | Fix |
| --- | --- | --- | --- |
| R1.0 | warning | no ADR files found | run `adr-init` / `adr-gen` |
| R1.1 | error | filename is `NNNN-kebab-slug.md` (four digits, lowercase ASCII) | rename the file |
| R1.2 | error | ADR number is unique | renumber the newer file |
| R1.3 | warning | no gap in `1..max` | restore the missing record or accept the gap |
| R1.4 | error | level-1 title exists | add `# <title>` |
| R1.5 | error | `status` is present (frontmatter or `## Status`) | add `status: proposed` |
| R1.6 | error | status is `proposed` / `accepted` / `rejected` / `deprecated` / `superseded by ADR-NNNN` | use the exact vocabulary |
| R1.7 | warning | `date` (when present) is a real `YYYY-MM-DD` | fix the date |
| R1.8 | error | no unfilled MADR template markers (`<!-- short title`, `Chosen option: ""`, …) | fill or delete the draft |
| R1.9 | warning | `## Context and Problem Statement` and `## Decision Outcome` exist and are non-empty | complete the MADR sections |

`index.md`, `README.md`, hidden directories, and `template/` are never treated
as ADRs.

## R2 — reference integrity

Supersession is the only cross-ADR link that is mechanically checked. The
convention is **bidirectional**:

```markdown
<!-- 0001-use-node-gateway.md -->
---
status: superseded by ADR-0007
---
```

```markdown
<!-- 0007-migrate-gateway-to-rust.md -->
---
status: accepted
supersedes: [ADR-0001]      # optional frontmatter key, or
---
...
## More Information

- Supersedes ADR-0001        # ... this line also satisfies the backlink
```

| Rule | Level | Check | Fix |
| --- | --- | --- | --- |
| R2.1 | error | `superseded by ADR-NNNN` target exists | fix the number or the status |
| R2.2 | error | the replacement links back | add `supersedes: [ADR-NNNN]` or a `Supersedes ADR-NNNN` line |
| R2.3 | error | an ADR cannot supersede itself | correct the number |
| R2.4 | error | no supersession cycle | make the chain linear |
| R2.5 | warning | the replacement is `accepted` | accept it, or point at the right record |
| R2.6 | warning | a `supersedes` claim is reciprocated | set the old ADR's status |

R2.2 is deliberately an error: a one-way link lets the old decision disappear
from the replacement's history. R2.5 is a warning so a `proposed` replacement
can be merged while review is in progress.

## Status vocabulary

| Status | Meaning | Index annotation |
| --- | --- | --- |
| `accepted` | in force | none |
| `proposed` | under review, not yet binding | `(proposed)` |
| `rejected` | considered and declined | `(rejected)` |
| `deprecated` | still true but should not be used for new work | `(deprecated)` |
| `superseded by ADR-NNNN` | replaced | `(superseded by ADR-NNNN)` |

Anything else is R1.6. The bare token `superseded` is rejected because it hides
the replacement and makes R2.1–R2.4 impossible to check.

## What is intentionally not checked

- Prose quality, option counts, or whether the decision is "good" — human review.
- Duplicate titles — different numbers may legitimately share a topic.
- Whether the code follows the decision — that is R3/R4 (adr-drift).
- Links to external URLs — network checks do not belong in a deterministic gate.
