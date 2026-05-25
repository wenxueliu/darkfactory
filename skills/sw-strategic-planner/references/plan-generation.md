# 计划生成 (Plan Generation)

Phase 2: 当清关清单全部通过或用户明确触发时，自动过渡到计划生成。这是从 "访谈和收集" 到 "构建和交付" 的转变。

---

## 触发条件

### 自动过渡 (AUTO-TRANSITION)

当自我清关清单全部 6 项通过时，**自动**进入计划生成阶段。

```
清关清单 ALL YES → 立即过渡到计划生成
```

### 明确触发 (EXPLICIT TRIGGER)

用户说以下任一项时:
- "生成计划" / "Create the work plan" / "Make it into a work plan"
- "保存为文件" / "Save it as a file" / "Generate the plan"
- "开始规划" / "Proceed with planning"

**任一触发立即激活计划生成。**

---

## Step 1: 注册 Todo List（MANDATORY — 立即执行）

**检测到触发条件后，第一个动作必须是注册以下 8 项步骤：**

使用 TodoWrite 注册以下步骤（以项目支持的 todo 追踪方式）:

```
Todo Items (计划生成):

1. [plan-1] Consult hw-pre-planning-consultant for gap analysis (auto-proceed)
   状态: pending → 立即标记为 in_progress

2. [plan-2] Build plan skeleton with ALL sections (no individual tasks yet)
   状态: pending

3. [plan-3] Write skeleton to plan file (single Write call)
   状态: pending

4. [plan-4] Edit-append tasks in batches of 2-4 (incremental write)
   状态: pending

5. [plan-5] Read-back verification after each batch
   状态: pending

6. [plan-6] Self-review: classify gaps (CRITICAL/MINOR/AMBIGUOUS)
   状态: pending

7. [plan-7] Present summary: Key Decisions, Scope, Guardrails, Auto-Resolved, Defaults, Decisions Needed
   状态: pending

8. [plan-8] Present choice: Start Work vs High Accuracy Review
   状态: pending
```

### 为什么注册 Todo List 至关重要

- 用户确切看到还剩下哪些步骤
- 防止跳过关键步骤（如 hw-pre-planning-consultant 咨询）
- 为每个阶段创建责任感
- 如果会话中断，可以从断点恢复

### 工作流

1. 触发检测到 → **立即** TodoWrite (plan-1 到 plan-8)
2. plan-1 标记为 in_progress → 咨询 hw-pre-planning-consultant（自动进行，不需要用户确认）
3. plan-2 标记为 in_progress → 构建计划骨架
4. plan-3 标记为 in_progress → 写入骨架到计划文件
5. plan-4 标记为 in_progress → 分批追加任务（边追加边标记进度）
6. plan-5 随 plan-4 一起进行 → 每批后验证
7. plan-6 标记为 in_progress → 自审查和缺口分类
8. plan-7 标记为 in_progress → 呈现摘要
9. plan-8 标记为 in_progress → 提供选择

**绝不跳过一个 todo。绝不未更新状态就继续。**

---

## Step 2: hw-pre-planning-consultant 缺口分析（MANDATORY）

**在生成计划之前**，必须调用 hw-pre-planning-consultant 来捕获你可能遗漏的内容:

```
调用 hw-pre-planning-consultant:
"审查本次规划会话，在我生成工作计划之前:

**用户目标**: {summary of what user wants}

**我们讨论了什么**:
{key points from interview}

**我的理解**:
{your interpretation of requirements}

**研究发现**:
{key discoveries from codebase-explorer and external-researcher}

请识别:
1. 我应该问但没有问的问题
2. 需要明确设置的 Guardrails
3. 潜在的范围蔓延区域需要锁定
4. 我做出的需要验证的假设
5. 缺失的验收标准
6. 未处理到的边缘情况"
```

### hw-pre-planning-consultant 调用规则

- **同步调用（blocking）** — 等待结果返回后才继续
- **不跳过** — 即使你觉得访谈非常全面也不能跳过
- **自动进行** — 不需要先问用户 "是否要咨询 Metis"（这已在 plan-1 中声明）
- **不基于 Metis 的结果重新提问** — 将 Metis 的发现静默融入你的理解中，除非 Metis 返回了 CRITICAL 级别缺口（需要用户决策）

### 处理 Metis 的反馈

| Metis 发现类型 | 处理方式 |
|---------------|---------|
| CRITICAL: 需要用户决策的问题 | 在计划中使用 [DECISION NEEDED: description] 占位符，在摘要中列出 |
| MINOR: 可自行解决的缺口 | 静默修复，在摘要中列入 "Auto-Resolved" |
| AMBIGUOUS: 有合理默认值的缺口 | 应用合理的默认值，在摘要中列入 "Defaults Applied" |
| GUARDRAIL: 需要设置的约束 | 融入 Must NOT Have section |
| QA GAP: 缺失的验收标准 | 在相应任务中补充 |

---

## Step 3: 构建计划骨架

在调用 Metis 并获得结果后，构建计划文件的完整骨架。加载 `references/plan-template.md` 获取精确的章节结构和格式。

### 骨架包含以下所有章节（但不含单个任务的细节）:

```markdown
# {Plan Title}

## TL;DR
> [summary + deliverables + effort + parallelism + critical path]

## Context
### Original Request
### Interview Summary
### Research Findings
### Pre-Planning Review (Metis)

## Work Objectives
### Core Objective
### Concrete Deliverables
### Definition of Done
### Must Have
### Must NOT Have (Guardrails)

## Verification Strategy
### Test Decision
### QA Policy

## Execution Strategy
### Parallel Execution Waves (structure only)
### Dependency Matrix (structure only)
### Agent Dispatch Summary (structure only)

---

## TODOs

---

## Final Verification Wave
### F1. Plan Compliance Audit
### F2. Code Quality Review
### F3. Real Manual QA
### F4. Scope Fidelity Check

## Commit Strategy

## Success Criteria
```

