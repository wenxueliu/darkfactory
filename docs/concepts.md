# 核心概念 (Core Concepts)

> **初次接触？** 先看 [README.md](../README.md) 了解项目概览，[quickstart.md](quickstart.md) 完成首次设置。本文解释黑灯工厂的核心设计理念和工作原理。

---

## Harness Engineering 核心思想

黑灯工厂 (Black-light Factory) 是 **Harness Engineering** 理念的落地实现：

| 原则 | 说明 |
|------|------|
| **Human in the loop** | 人类负责价值判断、战略决策、最终审核；AI 负责执行、审查、验证 |
| **Agent orchestration** | 多 Agent 协同工作，每个 Agent 有明确的职责边界和通信协议 |
| **Gate-driven quality** | 质量门禁不可妥协，每个阶段必须通过验收标准才能推进 |
| **Knowledge accumulation** | 每次开发都沉淀为可复用的知识，知识库随项目持续增长 |

系统遵循**验收驱动开发（Acceptance-driven Development）**，核心铁律：无失败测试不写产品代码。

### 多语言支持

- **编程语言无关** — Agent 不绑定特定编程语言。TDD Agent 适配 pytest/Jest/JUnit/Go test 等主流框架；Reviewer Agent 按语言加载对应的审查模式。新增语言只需扩展 `references/` 下的模式文件。
- **自然语言灵活切换** — 通过 `_context/config.user.yaml` 的 `communication_language` 控制。可切换为 `English`/`Japanese`/`Korean` 等。
- **业务场景快速适配** — 通过 `_context/config.yaml` 配置不同业务领域，无需修改 Agent 代码。

### 配置驱动的业务适配

| 适配维度 | 机制 | 示例 |
|----------|------|------|
| 技术栈 | `references/` 按语言加载模式文件 | Python 项目加载 `references/patterns-python.md` |
| 质量策略 | `enabled_reviewers` 配置 | 金融项目启用 security+logic；内部工具仅启用 logic |
| 流程节奏 | `min_iteration_before_human` | 探索性项目设高值；关键项目设低值 |
| 知识领域 | `knowledge-base/` 结构定制 | 微服务项目强化 `api-contracts/` |
| 交付策略 | `merge_strategy` | 持续部署用 `rebase`；保守团队用 `merge` |
| 自然语言 | `communication_language` | 中文/英文/日文团队，切换即用 |

---

## 开发流程 (Development Flow)

```
ideation → design → decomposition → execution → merge → test → delivery
```

每个阶段转换必须通过验收标准验证。未通过质量门禁的阶段不能推进。人类判断是最终安全阀——当迭代次数达到上限时升级到人工；未解决的 P0/P1/P2 问题不能推进。

### 需求生命周期跟踪 (Requirement Lifecycle Tracking)

每个需求从 ideation 到 delivery 的全生命周期状态记录在 `_context/memory/sw-shared/requirements-tracker.yaml` 中。该文件是 **sw-controller 判断阶段转换的权威数据源**。

**跟踪维度：**

| 维度 | 字段 | 更新者 |
|------|------|--------|
| 当前阶段 | `current_phase` | 各阶段 Agent 完成时更新 |
| 阶段状态 | `phases.<phase>.status` | pending / in_progress / done / blocked / skipped |
| 产出物清单 | `phases.<phase>.artifacts` | 每个阶段完成后记录产物文件路径 |
| 执行进度 | `phases.execution.progress` | sw-plan-executor 每 wave 更新 tasks_done/worktrees_active |
| 整体状态 | `status` | 自动推导（任一 blocked→blocked，任一 in_progress→active，全部 done→done） |

**8 个跟踪阶段与 pipeline 对应关系：**

```
ideation → value_assessment → design → decomposition → execution → merge → test → delivery
   ↑              ↑              ↑           ↑             ↑          ↑       ↑        ↑
  需求澄清      价值评估       特性设计    任务拆分      计划执行    分支合并  集成测试  交付管理
```

**与 harness_framework 的分工：**
- `requirements-tracker.yaml` 记录**需求级**阶段状态和进度快照，给人看、给 sw-controller 做决策
- Consul KV 记录**任务级**实时状态（BLOCKED/PENDING/IN_PROGRESS/DONE），给 Aggregator/Watchdog 做调度和故障恢复
- 二者通过 `dependencies.json`（sw-task-decomposer 导出）和 Consul KV 状态变更事件串联

---

## 问题严重级别

| Level | 名称 | 行动 |
|-------|------|------|
| P0 | Fatal | 必须修复，阻止所有阶段 |
| P1 | Severe | 必须修复，阻止下一阶段 |
| P2 | General | 必须修复，阻止下一阶段 |
| P3 | Suggestion | 仅记录 |

---

## 关键设计模式

### Intent Gate（意图门禁）

每次激活以意图验证开始：分类请求类型、检查歧义、路由到合适的 Agent 层。只有同时满足以下条件才执行：存在明确的实施动词、范围具体、没有待处理的专项结果。

### Autonomous Execution（自主执行）

"不要问——直接做。"TDD Agent 在提问前穷尽探索层级（直接工具 → 代码搜索 → 外部调研 → 上下文推理）。遇到阻塞时尝试不同方法而非停止。

### Structured Planning（结构化规划）

规划遵循「访谈 → 调研 → 计划生成 → 审查」流程。草稿在轮次间充当工作记忆。计划包含可 Agent 执行的 QA 场景（无"用户手动测试"标准）。

### Parallel Orchestration（并行编排）

计划执行默认以并行 wave 展开任务，每任务 4 阶段验证。执行者委托所有代码工作并独立验证一切——不信任子 Agent 的自我报告。

### Evidence-Driven Verification（证据驱动验证）

"无证据 = 未完成。"每个完成声明必须有全新的验证证据：诊断通过、构建通过、测试通过。在报告 DONE 前立即重新运行验证。

---

## 下一步

| 我想… | 看这里 |
|-------|--------|
| 查看完整 Agent 目录 | [agents.md →](agents.md) |
| 了解系统架构设计 | [architecture.md →](architecture.md) |
| 查看配置项详情 | [configuration.md →](configuration.md) |
| 深入了解知识库 | [knowledge-base.md →](knowledge-base.md) |
| 多平台技能开发 | [multi-platform.md →](multi-platform.md) |
