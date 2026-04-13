# 任务拆分

## What Success Looks Like

A set of independent, parallelizable tasks where:
- Each task has clear ownership and definition
- Dependencies between tasks are explicit
- Each task has acceptance criteria that define "done"
- Tasks can be executed concurrently in separate worktrees
- No circular dependencies

## Your Approach

**Analyze the design document.** Extract coherent units of work that:
- Can be developed independently
- Have minimal cross-task dependencies
- Are roughly equal in complexity (avoid mega-tasks)

**Dependency mapping:**
- Identify which tasks depend on outputs from other tasks
- Tasks with dependencies cannot start until dependencies are met
- Design tasks to minimize dependencies where possible

**Task definition template:**

```yaml
task_id: {id}
name: {descriptive name}
worktree: {worktree_base}/hw-task-{id}
dependencies: []
acceptance_criteria:
  - id: AC-1
    description: {specific, measurable result}
    verification: {how to verify}
status: pending
```

## Constraints

- Tasks must be independent enough to work in separate git worktrees
- Each task's worktree should be created at `{worktree_base}/hw-task-{task_id}`
- No circular dependencies (A→B→C→A)

## Output

Write task definitions to `{project-root}/_bmad/memory/hw-shared/tasks.yaml`:

```yaml
tasks:
  - task_id: hw-001
    name: {name}
    worktree: .worktree/hw-task-001
    dependencies: []
    acceptance_criteria: [...]
    status: pending
  - task_id: hw-002
    name: {name}
    worktree: .worktree/hw-task-002
    dependencies: [hw-001]  # if any
    acceptance_criteria: [...]
    status: pending
```

Also create `{project-root}/_bmad/memory/hw-controller/worktree-registry.yaml`:

```yaml
worktrees:
  hw-task-001:
    status: pending
    task_id: hw-001
  hw-task-002:
    status: pending
    task_id: hw-002
```

## Transition Gate

Task decomposition is complete when:
1. All tasks have acceptance criteria
2. Dependencies are resolved (no cycles)
3. Human approves the task list
