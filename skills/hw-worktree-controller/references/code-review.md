# 代码审核协调

## What Success Looks Like

Code is reviewed by heterogeneous agents in parallel, each from their perspective. All P0/P1/P2 issues are identified and resolved. Architecture conflicts are escalated to human.

## Your Approach

### Dispatch Parallel Reviews

Based on `enabled_reviewers` config, dispatch reviewers in parallel:

| Reviewer | Focus | Expected Output |
|----------|-------|----------------|
| Security Agent | Vulnerabilities, data handling | `reviews/{task_id}-security.md` |
| Logic Agent | Correctness, edge cases | `reviews/{task_id}-logic.md` |
| Performance Agent | Scalability, bottlenecks | `reviews/{task_id}-performance.md` |

### Review Process

1. **Collect code to review** — UT-passed, API test-passed code
2. **Dispatch to each reviewer** in parallel
3. **Collect results** from each reviewer
4. **Aggregate issues** by severity
5. **Address issues** — Fix or escalate

### Issue Handling

| Severity | Action |
|----------|--------|
| P0/P1/P2 | Must fix before proceeding |
| P3 | Document, optional to fix |

### Architecture Conflicts

If reviewers disagree on architecture:
1. Log conflict to `{project-root}/_bmad/memory/hw-shared/reviews/{task_id}-conflicts.md`
2. Escalate to human via Top Controller
3. Wait for resolution before proceeding

## Review Output Format

Each reviewer should output:

```markdown
## {Review Type} Review: {Task ID}

### Issues Found

| Severity | Issue | Location | Recommendation |
|----------|-------|----------|----------------|
| P1 | {description} | {file:line} | {fix} |

### Summary

- Total issues: {n}
- P0: {n} | P1: {n} | P2: {n} | P3: {n}
- Blocking: {yes/no}
```

## Transition

Code review is complete when:
1. All enabled reviewers have completed
2. All P0/P1/P2 issues resolved or escalated
3. Human has resolved any architecture conflicts
