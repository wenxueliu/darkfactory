# 任务状态上报

## What Success Looks Like

Top Controller has accurate, timely information about worktree progress. Status transitions are clear and actionable.

## Status Types

| Status | Meaning | When to Use |
|--------|---------|--------------|
| `RUNNING` | Worktree active, executing | Normal operation |
| `DONE` | Task complete, all gates passed | Success |
| `DONE_WITH_CONCERNS` | Complete but has concerns | Minor issues remain |
| `NEEDS_CONTEXT` | Blocked on missing info | Need information |
| `BLOCKED` | Stuck, need help | Cannot proceed |

## Report Format

Update `{project-root}/_context/memory/sw-controller/worktree-registry.yaml`:

```yaml
worktrees:
  sw-task-{id}:
    status: {RUNNING/DONE/BLOCKED/etc}
    task_id: {id}
    current_phase: {tdd-ut/tdd-api/review/gates}
    iteration: {n}/{max}
    progress_percent: {n}
    last_updated: {timestamp}
    issues:
      - severity: {P0/P1/P2/P3}
        description: {text}
        resolved: {yes/no}
    blockers: []
    concerns: []
```

## When to Report

| Event | Action |
|-------|--------|
| Phase transition | Report immediately |
| Iteration complete | Report progress |
| Issue found | Report if blocking |
| Issue resolved | Report progress |
| Blocked | Report immediately |
| Done | Report + summary |

## Progress Updates

Keep reports concise but informative:

```
[Task sw-001] Progress: 65%
- Phase: TDD-API Cycle (Layer 2)
- UT: PASS (23 tests)
- API Tests: 12/18 passing
- Issues: 2 P2 remaining (iteration 2/3)
- Next: Fix P2 issues, re-run API tests
```

## Final Report (DONE)

```yaml
task_id: sw-001
status: DONE
summary:
  ut_tests: {n} passed
  api_tests: {n} passed
  coverage: {n}%
  issues_resolved:
    - P0: {n}
    - P1: {n}
    - P2: {n}
    - P3: {n} (documented, not fixed)
  human_interventions: {n}
  total_iterations: {n}
duration: {duration}
```
