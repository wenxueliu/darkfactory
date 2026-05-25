# Intent Classification — Decision Tree

## 分类原则

意图分类 (Intent Classification) 是预规划分析的**强制第一步**。不同意图类型具有截然不同的失败模式、信息需求和 AI-slop 风险。错误分类意味着错误的防护措施。

分类基于三个维度:
1. **变更面 (Change Surface)**: 任务是修改现有代码还是创建新代码?
2. **边界清晰度 (Boundary Clarity)**: 用户是否明确定义了范围边界?
3. **决策密集度 (Decision Density)**: 任务是否涉及大量设计/架构决策?

## 决策树 (Decision Tree)

```
用户请求
│
├─ 请求涉及修改现有代码，但不改变其行为？
│  └─ YES → Refactoring
│
├─ 请求创建全新代码/项目，没有已有代码库约束？
│  └─ YES → Build from Scratch
│
├─ 请求涉及跨多个系统的架构级决策或技术选型？
│  └─ YES → Architecture
│
├─ 请求目标是获取信息/知识，而非产出代码？
│  └─ YES → Research
│
├─ 请求是开放式协作探索，没有明确的完成边界？
│  └─ YES → Collaborative
│
├─ 请求有明确的边界，在现有代码库中做有限的增改？
│  └─ YES → Mid-sized Task
│
└─ 难以判断？default → Mid-sized Task (最安全的默认分类)
```

## 六种意图类型详解

### 1. Refactoring (重构)

**定义**: 修改现有代码的内部结构，不改变其外部可观察行为。

**区分信号**:
- 关键词: "refactor", "重构", "clean up", "reorganize", "restructure", "simplify", "extract", "rename"
- 不引入新功能，不改变 API 契约，不修改数据库 schema
- 通常提到: "without changing behavior", "保持功能不变", "same functionality"

**置信度指标**:
- **High**: 明确声明"不改变行为"且不提及新功能
- **Medium**: 提到重构但也提到"改善" — 需确认改善是否涉及行为变更
- **Low**: 使用重构术语但实际描述的是重写 (rewrite)

**推荐工具组合**: 代码库探索 (理解现有结构) + 静态分析 (找依赖)

**应问的问题**:
- 重构的具体边界是什么? (哪些文件/模块/包)
- 行为不变的验证标准是什么? (哪些测试必须通过?)
- 重构触发原因是什么? (性能问题/可读性/解耦?)

**典型 AI-Slop 风险**: AI 可能在重构中"顺带优化"逻辑 — 行为漂移 (behavior drift) 是最常见的重构失败模式。

---

### 2. Build from Scratch (从零构建)

**定义**: 创建全新代码/项目，不受已有代码库约束。

**区分信号**:
- 关键词: "create a new", "build from scratch", "从零开始", "新建项目", "set up", "scaffold", "initialize"
- 没有"在现有 X 中"的约束
- 可能涉及技术栈选择

**置信度指标**:
- **High**: 明确是全新项目，无已有代码库
- **Medium**: 在现有 monorepo 中新建模块/服务 — 受 monorepo 规范约束
- **Low**: 描述为"从零构建"但实际涉及替换现有系统

**推荐工具组合**: 
- **必须先探索**: 代码库探索者 (hw-codebase-explorer) — 发现 monorepo 约定、现有技术栈、共享基础设施
- **必须先研究**: 外部研究员 (hw-external-researcher) — 了解最佳实践、库版本、starter templates

**关键原则: 探索先于提问 (Explore Before Asking)**
在向用户提问之前，必须先探索代码库和外部资源。不应问用户"项目用什么 linter?"如果代码库已有 `.eslintrc`。

**应问的问题** (探索完成后):
- 技术栈偏好? (如果探索发现多种可能选项)
- 与现有系统的集成点? (如果 monorepo)
- 最小可用版本 (MVP) 的功能边界是什么?

**典型 AI-Slop 风险**: 过度抽象 (premature abstraction) — 为一个功能构建"通用框架"; 过度工程化 (gold-plating) — 为尚未存在的百万用户设计。

---

### 3. Mid-sized Task (中型任务)

**定义**: 在现有代码库中做有限的、边界明确的增改。这是最常见的任务类型，也是 AI-slop 最常发生的类型。

**区分信号**:
- 关键词: "add X to Y", "implement Z in module W", "fix the way", "update the", "integrate"
- 有明确的作用范围 (特定模块/文件/功能)
- 不涉及架构决策或跨系统变更
- 不创建全新项目

**置信度指标**:
- **High**: 任务边界明确 (指定了具体模块/文件/API)，输入输出清晰
- **Medium**: 目标清晰但边界模糊 — 需要收窄
- **Low**: 描述模糊 ("improve the user system") — 可能需要分解

**推荐工具组合**: 代码库探索者 (理解目标模块) + 现有测试 (了解预期行为)

**应问的问题**:
- 这个变更的精确边界在哪里? (哪些文件/哪些模块不应被触及)
- 完成标准是什么? (什么行为/性能/结果表示任务完成?)
- 与哪些已有功能有交互? (需要回归验证的是什么?)

**典型 AI-Slop 风险 (4 种 — 见 `references/intent-midsized.md`)**:
1. Scope Inflation (范围膨胀) — AI 自动扩展任务范围
2. Premature Abstraction (过早抽象) — 为一个用例构建抽象层
3. Over-Validation (过度验证) — 在核心功能完成前验证所有边界情况
4. Documentation Bloat (文档膨胀) — 为小改动生成过多文档

