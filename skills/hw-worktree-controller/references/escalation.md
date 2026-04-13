# 人工介入请求

## What Success Looks Like

Escalations are clear, actionable, and contain everything needed for human to make a decision quickly.

## When to Escalate

| Condition | Action |
|-----------|--------|
| Max iterations reached | Must escalate |
| Architecture conflict | Must escalate |
| Merge conflict (complex) | Must escalate |
| Human override requested | Should escalate |
| P0 issue | Must escalate immediately |

## Escalation Template

```markdown
## 需要人工介入: {issue title}

**任务:** {task_id}
**工作树:** {worktree}

**问题描述:**
{clear, concise description}

**已尝试的解决方案:**
1. {attempt 1} — {result}
2. {attempt 2} — {result}
3. {attempt 3} — {result}

**迭代历史:**
- 迭代次数: {n} / {max}
- 问题持续时间: {duration}

**当前状态:**
- 阻塞: {yes/no}
- 可并行的任务: {list}

**可用选项:**
1. {option 1} — {pros}
2. {option 2} — {pros}
3. {option 3} — {pros}

**建议:**
{controller's recommendation}

**影响:**
- 阻塞: {what's blocked}
- 风险: {what could go wrong}
```

## After Human Decision

1. Log to `{project-root}/_bmad/memory/hw-shared/human-interventions.md`
2. Apply the decision
3. Update task status
4. Continue execution

## Anti-Patterns

- **Don't escalate too early** — Waste human attention
- **Don't escalate vague issues** — Human can't help without specifics
- **Don't hide what was tried** — Human needs to know what's been attempted
