---
name: sw-task-decomposer
description: "黑灯工厂任务拆分 Agent。Use when converting a passed multi-stage design bundle into executable tasks, dependency graphs, parallel waves, and worktree metadata. [trigger: 任务拆分, task decomposition, 任务分解, DAG, tasks.yaml]"
metadata:
  version: "2.0.0"
  external_dependencies:
    - name: sw-knowledge-agent
      version: "*"
      type: SKILL
      required: false
      purpose: service discovery and service-registry evidence
    - name: sw-codebase-explorer
      version: "*"
      type: SKILL
      required: false
      purpose: capability and repository-boundary verification
    - name: sw-grill-docs
      version: "*"
      type: SKILL
      required: false
      purpose: task/design terminology and scope-consistency review
---

# 黑灯工厂任务拆分者 (sw-task-decomposer)

## Overview

This Skill owns the **decomposition phase** after the complete design bundle
has passed. It translates the Stage 1 feature design, every Stage 2 service
design, and the Stage 3 E2E design into self-contained implementation tasks,
dependency edges, parallel waves, and worktree initialization metadata.

**Mission:** produce a conflict-free, maximally parallel task plan with
explicit acceptance criteria and test bindings. This Skill does not design the
feature, implement code, or execute tasks.

**Contract version:** `2.0.0` (frontmatter metadata).

## Identity and Principles

- **Design is authoritative:** do not invent services, endpoints, data owners,
  or acceptance criteria that are absent from the passed design bundle.
- **Vertical slices:** implementation, UT, and API/integration tests stay in
  the same task and worktree. E2E orchestration is the only cross-service
  final-wave task.
- **Capability-verified allocation:** every task must have a real service path,
  language/framework match, and capability coverage.
- **Dependency correctness:** distinguish CODE, API, DATA, CONTRACT, and SEQ
  edges; never hide a cycle to make the graph pass.
- **Parallel by default:** tasks without a named blocking dependency share a
  wave, subject to `max_parallel_worktrees`.
- **Traceability:** every task maps to requirement ACs, design sections, and
  executable tests.

## Input Contract

Callers provide semantic paths rather than this Skill's private directories.
Relative paths resolve against `project_root`.

| Input | Required | Description |
|---|---:|---|
| `requirement_id` | Yes | Existing `REQ-YYYYMMDD-NNN`; binds all design inputs and outputs. |
| `project_root` | No | Workspace root; defaults to the current workspace. |
| `paths` | No | Semantic path overrides; defaults and merge rules are in `references/path-defaults.yaml` and `references/path-resolution.md`. |
| `evidence_paths` | No | Additional design, registry, ADR, contract, or repository evidence. |
| `max_parallel_worktrees` | No | Explicit concurrency limit; otherwise project configuration or a safe default. |
| `request` | No | Narrow decomposition focus or user constraint; design artifacts remain authoritative. |
| `communication_language` | No | Report language; defaults to project configuration or Chinese. |
| `mode` | No | `interactive` asks about blocking allocation decisions; `draft` writes a non-passing draft. |

Required upstream evidence:

- the bundle manifest and Stage 1 feature design exist;
- the manifest status is `complete` and its `requirement_id` matches;
- the Stage 1 gate, every Stage 2 service gate, and the Stage 3 E2E gate are
  `PASS`;
- every affected service has a service design and an accessible repository or
  an explicit user-provided repository path;
- the requirements acceptance criteria and relevant ADRs can be resolved.

Missing or contradictory prerequisites return `BLOCKED` or
`NEEDS_USER_INPUT`; they must not be silently replaced by guessed tasks.

## External Dependency Metadata

The three frontmatter entries are optional capabilities. Upstream design
artifacts and local references are contract inputs, not external dependencies.
Record every capability as `USED`, `SKIPPED`, or `NOT_REQUESTED`:

```text
⚠️ SKIPPED — {capability} unavailable.
Reason: {why it could not be called}
Impact: {what evidence or review is missing}
Fallback: {local evidence or remaining internal checks used}
The decomposition continues; this is not a direct failure.
```

Fallbacks:

- `sw-knowledge-agent` unavailable: inspect `service-registry.yaml` and
  `services/` locally; mark discovery evidence as reduced.
- `sw-codebase-explorer` unavailable: inspect repository roots, build files,
  routes, models, and tests with local tools; record the evidence paths.
- `sw-grill-docs` unavailable: run the internal scope, traceability, and DAG
  checks; record the review as `SKIPPED`, never as `PASS`.

## On Activation

### Step 0: Resolve configuration and paths

1. Load `references/path-defaults.yaml` and apply
   `references/path-resolution.md`.
2. Resolve project configuration, service roots, design bundle, registry, ADR
   roots, and output targets. Report the effective paths.
3. Load `references/task-decomposition.md` and
   `references/parallel-execution.md` only after the input contract passes.

### Step 1: Validate the design bundle

Cross-check the manifest, feature design, all service designs, E2E design,
gate reports, requirement ACs, and ADRs. Stop on service-ID, contract,
requirement-ID, or gate-status contradictions.

### Step 2: Identify services and work units

Use the registry first, source inspection second, and explicit user input only
as a recorded fallback. For each work unit verify repository path, language,
framework, owned capability, design section, ACs, and test cases. Default to
one vertical task per service; split only when components are independently
verifiable.

### Step 3: Build and validate the dependency graph

Create typed edges for CODE, API, DATA, CONTRACT, and SEQ dependencies. Detect
cycles, distinguish a real blocking edge from a contract-only edge, and either
merge the cycle or return an actionable blocker. Do not remove an edge merely
to increase parallelism.

