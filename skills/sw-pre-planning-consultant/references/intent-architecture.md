# Intent Analysis: Architecture (架构决策)

## 核心挑战

Architecture 意图的独特挑战是决策在不确定条件下做出，且决策的影响面广、持续时间长。AI 在架构场景中有两个倾向性错误:
1. **过度建议新技术**: AI 天然偏向较新的、社区热议的方案
2. **决策无记录**: 做出技术选择但不留下选择理由，导致新团队成员无法理解"为什么当初选了 X"

## Phase 1: 决策边界定义 (Decision Boundary)

### 架构决策 vs 实现细节

不是所有技术选择都是架构决策。判断标准:

| 标准 | 架构决策 | 实现细节 |
|------|---------|---------|
| 可逆性 | 低 — 更改成本高 | 高 — 改几行代码 |
| 影响面 | 宽 — 影响多个模块/团队 | 窄 — 影响单个模块 |
| 约束力 | 强 — 限制未来选择 | 弱 — 不影响其他选择 |
| 需要共识 | 是 | 否 |

示例:
- "选择数据库类型 (SQL vs NoSQL)" → 架构决策
- "选择 ORM 的具体某个方法" → 实现细节
- "选择服务间通信协议 (REST/gRPC/消息)" → 架构决策
- "选择 gRPC 的某个配置参数" → 实现细节

### 决策范围限定

对于每个架构决策，明确:
```
决策: [要决定什么]
范围: [影响哪些系统/模块/团队]
约束: [必须遵守的限制条件]
时间敏感度: [需要在何时之前决定]
可逆性: [单向门 / 双向门]
```

## Phase 2: 战略顾问咨询触发 (Advisor Consultation)

### 何时必须委托 sw-strategic-advisor

以下情况，在 Planner Directives 中 RECOMMEND 后续委托 `sw-strategic-advisor` 深度审查:

| 条件 | 原因 |
|------|------|
| 决策涉及 3+ 个系统的交互 | 交互复杂性超出单个 planner 的分析范围 |
| 存在明显的安全/性能 trade-off | 需要专门的安全/性能视角 |
| 涉及不熟悉的技术栈 | 需要额外的研究深度 |
| 多个方案各有优劣，无明显胜者 | 需要结构化的 trade-off 分析 |
| 决策会影响团队未来 6 个月以上的开发 | 长期影响需要更深度推理 |

### 最小顾问输入

如果触发顾问咨询，确保提供:
```
Delegate to sw-strategic-advisor with:
- Context: [当前架构决策的上下文]
- Options: [考虑的 2-3 个方案]
- Constraints: [已知约束]
- Specific Ask: [需要顾问回答的具体问题 — 不是"评估架构"，而是"方案A对延迟的影响是否可接受?"]
```

## Phase 3: Trade-off 文档化要求

### 决策记录模板 (Decision Record)

每个架构决策 MUST 包含以下字段:

```
## Decision: [决策标题]

### Context
[为什么需要做这个决策? 当前的约束和背景是什么?]

### Options Considered
| Option | Pros | Cons | Cost (Effort) |
|--------|------|------|---------------|
| A      | ...  | ...  | ...           |
| B      | ...  | ...  | ...           |

### Decision
[选择哪个方案]

### Rationale
[为什么选这个? 关键的决定性因素是什么?]

### Consequences
- **Positive**: [选择这个方案带来的好处]
- **Negative**: [选择这个方案的代价、风险、限制]
- **Mitigation**: [如何减轻负面影响]

### Reversibility
[这个决定是可逆的吗? 如果是，回溯成本是多少?]

### Date / Review Trigger
[决策日期 / 什么条件下应该重新审视这个决定?]
```

### 决策记录存储位置

- 存储于: `{project-root}/_context/memory/sw-shared/design-decisions.md`
- 每个决策独立一节，按时间倒序排列
- 使用一致的格式使决策可搜索、可比较

## 应问的问题

1. **约束确认** (必问 — 最高优先级):
   ```
   "这个架构决策的约束条件是什么?
   - 技术约束: 必须兼容的系统、已定的技术栈?
   - 组织约束: 团队技能、维护能力、招聘难度?
   - 时间约束: 需要在什么时间前做出决定? 实施期限?
   - 成本约束: 是否有预算限制?"
   ```

2. **决策可逆性** (高优先级):
   ```
   "这个决策是单向门 (难以逆转) 还是双向门 (可以回头)?
   - 如果难以逆转: 需要更深入的分析和更广泛的 input
   - 如果可以回头: 可以偏向快速决策 + 设置 review checkpoint"
   ```

3. **决策影响面**:
   ```
   "这个决策具体会影响哪些部分?
   - 哪些服务/模块/团队会受影响?
   - 是否存在不同意的潜在 stakeholders?"
   ```

4. **替代方案探索** (如果用户只提了一个方案):
   ```
   "你提到了 [方案A]。在决定之前，是否需要我探索以下替代方案?
   - [基于探索发现的替代方案]
   - [行业常见替代方案]"
   ```

## Planner Directives for Architecture Intent

### MUST 指令

```
MUST document every architecture decision using the Decision Record template.
MUST list at least 2 options for each architecture decision (including "do nothing").
MUST state the constraints before evaluating options.
MUST identify the decision's reversibility (one-way vs two-way door).
MUST NOT commit to implementation without documented decision rationale.
```

### SHOULD 指令

```
SHOULD delegate deep architecture analysis to sw-strategic-advisor when:
  - 3+ systems interact
  - Security/performance trade-offs exist
  - Unfamiliar tech stack involved
SHOULD store decision records in {project-root}/_context/memory/sw-shared/design-decisions.md.
SHOULD set review triggers for reversible decisions (e.g., "revisit in 3 months").
```

### MAY 指令

```
MAY propose a prototype/spike before committing to a full architecture decision.
MAY defer non-critical architecture decisions to implementation phase with explicit notes.
```

## QA / Acceptance Criteria for Architecture

所有验收标准必须 agent-executable:

1. **[Check]** 决策记录完整:
   ```
   验证命令: grep -c "## Decision:" {project-root}/_context/memory/sw-shared/design-decisions.md
   预期: 决策记录数量 >= 本次涉及的架构决策数
   且每个决策包含: Context, Options, Decision, Rationale, Consequences
   ```

2. **[Static Analysis]** 选项数量合规:
   ```
   验证: 每个决策的 Options Considered 表至少包含 2 行
   检查: 是否存在 "do nothing" 或 "defer" 作为显式选项
   ```

3. **[Check]** 约束文档化:
   ```
   验证: 每个决策的 Context 部分包含明确的约束列表
   检查: grep -A 10 "## Decision:" | grep -i "constraint"
   ```

4. **[Script]** 决策影响面验证:
   ```
   检查每个决策是否明确列出了影响的服务/模块
   验证: grep -A 20 "## Decision:" | grep -i "affects\|impacts\|consequences"
   ```

5. **[Check]** 可逆性标记:
   ```
   验证: 每个决策包含 "Reversibility" 部分
   检查: grep -A 20 "## Decision:" | grep -i "reversib"
   ```
