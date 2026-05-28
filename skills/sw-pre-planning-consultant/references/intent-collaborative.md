# Intent Analysis: Collaborative (协作任务)

## 核心挑战

Collaborative 意图的独特挑战是 **navigating uncertainty without anchoring too early**。不同于其他意图类型有明确的最终产物，协作任务的成功标准是"用户获得了他们需要的洞察/进展"——这个标准高度主观且不断演化。

两个主要失败模式:
1. **过早收敛 (Premature Convergence)**: AI 在探索不充分时就急于给出确定方案
2. **目标漂移 (Goal Drift)**: 在协作过程中偏离用户的实际关注点

## Phase 1: 增量明晰协议 (Incremental Clarity Protocol)

### 协议原则

Collaborative 任务不要求一次性获得所有信息。使用**渐进式明晰**:

```
Step 1: 理解当前最重要的未知 → 
Step 2: 解决这个未知 → 
Step 3: 基于新理解，确定下一个最重要的未知 →
Repeat
```

每一步只追求解答**一个最重要的未知**。不要试图一次解决所有问题。

### 当前状态诊断

在协作开始时，诊断用户当前所处阶段:

| 阶段 | 信号 | 策略 |
|------|------|------|
| **探索初期** | "I'm thinking about...", "not sure", "maybe", "considering" | 扩展选项空间: 提出可能的方向和视角，不做收敛 |
| **方向选择** | "leaning toward", "probably", "between A and B" | 结构化比较: 明确每个选项的 tradeoffs，帮助决策 |
| **方案细化** | "how exactly", "what's the best way to", "implementation detail" | 深入细节: 提供具体的实现方法和注意事项 |
| **验证确认** | "does this make sense", "what do you think of", "any issues with" | 审查模式: 检查潜在问题、盲点、遗漏 |

### 用户意图追踪

在协作过程中持续追踪:

```
追踪维度:
- 不变目标: 用户始终想要达成的核心目标（即使表述方式改变）
- 变化约束: 随着讨论深入而变化的约束条件
- 已探索方向: 已经讨论过的方向和弃用原因
- 开放问题: 尚未解决的关键不确定性
```

## Phase 2: 职责分工 (Division of Responsibility)

协作任务中的人机职责边界:

| 职责 | 人类 | AI |
|------|------|-----|
| 目标定义 | ✅ 最终决定 | 帮助澄清和结构化 |
| 价值判断 | ✅ 最终决定 | 提供分析框架 |
| 约束条件 | ✅ 最终决定 | 提出未考虑的约束 |
| Trade-off 评估 | ✅ 最终决策 | 列出 trade-off 维度 |
| 技术可行性 | 可以挑战 | ✅ 评估和建议 |
| 替代方案 | 可以提出 | ✅ 搜索和提议 |
| 风险识别 | 可以补充 | ✅ 系统扫描 |
| 实现细节 | 可选 | ✅ 提供和执行 |

关键原则: **人类负责"为什么"和"是什么"，AI 负责"如何做"和"有什么风险"。**

## Phase 3: 通信协议 (Communication Protocol)

### 检查点 (Checkpoints)

在以下节点主动设立检查点:
- 发现关键未知时: "这里有一个关键不确定点: [X]。在继续之前需要明确..."
- 方向选择时: "基于当前讨论，有两个主要方向。需要决定走哪条路..."
- 范围变化时: "这个方向看起来扩展了讨论范围。确认一下: 是否要将 [X] 也纳入?"
- 达到自然停顿点时: "当前阶段似乎任务完成了。下一步是 [X] 还是换个方向?"

### 结构化输出模板

当讨论收敛到一定程度时，提供结构化摘要:

```
## Current Understanding
- **Goal**: [当前理解的目标]
- **Approach**: [当前讨论的方法]
- **Key Decisions Made**: [已做出的关键选择]
- **Open Questions**: [尚未解决的关键问题]

## Next Options
1. [Option A]: [简述] — [何时合适]
2. [Option B]: [简述] — [何时合适]

Which direction should we explore next?
```

### 终止信号

识别何时协作任务应自然结束:

| 信号 | 行动 |
|------|------|
| 用户说 "ok", "got it", "makes sense", "I'll do X" | 确认理解，提供最终摘要，结束 |
| 用户的问题从探索性变为实现性 | 建议转变为其他意图类型 (Mid-sized / Build) |
| 讨论循环超过 3 轮未取得进展 | 提出重新框定问题 |
| 用户反复确认同一问题 | 可能是 AI 未理解 — 换个角度解释 |

## 应问的问题

协作任务的问题应**逐步提出，而非一次全部**:

1. **方向确认** (早期):
   ```
   "当前看来最重要的未知是 [X]。我们先聚焦解决这个?
   还是说你觉得 [Y] 更关键?"
   ```

2. **深度确认** (中期):
   ```
   "当前讨论到 [X] 层面。需要继续深入到实现细节，
   还是这个抽象层面的分析已经足够?"
   ```

3. **产出确认** (后期):
   ```
   "这次讨论是否需要产出什么具体的文档/决策记录?
   还是讨论本身已经达到目标?"
   ```

## Planner Directives for Collaborative Intent

协作意图通常不直接生成 Planner Directives (因为没有具体的执行计划)。但如果协作的结果是需要转为执行:

### 过渡指令

当协作产生具体执行方向时:
```
MUST capture the decisions and rationale from this collaboration session
  in {project-root}/_context/memory/sw-shared/design-decisions.md
  before initiating any implementation.
MUST confirm with user that the captured plan matches their understanding.
SHOULD transition to a Mid-sized Task or Build from Scratch intent with
  the captured plan as input.
```

### 协作过程指令

```
MUST maintain a running summary of key decisions during collaboration.
MUST flag when the discussion drifts from the original topic.
MUST NOT commit to implementation during the collaborative exploration phase.
SHOULD suggest transitioning to a concrete intent when the direction solidifies.
```

## QA / Acceptance Criteria for Collaborative

协作的 QA 不是关于代码产物，而是关于协作质量:

1. **[Check]** 决策记录:
   ```
   验证: 所有关键决策和其理由已被记录
   检查: {project-root}/_context/memory/sw-shared/design-decisions.md
   包含本次协作的所有关键选择
   ```

2. **[Check]** 无遗漏的开放问题:
   ```
   验证: 协作结束时的所有开放问题已被明确标记
   格式: 每个开放问题有明确的下一步 (谁负责、何时、如何解决)
   ```

3. **[Check]** 协作摘要:
   ```
   验证: 最终输出包含结构化的协作摘要
   包含: 目标、决策、替代方案、边界条件
   ```
