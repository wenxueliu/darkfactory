# 人工介入判断

## What Success Looks Like

Human intervention happens at the right moments:
- Not too early (waste human attention)
- Not too late (block progress unnecessarily)
- With clear context and options
- Result is documented and acted upon

## When to Escalate

| Condition | Action |
|-----------|--------|
| P0/P1/P2 issues after max iterations | Human must review |
| Architecture review conflict | Human must decide |
| Merge conflict (complex) | Human must resolve |
| Worktree blocked > N iterations | Human must assist |
| Human override requested | Human approves/rejects |

## Escalation Template

When requesting human intervention, present:

```markdown
## 需要人工介入: {issue title}

**问题描述:**
{clear, concise problem statement}

**已尝试的解决方案:**
1. {attempt 1}
2. {attempt 2}
3. {attempt 3}

**当前状态:**
{context: what's been tried, what's blocked}

**可用选项:**
1. {option 1} — {pros}
2. {option 2} — {pros}
3. {option 3} — {pros}

**建议:**
{controller's recommendation if any}

**影响:**
{what's blocked, what can proceed in parallel}
```

## Configuration

Use `min_iteration_before_human` config:
- Default: 3 iterations
- After this threshold, strongly recommend human review
- Beyond threshold + unresolved = must escalate

## After Human Decision

1. Log decision to `{project-root}/_context/memory/sw-shared/human-interventions.md`
2. Record rationale for future reference
3. Apply decision and proceed
4. Update any affected task statuses

## Knowledge Base Update

If intervention revealed knowledge gaps:
- Note in human-interventions.md
- Suggest knowledge base update after delivery
