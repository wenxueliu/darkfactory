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
| Context Agent | Missed requirements, background knowledge | `reviews/{task_id}-context.md` |

### Review Inputs

Before dispatching, collect the inputs each reviewer needs:

| Reviewer | Needs |
|----------|-------|
| Security / Logic / Performance | Changed files, diff, full file contents |
| Context | Changed files, task goal/requirements, constraints (from tasks.yaml). The context agent searches git/GitHub/Slack/codebase itself — it does NOT need file contents in the prompt. |

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
1. Log conflict to `{project-root}/_context/memory/sw-shared/reviews/{task_id}-conflicts.md`
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

## Knowledge Base Update: P3 发现沉淀为经验教训

在所有 P0/P1/P2 问题解决后，检查是否有值得记录为经验教训的 P3 发现。

### P3 筛选标准

- **值得记录的候选项:** 可能在其他模块重复出现的通用模式、配置或依赖的最佳实践、容易遗漏的边缘案例提醒、在扩散前被及时制止的反模式
- **跳过的:** 一次性命名建议（如"rename this variable for readability"）、纯代码风格偏好

### 提取流程

1. 读取审查结果文件:
   - `reviews/{task_id}-logic.md`
   - `reviews/{task_id}-security.md`
   - `reviews/{task_id}-performance.md`
   - `reviews/{task_id}-context.md`

2. 解析 severity 列为 `P3` 的行，从表列中提取 Issue、Location 和 Recommendation。
   - 上下文审核的 P3 可能包含文档更新建议和后续任务创建建议。

3. 对每个符合条件的 P3 发现，调用 kb-log.py 创建 lesson 条目:

   ```bash
   python scripts/kb-log.py lesson "(P3) {简短模式名}" \
     --author "sw-worktree-controller" --stdin <<'EOF'
   ## Summary
   {从 P3 Issue 标题提炼的一句话描述}
   ## Details
   {从 Issue Details 中提取的完整描述，包含代码示例和修复建议}
   ## Context
   在 {review_type} 审查任务 {task_id} 时发现。严重级别: P3（建议，非阻塞）。
   ## Usage
   {从 Recommendation 列提炼的指导——未来开发中应如何应用此模式}
   ## Related
   - 审查报告: reviews/{task_id}-{type}.md
   EOF
   ```

   先使用 `--dry-run` 预览条目内容，确认后再正式写入。

4. 如果 P3 发现数量为 0，或者筛选后无可复用价值，则跳过本步骤。

5. 对每个审核类型（logic / security / performance / context）独立执行——逻辑审查的 P3 和上下文挖掘的 P3 可能分别沉淀为不同领域的经验教训。

### Config 控制

当 `sw.knowledge_base_auto_update` 为 false 时跳过本步骤，直接进入状态报告。

## Transition

Code review is complete when:
1. All enabled reviewers have completed
2. All P0/P1/P2 issues resolved or escalated
3. Human has resolved any architecture conflicts
4. P3 lessons extracted to knowledge base (if applicable per config)
