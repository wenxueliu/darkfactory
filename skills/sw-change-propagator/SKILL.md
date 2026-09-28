---
name: sw-change-propagator
description: "黑灯工厂需求变更传播 Agent。Use when a requirement changes during design, decomposition, coding, testing, or delivery and the current/downstream artifacts must be versioned, invalidated, and regenerated. [trigger: 需求变更, 变更传播, 局部调整, 影响分析, 重新规划]"
metadata:
  version: "1.0.0"
  external_dependencies:
    - name: change.py
      version: "1.0.0"
      type: TOOL
      required: true
      purpose: generate and apply versioned change propagation packets
    - name: PyYAML
      version: ">=6.0"
      type: LIBRARY
      required: true
      purpose: read and update requirements-tracker.yaml
    - name: sw-requirements-clarifier
      version: "*"
      type: SKILL
      required: false
      purpose: re-clarify changes that alter user intent or acceptance criteria
    - name: sw-task-decomposer
      version: "*"
      type: SKILL
      required: false
      purpose: regenerate the task DAG after downstream invalidation
---

# 黑灯工厂需求变更传播 (sw-change-propagator)

## Overview

This Skill owns the change boundary after a requirement has entered the
workflow. It classifies the change, finds the earliest affected phase, creates
an auditable change packet, and propagates version/content deltas through the
current and downstream phases.

It does not silently rewrite completed requirements, design documents, tasks,
or code. It creates a packet first; applying it requires explicit approval.

**Contract version:** `1.0.0`.

## Change Classification

| Kind | Meaning | Action |
|---|---|---|
| `small` | One local implementation or document step; no acceptance, contract, or dependency impact | Directly edit the current step; do not propagate. |
| `partial` | Same user outcome, but an already completed/current stage or downstream output is affected | Start at the earliest affected phase, increment revisions, and regenerate that phase plus all later phases. |
| `large` | New user outcome, major scope change, or a change that should be released independently | Create a new requirement and start from ideation; preserve the old requirement. |

When uncertain between `small` and `partial`, choose `partial`. When the
change alters the user outcome or can be released independently, choose
`large`.

## Input Contract

| Input | Required | Description |
|---|---:|---|
| `project_root` | Yes | Workspace root containing `knowledge/requirements-tracker.yaml`. |
| `requirement_id` | Yes | Existing requirement identifier. |
| `change_summary` | Yes | User-approved description of what changed and why. |
| `kind` | Yes | `small`, `partial`, or `large`; ask if classification is uncertain. |
| `current_phase` | No | Current phase; defaults from tracker. |
| `affected_phases` | No | Additional impact hints; partial propagation starts at the earliest one. |
| `approval` | Required for apply | Explicit human approval before tracker mutation or downstream regeneration. |

Phase aliases such as `service_design`, `feature_design`, `coding`, and
`integration_test` resolve to the canonical tracker phases.

## Workflow

1. Read the tracker and the current phase status.
2. Classify the change and identify the earliest affected phase.
3. Run `change.py plan`; do not mutate the tracker yet.
4. Review the packet: source revision, target revision, invalidated phases,
   source artifacts, and phase-specific content changes.
5. Ask for approval when the change is `partial` or `large`.
6. Run `change.py apply --approve` only after approval.
7. For `partial`, delegate the affected phases in order. Each downstream
   Agent consumes its phase delta, writes the new artifact revision, reruns its
   gate, and hands the revised output to the next phase.
8. For `large`, invoke `sw-requirements-clarifier` with the new requirement
   and do not modify the old requirement's downstream artifacts.
9. Update the tracker only with verified outputs; never mark a
   `change_requested` phase as `done` based on a plan alone.

Example:

```bash
python change.py plan \
  --project-root . \
  --requirement-id REQ-001 \
  --kind partial \
  --current-phase service_design \
  --change "新增权限校验"

python change.py apply \
  --project-root . \
  --packet knowledge/changes/REQ-001/CHG-*/change-propagation.yaml \
  --approve
```

## Output Contract

The Skill returns and writes:

| Output | Required |
|---|---:|
| `change-propagation.yaml` | Schema version, strategy, source/target revision, affected phases, and approval status. |
| `phase-deltas/*.md` | One content-change checklist for the current/downstream phase. |
| `tracker` update | Only after approval; records `change_requests`, previous status, new revision, and `superseded_by`. |
| `status` | `NEEDS_USER_INPUT`, `READY`, or `BLOCKED`. |
| `next_action` | Exact downstream Agent and phase to resume. |

For a partial change beginning in `design`, the packet must contain:

```text
design → decomposition → execution → merge → test → delivery
```

Each phase receives its own target revision and content delta. Existing
artifacts remain available as historical evidence; they are not silently
overwritten by the planner.

## State Rules

- `change_requested` blocks normal phase transition until the phase gate passes.
- `superseded_by` identifies the change packet that invalidated the prior output.
- `previous_status` preserves whether the phase was `done`, `in_progress`, or
  `pending` before the change.
- Completed code is preserved in its worktree/commit; affected work is paused
  and replanned rather than discarded.
- A reviewer suggestion that changes business scope is a change request, not
  an automatic code edit.

## Acceptance Criteria

- Small changes produce exactly one affected phase and no downstream revision.
- Partial changes produce every phase from the earliest affected phase through
  delivery, each with source/target revision and content changes.
- Large changes create a new requirement skeleton and leave the old
  requirement's downstream artifacts untouched.
- Applying a packet requires explicit approval and is idempotently rejected if
  already applied.
- Completed affected phases are marked `change_requested` with
  `previous_status` and `superseded_by` recorded.
- Every downstream Agent receives the phase delta before it writes a new
  artifact or resumes execution.
- No stale artifact is accepted by `sw-controller` as a valid phase input.
