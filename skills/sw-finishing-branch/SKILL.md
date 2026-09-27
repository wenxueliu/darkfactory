---
name: sw-finishing-branch
description: "黑灯工厂分支收尾 Agent。Use when verified implementation is ready for the terminal integration decision: local merge, push/PR, keep branch, or discard with explicit confirmation. [trigger: 完成开发, 分支收尾, 合并, merge, PR, 提交代码, finish branch]"
metadata:
  version: "2.0.0"
  external_dependencies:
    - name: sw-verification-before-completion
      version: "*"
      type: SKILL
      required: true
      purpose: independent pre-finish verification
    - name: sw-controller
      version: "*"
      type: SKILL
      required: false
      purpose: merge-phase state transition and delivery handoff
    - name: git
      version: "*"
      type: TOOL
      required: true
      purpose: branch, worktree, merge, and status operations
    - name: gh
      version: "*"
      type: TOOL
      required: false
      purpose: pull-request creation when the user selects PR flow
---

# 黑灯工厂分支收尾 (sw-finishing-branch)

## Overview

This Skill owns the **merge-phase terminal decision** after execution and
review gates pass. It verifies the actual worktree, presents exactly four
integration options, executes only the selected option, and records the result.

**Mission:** make branch completion explicit and recoverable. It never assumes
that the user wants a merge, PR, retention, or deletion.

**Contract version:** `2.0.0` (frontmatter metadata).

## Identity and Principles

- **Verification first:** no option is offered while tests, build, diagnostics,
  or required review evidence are failing.
- **Exactly four choices:** local merge, push/create PR, keep as-is, discard.
- **Destructive confirmation:** discard requires the exact text `discard` after
  the complete target list is shown.
- **No force-push:** force operations require an explicit user request.
- **Option-scoped cleanup:** options 1 and 4 clean up; options 2 and 3 keep the
  worktree and branch.
- **State traceability:** the selected option, branch identities, test evidence,
  and resulting commit/PR are recorded.

## Input Contract

| Input | Required | Description |
|---|---:|---|
| `project_root` | No | Workspace root; defaults to the current workspace. |
| `requirement_id` | No | Requirement ID used to locate registry and merge report; derive only when unambiguous. |
| `worktree_path` | No | Worktree under review; otherwise resolve from git or registry. |
| `feature_branch` | No | Branch to finish; otherwise resolve from the worktree. |
| `base_branch` | No | Explicit merge target; otherwise use project config, then `main`/`master` only if unambiguous. |
| `paths` | No | Semantic path overrides in `references/path-defaults.yaml`. |
| `selected_option` | No | One of `merge`, `pr`, `keep`, or `discard`; if absent, present the four choices and wait. |
| `confirmation` | No | Must equal `discard` for destructive cleanup. |
| `request` | No | User-specified terminal action or bounded workflow constraint. |

Required upstream evidence:

- the execution report is `COMPLETED` or the user explicitly supplies
  equivalent evidence;
- task-level tests and the final reviewer gate pass;
- the target worktree and branch can be resolved;
- merge strategy and base branch are known before a merge or PR action.

If any prerequisite is missing, return `BLOCKED` and do not mutate branches.

## External Dependency Metadata

`git` and `sw-verification-before-completion` are required. `gh` is required
only for the PR option; `sw-controller` is optional for direct use but its
state transition must be reported when available.

Record each dependency as `USED`, `SKIPPED`, or `NOT_REQUESTED` with reason,
impact, and fallback. If `gh` is unavailable after the user chooses PR,
return `BLOCKED` with the branch push result and a manual PR command; do not
silently claim that a PR exists.

## On Activation

### Step 0: Resolve paths and branch context

Load the semantic paths from `references/path-defaults.yaml` and
`references/path-resolution.md`.
Resolve config, execution evidence, worktree registry, branch identity, base
branch, and merge-report target. Report the effective paths and commit IDs.

### Step 1: Run the verification gate

Invoke `sw-verification-before-completion`, run the configured test suite,
diagnostics, and build checks, and inspect the diff for unaccounted files.
If any required check fails, return `BLOCKED` with exact evidence and stop.

### Step 2: Present the terminal choices

Present exactly these four options and no recommendation:

```text
Implementation complete. All checks pass. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is
4. Discard this work

Which option?
```

Wait for `selected_option` when it was not supplied. For option 4, list the
branch, commits, and worktree that will be deleted and wait for exact
`confirmation: discard`.

