# Change propagation packet reference

## Packet semantics

`change.py plan` is intentionally non-mutating. It writes a packet under:

```text
knowledge/changes/{requirement_id}/{change_id}/
├── change-propagation.yaml
└── phase-deltas/
    ├── 01-design.md
    ├── 02-decomposition.md
    └── ...
```

The packet is the handoff between the change assessment and downstream Agents.
The phase delta is a content contract, not a final design: the receiving Agent
must use the original artifact, the delta, and current repository evidence to
write the new phase output.

## Propagation matrix

| Earliest affected phase | Regenerate from there |
|---|---|
| `ideation` | ideation → value assessment → design → decomposition → execution → merge → test → delivery |
| `design` | design → decomposition → execution → merge → test → delivery |
| `decomposition` | decomposition → execution → merge → test → delivery |
| `execution` | execution → merge → test → delivery |
| `merge` | merge → test → delivery |
| `test` | test → delivery |
| `delivery` | delivery |

`small` is the only exception: it affects only the current phase and keeps
the same revision. `large` has no propagation list because it creates a new
requirement and begins at ideation.

## Version policy

- `source_revision` is the revision consumed before the change.
- `target_revision` is source + 1 for a propagated phase.
- A propagated phase keeps its own revision; do not use one global version to
  hide a phase that was not regenerated.
- The old output remains a historical artifact and is linked through
  `superseded_by`.

## Handoff contract

Each receiving phase must report:

```yaml
status: done
revision: 2
change_id: CHG-...
input_packet: knowledge/changes/...
gate: PASS
artifacts:
  - knowledge/...
```

The controller may advance only when the phase revision matches the packet's
target revision and the phase gate is `PASS`.
