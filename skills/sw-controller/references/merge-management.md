# 合并管理

## What Success Looks Like

All worktrees are successfully merged back to the main branch:
- No unresolved merge conflicts
- Each worktree's changes are preserved and coherent
- Main branch remains stable throughout

## Your Approach

**Pre-merge verification:**
1. Confirm all worktrees report `DONE`
2. Verify no pending P0/P1/P2 issues
3. Check merge strategy from config (`merge` or `rebase`)

**Merge process:**
```bash
# From main branch
git checkout main
git merge --{strategy} hw-task-{id}
# Resolve conflicts if any
git add -A
git commit -m "Merge worktree hw-task-{id}: {summary}"
```

**Conflict resolution:**
If merge conflicts occur:
1. Identify conflicting files
2. Assess complexity
3. Either:
   - Auto-resolve if trivial
   - Request human help for complex conflicts
4. Document resolution in `{project-root}/_bmad/memory/hw-shared/design-decisions.md`

**Cleanup:**
After successful merge:
```bash
git worktree remove {worktree_base}/hw-task-{task_id}
git branch -d hw-task-{task_id}  # Safe, branch is merged
```

Update registry:
```yaml
worktrees:
  hw-task-{id}:
    status: merged
    merged_at: {timestamp}
```

## Merge Strategies

| Strategy | Config Value | Use When |
|----------|--------------|----------|
| `--no-ff` | `merge` | Need to preserve worktree history |
| `rebase` | `rebase` | Prefer linear history |

## Transition Gate

Merge is complete when:
1. All worktrees merged to main
2. No merge conflicts remain
3. Main branch is stable (tests pass)
4. Worktrees cleaned up