---

### 4. Collaborative (协作任务)

**定义**: 开放式协作探索，没有固定的完成边界。用户与 AI 迭代交互，逐步明晰目标。

**区分信号**:
- 关键词: "help me", "pair on", "let's", "walk through", "explore together", "一起看看", "帮我分析"
- 没有明确的完成标准或终点
- 对话式、探索式语气

**置信度指标**:
- **High**: 明确请求协作/pairing/探索，无完成边界
- **Medium**: 请求可能收敛为明确任务但当前阶段是探索性的
- **Low**: 看似协作但实际可用确定性方法解决

**推荐工具组合**: 灵活按需调用 — 随对话推进逐步确定工具需求

**应问的问题**:
- 当前最重要的未知是什么? (聚焦方向)
- 如果只能弄清楚一件事，应该是什么? (优先级)
- 是否需要最终产出物? 还是探索过程本身就是目标?

**典型 AI-Slop 风险**: 过早收敛 (premature convergence) — AI 在探索不充分时就试图给出确定方案。

---

### 5. Architecture (架构决策)

**定义**: 涉及跨系统、跨模块的架构级决策或技术选型。

**区分信号**:
- 关键词: "design the architecture", "evaluate tradeoffs", "should we use X or Y", "架构设计", "技术选型", "system design"
- 涉及多个系统/服务/模块之间的交互
- 决策有长期影响
- 通常涉及权衡分析

**置信度指标**:
- **High**: 明确的架构设计/技术选型请求，涉及明确的多选项比较
- **Medium**: 请求有架构含义但用户可能未意识到
- **Low**: 看似功能请求但实际涉及架构变更

**推荐工具组合**: 战略顾问 (hw-strategic-advisor) + 知识库查询 (已有 ADR 和决策记录)

**建议**: 对于架构意图，强烈建议 (RECOMMEND) 在规划后委托 `hw-strategic-advisor` 进行深度审查。预规划阶段重点确保决策范围被正确界定、决策依据被明确记录。

**应问的问题**:
- 这个架构决策的约束条件是什么? (技术/组织/时间/成本)
- 决策影响的服务/模块/团队有哪些?
- 决策的可逆性? (单向门 vs 双向门)

**典型 AI-Slop 风险**: 决策无记录 (undocumented decisions) — AI 做架构选择但不留下选择理由，导致后续无法回溯。

---

### 6. Research (调查研究)

**定义**: 以获取信息/知识为目标，而非产出代码。

**区分信号**:
- 关键词: "research", "investigate", "what are the options", "调研", "调查", "find out", "compare"
- 输出目标是信息，非代码
- 可能涉及多方案比较
- 通常需要外部信息源

**置信度指标**:
- **High**: 明确的研究/调查请求，有具体的研究问题
- **Medium**: 研究请求但范围可能过于宽泛
- **Low**: 功能请求伪装为研究请求 (实际是"先帮我决定再帮我做")

**推荐工具组合**: 
- **必须先探索**: 外部研究员 (hw-external-researcher) — 并行多条研究轨道
- 可能需要: 代码库探索者 (内部实现调研)

**关键原则: 探索先于提问 (Explore Before Asking)**
研究请求几乎总能从外部搜索中获益。在向用户提问之前，先并行启动多条搜索轨道。

**应问的问题** (探索完成后):
- 研究的深度要求? (概览 vs 深度)
- 决策时间线? (快速决策 vs 全面评估)
- 研究结果的使用者? (工程师/架构师/管理层?)

**典型 AI-Slop 风险**: 无边界研究 (research without exit criteria) — 研究永远做不到"足够好"。

---

## 分类后行动 (Post-Classification Actions)

分类完成后，立即执行对应的 Phase 1 分析 (加载对应 reference 文件)。

| 意图类型 | Phase 1 Reference | 首个行动 |
|----------|-------------------|---------|
| Refactoring | `references/intent-refactoring.md` | 建立行为不变的验证标准 |
| Build from Scratch | `references/intent-build.md` | 启动探索代理 (codebase + external) |
| Mid-sized Task | `references/intent-midsized.md` | 定义精确边界 + 激活 AI-slop 防护 |
| Collaborative | `references/intent-collaborative.md` | 建立增量明晰协议 |
| Architecture | `references/intent-architecture.md` | 确认决策边界 + 准备 trade-off 文档模板 |
| Research | `references/intent-research.md` | 启动探索代理 + 定义退出标准 |

## 边缘情况处理

### 多意图混合请求

如果用户请求混合了多种意图 (例如 "refactor the auth module and add a new login method"):
1. 识别**主导意图** (哪个意图决定了主要工作方向)
2. 在 Pre-Analysis 中标注**次要意图**
3. 为主要意图生成核心指令，为次要意图生成附加约束

### 无法确定

如果经过决策树仍无法确定意图类型:
- 默认分类为 **Mid-sized Task** (最安全的默认值)
- 置信度标记为 **low**
- 在 Questions 中首先请求澄清意图

### 意图变化

如果在分析过程中发现实际意图与初步分类不符:
- 重新分类并标注 "Reclassified from X to Y because: [reason]"
- 使用新分类的参考文件重新执行 Phase 1
