# 交接协议 (Handoff Protocol)

当计划生成完成并通过自审查（及可能的高精度审查）后，执行交接协议。这是从 "规划" 到 "执行" 的转变。

---

## 交接前完成检查清单

在向用户呈现计划之前，完成以下所有检查:

```
□ 计划文件存在于 _bmad/memory/hw-shared/plans/{plan-name}.md
□ 计划文件包含所有 9 个必需章节
□ 所有 TODOs 具有 WHAT TO DO + QA SCENARIOS
□ 所有 QA SCENARIOS 具有具体工具 + 步骤 + 断言 + 证据路径
□ 所有 QA SCENARIOS 包含 BOTH happy path + failure scenario
□ 零 [DECISION NEEDED] 占位符残留（所有 CRITICAL 缺口已解决）
□ 自审查已完成（缺口已分类处理）
□ 如果 High Accuracy: Momus 返回了 OKAY
□ 草稿文件仍存在（将在交接后删除）
```

---

## Step 1: 呈现计划摘要

向用户呈现结构化的计划摘要。不要只转储文件路径——让用户能够快速做出明智的决策。

### 摘要格式

```
## Plan Generated: {plan-name}

### TL;DR
{从计划的 TL;DR section 复制的 1-2 句话}

### Key Decisions Made
- **[Decision 1]**: [1 句理由]
- **[Decision 2]**: [1 句理由]
- **[Decision 3]**: [1 句理由]

### Scope
**IN**:
- [Item 1]
- [Item 2]
- [Item 3]

**OUT** (Explicit Exclusions):
- [Item 1]
- [Item 2]

### Guardrails Applied
- [Guardrail 1 — 来自 Metis 审查]
- [Guardrail 2 — 来自 Metis 审查]
- [Guardrail 3 — 来自你的分析]

### Auto-Resolved (minor gaps fixed silently)
- **[Gap 1]**: [How resolved]
- **[Gap 2]**: [How resolved]

### Defaults Applied (override if needed)
- **[Default 1]**: [What was assumed. User can override.]
- **[Default 2]**: [What was assumed. User can override.]

### Decisions Needed from User (if any)
- **[Question 1]**: [Context and options]
- **[Question 2]**: [Context and options]

### Plan Stats
- **Tasks**: {N} total
- **Waves**: {N} parallel waves
- **Est. Effort**: [Quick | Short | Medium | Large | XL]
- **Max Parallel**: {N} tasks (Wave {X})
- **Critical Path**: {N} tasks ({N} sequential dependencies)

### Files
- **Plan**: _bmad/memory/hw-shared/plans/{plan-name}.md
- **Draft**: _bmad/memory/hw-shared/drafts/{name}.md (will be deleted on handoff)
```

---

## Step 2: 呈现选择（MANDATORY）

向用户呈现两个选择。这必须是一个明确的二选一:

```
## Plan is Ready. How would you like to proceed?

### Option A: Start Work
Execute the plan now. This will delegate to hw-plan-executor which will:
- Register the plan as your active work boulder
- Execute tasks wave by wave with maximum parallelism
- Run QA scenarios and capture evidence
- Track progress across sessions
- Enable automatic continuation if interrupted

### Option B: High Accuracy Review
Have hw-plan-reviewer rigorously verify every detail:
- 100% file references verified
- All tasks executable without additional context
- All QA scenarios have concrete tools + steps + assertions
- Zero contradictions or missing dependencies

This adds a review loop but guarantees precision. Momus will reject the plan
if any issues are found. You fix and resubmit until OKAY.

---

Which do you prefer?
```

如果用户选择 **Option A** → 跳转到 Step 4（交接执行）。

如果用户选择 **Option B** → 进入高精度审查循环。加载 `references/high-accuracy-mode.md`。

---

## Step 3: 高精度审查循环（如果选择 Option B）

参见 `references/high-accuracy-mode.md` 获取完整协议。

当 Momus 返回 OKAY 后，返回 Step 1——重新呈现摘要（因为计划可能在审查循环中被修改）。

---

## Step 4: 交接执行

### 4a. 删除草稿文件（MANDATORY）

草稿已完成其目的。清理:

```
Delete "{project-root}/_bmad/memory/hw-shared/drafts/{name}.md"
```

**为什么删除**:
- 计划现在是唯一的真相源
- 草稿是工作记忆，不是永久记录
- 防止草稿和计划之间的混淆
- 保持 drafts/ 目录为下次规划会话清洁

### 4b. 引导用户运行 hw-plan-executor

```
Plan saved to: _bmad/memory/hw-shared/plans/{plan-name}.md
Draft cleaned up: _bmad/memory/hw-shared/drafts/{name}.md (deleted)

To begin execution, delegate to hw-plan-executor with the plan path:
  hw-plan-executor _bmad/memory/hw-shared/plans/{plan-name}.md

This will:
1. Register the plan as the active work scope
2. Execute tasks wave by wave with maximum parallelism
3. Run all QA scenarios and capture evidence to _bmad/memory/hw-shared/evidence/
4. Present results after each wave
5. Enable session recovery if interrupted
```

### 4c. 最终状态更新

更新规划者私有状态:

```
{project-root}/_bmad/memory/hw-strategic-planner/planning-state.yaml:
  last_plan: {plan-name}.md
  completed_at: {timestamp}
  review_mode: [none | high-accuracy]
  review_iterations: {N}
  handoff_to: hw-plan-executor
```

---

## 轮次终止：交接完成

交接完成后的最后一个轮次必须以此结束（符合 Turn Termination Rules）:

```
Plan complete. Ready for execution.

Next action: Delegate to hw-plan-executor with the plan path.
```

**绝不**以 "有问题随时问我" 结束。交接完成意味着你的工作已完成——引导用户到下一步。

---

## 交接反模式

### NEVER

- 在没有计划摘要的情况下直接说 "计划已保存"
- 跳过两种选择的呈现
- 保留草稿文件（它会混淆执行者和未来的规划会话）
- 在 Momus 审查 OKAY 之前启动执行
- 对于 High Accuracy 模式: 呈现计划而不启动审查循环

### ALWAYS

- 呈现结构化摘要
- 提供两个明确的选择
- 删除草稿文件
- 引导用户到 hw-plan-executor
- 以明确的下一步结束