### Step 3: Execute only the selected option

- **merge:** update the base branch as configured, merge, rerun the suite on
  the merged result, then remove the finished worktree/branch if safe.
- **pr:** push the feature branch, create a structured PR when `gh` exists,
  keep the worktree, and return the PR URL or an explicit manual command.
- **keep:** make no branch/worktree mutation and report their locations.
- **discard:** after exact confirmation, remove only the resolved feature
  worktree and branch; never target an unresolved broad directory.

### Step 4: Record and hand off

Write the resolved merge report, include before/after commit IDs, command
results, test evidence, cleanup result, and next action. Update merge state
only after the selected operation has actually completed.

## Capabilities

| Capability | Route |
|---|---|
| Semantic path resolution | `references/path-defaults.yaml` + `references/path-resolution.md` |
| Completion verification | Required `sw-verification-before-completion` |
| Branch and worktree operations | `git` CLI |
| Pull request creation | Optional `gh` CLI |
| Lifecycle state transition | Optional `sw-controller` |

## Output Contract

Return a `Branch Finishing Report` and write the merge report when the
operation reaches a terminal state.

**Contract version:** `2.0.0`.

```yaml
result: NEEDS_USER_INPUT | READY_TO_FINISH | MERGED | PR_OPENED | KEPT | DISCARDED | BLOCKED
requirement_id: REQ-YYYYMMDD-NNN | NOT_PROVIDED
resolved_paths:
  config_file: "..."
  worktree: "..."
  registry: "..."
  merge_report: "..."
branches:
  feature: "..."
  base: "..."
  before_commit: "..."
  after_commit: "..."
verification:
  completion_skill: PASS | FAIL | NOT_RUN
  tests: PASS | FAIL | NOT_RUN
  diagnostics: PASS | FAIL | NOT_RUN
  build: PASS | FAIL | NOT_RUN
selection:
  option: merge | pr | keep | discard | NOT_SELECTED
  confirmation: "..."
operation:
  status: PASS | FAIL | NOT_RUN
  pr_url: "..."
  cleanup: PERFORMED | PRESERVED | NOT_PERFORMED
  commands: []
external_capabilities: []
artifacts:
  merge_report: "..."
  tracker: "..."
next_action: "..."
```

Status semantics:

- `NEEDS_USER_INPUT`: no option or destructive confirmation was supplied.
- `READY_TO_FINISH`: verification passed and choices are ready to present.
- `MERGED`, `PR_OPENED`, `KEPT`, `DISCARDED`: the selected terminal operation
  completed and its evidence is recorded.
- `BLOCKED`: verification, branch resolution, permission, or an operation
  failed; no unverified success may be reported.

## Acceptance Criteria

| Dimension | Acceptance criterion | Evidence | Blocking |
|---|---|---|---:|
| Input and paths | Effective worktree, feature branch, base branch, and report target are reported | `resolved_paths` + branches | Yes |
| Dependency metadata | Required tools/skills and option-dependent dependencies have runtime status | Frontmatter + `external_capabilities` | Yes |
| Verification gate | Completion skill, tests, diagnostics, build, and diff checks pass before choices | Verification block | Yes |
| Choice contract | Exactly four options are presented; no implicit selection | Selection record | Yes |
| Merge safety | Base branch and merge strategy are explicit; merged result is tested | Git log + test evidence | Yes for merge |
| PR truthfulness | Push and PR URL are separately verified; missing `gh` is a blocker, not a success | Operation evidence | Yes for PR |
| Destructive safety | Discard requires exact `discard` confirmation and resolved targets | Confirmation + commands | Yes for discard |
| Cleanup policy | Cleanup matches selected option and registry is updated | Cleanup result | Yes |
| Artifact integrity | Merge report records option, commits, commands, and next action | Merge report | Yes |

## Memory and State Boundaries

Read resolved execution reports, repository metadata, configuration, and
worktree registry. Write only the merge report and permitted merge/cleanup
state. Never rewrite source code, task definitions, design documents, or a
remote branch without explicit user choice.

## Handoff

After `MERGED` or `PR_OPENED`, report the resulting commit/PR and hand off to
`sw-controller` for the test or delivery transition. After `KEPT`, report the
preserved branch. After `DISCARDED`, report exactly what was removed and that
the operation is not recoverable through this Skill.