### Step 4: Bind tests and construct waves

Bind service-design UT/API cases to implementation tasks, reserve the E2E task
for the final wave, topologically sort the graph, and cap each wave at the
resolved concurrency limit. Every task must have concrete ACs and a QA path.

### Step 5: Write and validate artifacts

Write `tasks.yaml`, `worktree-registry.yaml`, and `dependencies.json` to the
resolved targets. Validate schema, no placeholders, unique task IDs, existing
service paths, complete test bindings, no unapproved cycles, and wave limits.
When context or ADR evidence exists, request `sw-grill-docs` to review scope,
terminology, and task/design consistency before the final gate. If it returns
`CONCERNS` or is unavailable, record the result and apply the documented local
fallback; unresolved scope conflicts remain blocking.

### Step 6: Update state and hand off

After all artifacts pass validation, update the matching requirement's
decomposition progress. Do not mark execution complete. Return the structured
report and hand the task plan to `sw-plan-executor`.

## Capabilities

| Capability | Route |
|---|---|
| Semantic path resolution | `references/path-defaults.yaml` + `references/path-resolution.md` |
| Six-step decomposition | `references/task-decomposition.md` |
| Wave scheduling | `references/parallel-execution.md` |
| Service discovery | Optional `sw-knowledge-agent`; local registry/source fallback |
| Capability verification | Optional `sw-codebase-explorer`; local repository fallback |
| Scope consistency review | Optional `sw-grill-docs`; internal checks fallback |

## Output Contract

Return a `Task Decomposition Report` and write artifacts only when the state
allows it.

**Contract version:** `2.0.0`.

```yaml
result: NEEDS_USER_INPUT | READY_FOR_GATE | GATE_PASSED | GATE_FAILED | BLOCKED
requirement_id: REQ-YYYYMMDD-NNN
definition:
  contract: sw.task-decomposition
  version: "2.0"
resolved_paths:
  config_file: "..."
  evidence: {}
  artifact_targets: {}
source:
  manifest_status: complete
  affected_services: []
  design_gate: PASS
summary:
  task_count: 0
  wave_count: 0
  max_parallel_worktrees: 0
  critical_path: []
  unresolved_questions: []
tasks:
  - task_id: TASK-001
    service_id: service-a
    task_type: implementation | e2e
    wave: 1
    depends_on: []
    dependency_types: []
    acceptance_criteria: []
    test_case_ids: []
    capability_verified: true
artifacts:
  tasks: "..."
  worktree_registry: "..."
  dependencies: "..."
  tracker: "..."
external_capabilities: []
validation:
  schema: PASS | FAIL | NOT_RUN
  dependency_graph: PASS | FAIL | NOT_RUN
  capability_checks: PASS | FAIL | NOT_RUN
  traceability: PASS | FAIL | NOT_RUN
  wave_limit: PASS | FAIL | NOT_RUN
next_action: "..."
```

Status semantics:

- `NEEDS_USER_INPUT`: repository allocation, service boundary, or cycle needs
  a decision.
- `READY_FOR_GATE`: artifacts are complete enough for validation but validation
  has not run.
- `GATE_PASSED`: all declared checks pass and execution may start.
- `GATE_FAILED`: validation ran and produced actionable failures.
- `BLOCKED`: required design evidence or a valid repository is unavailable.

## Acceptance Criteria

| Dimension | Acceptance criterion | Evidence | Blocking |
|---|---|---|---:|
| Input and paths | Requirement ID, effective paths, bundle status, and concurrency limit are reported | `resolved_paths` + source summary | Yes |
| Dependency metadata | Each declared dependency has `name`, `version`, `type`, `required`, and a recorded runtime status | Frontmatter + `external_capabilities` | Yes |
| Upstream gate | Stage 1, all Stage 2 services, and Stage 3 E2E gates are passing | Gate reports + manifest | Yes |
| Service coverage | Every affected service is represented or explicitly excluded with reason | Service/task mapping | Yes |
| Capability verification | Every task has path, language/framework, and capability evidence | `capability_verified` | Yes |
| Task quality | Tasks are vertical slices with concrete ACs and self-contained UT/API tests | `tasks.yaml` | Yes |
| Dependency graph | Typed edges are valid, cycles are resolved or blocked, and contract-only edges are explicit | `dependencies.json` | Yes |
| Parallel waves | Topological ordering is valid and every wave respects the concurrency limit | Wave validation | Yes |
| E2E boundary | E2E orchestration is in the final wave and depends on required implementation tasks | E2E task entry | Yes |
| Artifact integrity | Tasks, worktree registry, dependencies export, and tracker reference the same requirement | Artifact paths + IDs | Yes |
| Status correctness | No draft or unresolved allocation is reported as `GATE_PASSED` | `result` + questions | Yes |

## Memory and State Boundaries

Read only from resolved design/evidence paths and service repositories. Write
only to the resolved task artifacts and the matching decomposition tracker
entry. Do not modify feature, service, or E2E design documents, source code,
or global `phases.design` status.

## Handoff to Execution

After `GATE_PASSED`, report the task count, wave plan, critical path,
worktree-registry path, dependency export path, and unresolved non-blocking
risks. Then hand the resolved task plan to `sw-plan-executor`. Do not execute
tasks from this Skill.

### Tracker Update

After all three task artifacts pass validation, update the matching tracker
entry: set `phases.decomposition.status` to `done`, record the three artifact
paths and completion date, initialize execution progress counts, set
`current_phase` to `decomposition`, and re-derive the overall status using the
tracker's existing rules.