---

## Step 4: 写入骨架到计划文件（单次 Write）

将骨架一次性写入计划文件。这是**唯一一次**使用 Write 操作:

```
Write("{project-root}/_bmad/memory/hw-shared/plans/{plan-name}.md", skeletonContent)
```

`{plan-name}` 命名规则:
- kebab-case, 描述性
- 示例: `jwt-authentication-plan.md`, `refactor-user-module.md`, `dark-mode-feature.md`
- 如果有重名，追加数字: `dark-mode-feature-2.md`

**FORBIDDEN**: 第二次对同一文件使用 Write —— 第二次 Write 会完全覆盖第一次的内容。

---

## Step 5-7: 增量写入协议 (Incremental Write Protocol)

这是**最关键的步骤**。计划包含大量任务时，一次性生成所有内容会超出输出 token 限制。必须分批追加。

### 增量写入规则

1. **仅一次 Write** — 骨架（已在 Step 4 完成）
2. **多次 Edit** — 任务分批追加（每批 2-4 个任务）
3. **每次 Edit 后 Read** — 验证追加内容完整性

### 追加锚点

使用 Final Verification Wave section 作为追加锚点。每次 Edit 在 Final Verification Wave 之前插入新的任务批次:

```
Edit("{project-root}/_bmad/memory/hw-shared/plans/{plan-name}.md",
  oldString="---\n\n## Final Verification Wave",
  newString="- [ ] {N}. {Task Title}\n\n  **What to do**: ...\n  **QA Scenarios**: ...\n\n- [ ] {N+1}. {Task Title}\n\n  **What to do**: ...\n  **QA Scenarios**: ...\n\n---\n\n## Final Verification Wave")
```

### 批次大小规则

| 任务复杂度 | 每批任务数 | 理由 |
|-----------|-----------|------|
| Simple (每任务 <500 words) | 3-4 个 | 平衡速度与输出限制 |
| Medium (每任务 500-1000 words) | 2-3 个 | 避免内容截断 |
| Complex (每任务 >1000 words) | 1-2 个 | 确保完整性 |

### 每批后的验证步骤

每次 Edit 追加后:
```
Read("{project-root}/_bmad/memory/hw-shared/plans/{plan-name}.md", offset={last known line})
```

验证:
- [ ] 新任务已出现在文件中
- [ ] QA Scenarios 完整（happy path + failure scenario）
- [ ] 没有内容截断
- [ ] References 完整
- [ ] Checkbox 格式正确

### 完整追加流程示例

```
批次 1: Edit 追加 Tasks 1-3 → Read 验证 → 确认
批次 2: Edit 追加 Tasks 4-6 → Read 验证 → 确认
批次 3: Edit 追加 Tasks 7-9 → Read 验证 → 确认
...
批次 N: Edit 追加最后批次 → Read 验证 → 确认 → 进入自审查
```

---

## Step 8: 自审查 (Self-Review)

所有任务写入完成后，进行自审查。目标: 发现缺口并在呈现给用户之前分类处理。

### 缺口分类 (Gap Classification)

| 级别 | 定义 | 处理方式 |
|------|------|---------|
| **CRITICAL** — 需要用户输入 | 商业逻辑选择、技术栈偏好、不明确的需求 | 在计划中放入 [DECISION NEEDED: ...] 占位符，在摘要中列出，提出具体问题 |
| **MINOR** — 可自行解决 | 通过搜索找到的缺失文件引用、明显的验收标准 | 立即在计划中修复，在摘要中列入 "Auto-Resolved" |
| **AMBIGUOUS** — 有合理默认值 | 错误处理策略、命名约定 | 应用合理默认值，在摘要中列入 "Defaults Applied" |

### 自审查清单

```
□ 所有 TODO 项具有具体的验收标准？
□ 所有文件引用在代码库中存在？
□ 没有基于证据的关于商业逻辑的假设？
□ Metis 审查中的 Guardrails 已融入？
□ 范围边界已在 Must Have / Must NOT Have 中明确定义？
□ 每个任务都有 Agent-Executed QA Scenarios（不仅仅是测试断言）？
□ QA scenarios 包含 BOTH happy-path AND negative/error scenarios？
□ 零验收标准需要人工干预？
□ QA scenarios 使用具体的选择器/数据，而非模糊描述？
□ 每个任务都有 References section（告诉执行者看哪里、为什么）？
```

### 缺口处理协议

**如果缺口是 CRITICAL（需要用户决策）:**
1. 在计划中放置占位符: `[DECISION NEEDED: {description}]`
2. 在摘要中列入 "Decisions Needed"
3. 提出具体问题并附带选项
4. 收到用户回答后 → 静默更新计划 → 继续

**如果缺口是 MINOR（可自行解决）:**
1. 立即在计划中修复
2. 在摘要中列入 "Auto-Resolved"
3. 无需提问——继续

**如果缺口是 AMBIGUOUS（有合理默认值）:**
1. 应用合理默认值
2. 在摘要中列入 "Defaults Applied"
3. 用户可以后续覆盖——不需要等待

---

## 计划生成阶段的反模式

### NEVER
- 跳过低谷分析（hw-pre-planning-consultant）
- 多次 Write 到同一计划文件
- 一次性生成所有任务（超出输出限制）
- 不追加以验证追加完整性
- 跳过自审查
- 将计划拆分为多个文件

### ALWAYS
- 触发后立即注册 TodoWrite
- 先咨询 hw-pre-planning-consultant
- 骨架一次写入，任务分批追加
- 每批后验证完整性
- 自审查后分类缺口
- 单一计划文件包含所有内容
