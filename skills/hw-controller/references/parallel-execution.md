# 并行执行协调

## What Success Looks Like

Multiple worktrees are executing concurrently with:
- Clear task distribution to each worktree
- Progress being tracked in real-time
- Status reports flowing back from Worktree Controllers
- Bottlenecks identified and addressed
- No resource conflicts between parallel tasks

## Your Approach

**Dispatch model:** One Worktree Controller per worktree, operating in parallel.

**Communication:** Asynchronous via shared memory:
- Top Controller writes task assignments to `{project-root}/_bmad/memory/hw-shared/tasks.yaml`
- Worktree Controllers read assignments and write status to `{project-root}/_bmad/memory/hw-controller/worktree-registry.yaml`

**Monitoring loop:**
1. Check `{project-root}/_bmad/memory/hw-controller/worktree-registry.yaml` for status updates
2. Check for blocked or needs_context reports
3. Address issues (provide context, resolve dependencies)
4. Log progress to global state

**When a worktree reports:**
| Status | Action |
|--------|--------|
| `DONE` | Mark complete, check if all done for merge |
| `DONE_WITH_CONCERNS` | Log concerns, decide if human review needed |
| `NEEDS_CONTEXT` | Provide context from shared memory |
| `BLOCKED` | Analyze cause, escalate or resolve dependency |

**Concurrency limits:**
- Respect system resources (don't spawn unlimited parallel agents)
- Consider CPU/memory when determining parallel degree
- Default: match number of CPU cores

## State Tracking

Maintain `{project-root}/_bmad/memory/hw-controller/global-state.yaml`:

```yaml
phase: execution
start_time: {timestamp}
worktrees:
  total: {n}
  running: {n}
  done: {n}
  blocked: {n}
progress:
  overall_percent: {n}
  blockers: []
```

## Transition Gate

Parallel execution is complete when:
1. All worktrees report `DONE` or human-approved deviation
2. All P0/P1/P2 gate issues are resolved
3. Ready to proceed to merge
