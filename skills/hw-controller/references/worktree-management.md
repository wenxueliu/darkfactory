# Worktree管理

## What Success Looks Like

Each task has a clean, isolated worktree that:
- Is created from the correct base branch
- Has proper setup (dependencies installed, environment configured)
- Can be developed independently without conflicts
- Is registered in the worktree registry
- Is ready for execution to begin

## Your Approach

**Safety first.** Before creating any worktree:
1. Verify `.worktree/` is in `.gitignore` — never commit worktrees
2. Confirm base branch is correct

**Creation process per task:**
```bash
# From project root
git worktree add {worktree_base}/hw-task-{task_id} -b hw-task-{task_id}
cd {worktree_base}/hw-task-{task_id}
# Run project setup (npm install / pip install / etc.)
```

**Registration:**
Update `{project-root}/_bmad/memory/hw-controller/worktree-registry.yaml`:

```yaml
worktrees:
  hw-task-{id}:
    branch: hw-task-{id}
    status: created
    task_id: {id}
    created_at: {timestamp}
```

**Cleanup on failure:**
If worktree setup fails, remove the worktree and mark task as blocked:
```bash
git worktree remove {worktree_base}/hw-task-{task_id}
```

## Key Principles

- "Systematic directory selection + safety verification = reliable isolation"
- Proceed only after verifying gitignore
- Never skip baseline test verification
- Each worktree should have clean test baseline before execution

## Dependencies

Requires git worktree support. Ensure the project supports worktrees:
- Main branch should be in good state
- No uncommitted changes blocking branch creation

## Transition Gate

Worktree management is complete when:
1. All task worktrees are created
2. Each worktree has working environment
3. Registry is up to date
4. Ready to dispatch to parallel execution
