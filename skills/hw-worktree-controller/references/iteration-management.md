# 迭代管理

## What Success Looks Like

Issues are fixed through iteration before escalating. Each iteration makes progress. Escalation happens at the right time — not too early, not too late.

## Iteration Loop

```
Issue Found → Attempt Fix → Verify → Pass?
                                      ↓
                              Yes → Next issue or Done
                                      ↓
                               No → Count iteration
                                      ↓
                              Max reached? → Escalate
                                      ↓
                                   No → Retry
```

## Tracking

Track per task:
- Total iterations attempted
- Current iteration number
- Issues remaining
- Time spent

## When to Iterate

| Condition | Action |
|-----------|--------|
| Simple fix | Iterate immediately |
| Complex issue | Try once, then escalate |
| Same issue recurring | Escalate |
| Max iterations reached | Escalate |

## Max Iterations

From config: `min_iteration_before_human` (default: 3)

After max iterations:
- If issue unresolved → escalate to human
- Document what was tried
- Include in escalation report

## Progress Reporting

Keep Top Controller informed:

```yaml
iteration: {n}/{max}
issues_remaining:
  - id: {n}
    severity: {P0/P1/P2}
    description: {text}
    attempts: {n}
```

## Transition

Iteration management ends when:
1. Issue resolved → continue to next
2. Max iterations reached → escalate
3. All issues resolved → proceed to next phase
