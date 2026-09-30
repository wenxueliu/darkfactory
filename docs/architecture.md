# 系统架构 (System Architecture)

> **需要背景？** 先看 [README.md](../README.md) 了解项目概览，[concepts.md](concepts.md) 了解设计理念，[agents.md](agents.md) 了解 Agent 目录。本文是完整的系统架构设计文档。

---

## Agent 架构 (v2, 44 skills)

```
sw-controller (Intent Gate + Phase Transition + 委派纪律 — 只协调，不执行)
  │
  ├── [需求层 — Ideation]
  │     sw-requirements-clarifier (NEW: 需求澄清 — 渐进澄清对话(frontier)→规格文档)
  │     sw-value-judgment (REVIVED: 需求价值评估)
  │
  ├── [规划层 — Planning]
  │     sw-strategic-planner (NEW: 执行计划 — 消费已通过设计→计划生成)
  │       ├── sw-pre-planning-consultant (NEW: 预规划分析 — 意图分类+AI slop防护)
  │       ├── sw-plan-reviewer (NEW: 计划审查 — 阻断器发现者)
  │       ├── sw-codebase-explorer (NEW: 内部代码搜索)
  │       └── sw-external-researcher (NEW: 外部文档/OSS研究)
  │
  ├── [设计层 — Design]
  │     sw-brainstorming (NEW: 头脑风暴 — HARD-GATE: 设计批准前禁止实现)
  │     sw-feature-designer (仅跨服务 Stage 1: 系统特性设计)
  │     ├── sw-service-designer (单服务直达，或跨服务 Stage 2, 并行)
  │     └── sw-e2e-designer (跨服务 Stage 3: E2E测试设计)
  │
  ├── [拆分层 — Decomposition]
  │     sw-task-decomposer (NEW: 任务拆分 — DAG+Wave+tasks.yaml+dependencies.json)
  │
  ├── [执行层 — Execution]
  │     sw-plan-executor (NEW: 多任务计划执行 — 并行fan-out + 4阶段验证)
  │       └── sw-worktree-controller × N (单任务协调)
  │             └── sw-tdd-agent (增强: 自主深度工作 + TODO执念)
  │                   ├── sw-reviewer-logic (逻辑审查)
  │                   ├── sw-reviewer-security (安全审查)
  │                   ├── sw-reviewer-performance (性能审查)
  │                   ├── sw-reviewer-context (NEW: 上下文挖掘 — 4-way fan-out 必选)
  │                   └── sw-lint-checker (NEW: 跨语言规范检查 — TDD 周期内强制)
  │     sw-receiving-review (NEW: 审查反馈处理 — 验证后实现，禁止表演性同意)
  │
  ├── [测试层 — Test]
  │     sw-integration-tester (NEW: 集成测试 — env health check + newman 硬执行)
  │     sw-browser-tester (NEW: 浏览器E2E测试 — Kimi WebBridge真实会话+视觉证据采集)
  │
  ├── [交付层 — Delivery]
  │     sw-delivery-manager (NEW: 交付管理 — 检查清单+Release Notes)
  │     sw-deployer (NEW: 部署执行 — 测试/生产环境部署 + 健康检查 + 回滚)
  │
  ├── [咨询层 — Consultation, 水平调用]
  │     sw-strategic-advisor (NEW: 战略技术顾问 — 只读深度推理)
  │     sw-codebase-explorer (NEW: 内部代码搜索)
  │     sw-external-researcher (NEW: 外部研究+证据引用)
  │     sw-multi-search (NEW: 多源搜索编排 — fan-out + 聚合 + 排序)
  │     sw-media-interpreter (NEW: PDF/图片/图表解读)
  │
  └── [基础设施层 — Infrastructure]
        sw-setup (模块安装配置)
        sw-change-propagator (需求变更传播 — revision + 下游阶段重生成)
        sw-knowledge-agent (REVIVED: 知识库管理)
        sw-systematic-debugging (系统化调试)
        sw-verification-before-completion (完成前验证)
        sw-finishing-branch (NEW: 分支收尾 — 4-option终端状态)
        sw-document-project (NEW: 项目文档生成 — brownfield scanning + 3-level scan)
        sw-writing-skills (NEW: 元技能 — TDD应用于文档编写)
        sw-grill-docs (NEW: 文档对照质询 — 设计/计划 vs knowledge/CONTEXT.md + ADRs)
        using-harness (bootstrap技能)
```

---

## E2E 阶段覆盖

每个阶段有结构化模板和质量门禁，全生命周期状态记录在 `requirements-tracker.yaml` 中：

| Phase | Templates | Gate Check | Tracker 更新者 |
|-------|-----------|------------|---------------|
| **ideation (需求)** | `requirements/{variant}` definition package, value assessment | resolved `gate.yaml` + `validator.yaml` | sw-requirements-clarifier |
| **value_assessment (价值)** | `requirements/{id}/value-assessment.md`, `requirements/{id}/roi.md` | value scoring | sw-value-judgment |
| **design (设计)** | 按服务拓扑选择 `service-design/{type}`，跨服务追加 `feature-design/default` 与 `e2e/default`，以及 ADR | applicable definition gates + validators | sw-controller topology router |
| **planning (执行计划)** | `knowledge/plans/{plan}.md` + approved design references | design gate PASS + plan gate/review | sw-strategic-planner |
| **decomposition (拆分)** | `task-decomposition.md` → minimal/existing execution plan + `tasks.yaml` | plan/task graph/dependency check | sw-task-decomposer |
| **execution (执行)** | TDD cycles + lint check + parallel review | P0/P1/P2 gate | sw-plan-executor |
| **merge (合并)** | `merge-management.md` | conflict-free merge | sw-controller |
| **test (测试)** | `requirements/{id}/integration-test-plan.md`, `requirements/{id}/test-results.yaml`, `requirements/{id}/browser-e2e-results.yaml` | all IT PASS + all browser E2E PASS | sw-controller |
| **delivery (交付)** | `delivery-checklist.md`, `release-notes-template.md` | `delivery-acceptance-gate.md` | sw-delivery-manager |

## 需求变更传播

需求变更不是普通的“继续执行”。控制器先委托
`sw-change-propagator` 判断变更规模：

```text
small   → 当前步骤直接调整
partial → 最早受影响阶段 → 后续阶段全部生成新 revision
large   → 新建需求 → ideation 重新开始
```

局部变更先写入 `knowledge/changes/{requirement_id}/{change_id}/`，其中包含
`change-propagation.yaml` 和每个受影响阶段的 `phase-deltas/*.md`。审批应用后，
tracker 为旧阶段记录 `previous_status`、`superseded_by`、`change_packet` 和目标
`revision`；控制器在目标 revision 和门禁完成前不得继续向后推进。

## 发行与安装

`package.py` 是独立的发行入口：

```text
build → publish(local/remote Git) → download → install(project/user) → init
```

包内包含清单、SHA-256 校验、skills、hooks、平台插件和 Agent 初始化入口。
详细命令见 [package-lifecycle.md](package-lifecycle.md)。

知识库在所有阶段持续维护：ADR 在 `knowledge/decisions/`、模式在 `knowledge/patterns/`、经验教训在 `knowledge/lessons/`。

## 工作区边界

黑灯工厂把源码仓库、项目知识和编排状态分开管理：

```text
{project-root}/
├── services/                         # 用户放入的一个或多个独立源码仓库
│   ├── {repository-name}/            # 每个直接子目录都是一个 Git 仓库/服务单元
│   └── ...
├── knowledge/                        # 工作区级、可读、可积累的知识与工作流状态
│   ├── decisions/                    # 企业级 ADR
│   ├── patterns/                     # 跨仓库通用模式
│   ├── lessons/                      # 企业级经验教训
│   ├── contracts/                    # 跨仓库契约
│   ├── domains/                      # 领域知识
│   ├── services/{service-id}/        # 服务发现生成的概览、API、Schema
│   ├── requirements-tracker.yaml     # 需求全生命周期状态
│   ├── tasks.yaml                    # 任务定义和状态
│   └── sw-{agent}/                   # Agent 私有状态
└── _context/                         # 配置与框架状态
```

初始化完成后，用户必须将待修改的代码仓放入 `services/{repository-name}/`。一个仓库是这个模型的自然特例，仍然执行同一套服务发现、设计、拆分和质量门禁；`services/` 为空时不得退回到工作区根目录寻找业务源码，流程必须阻塞并提示用户补充仓库。

服务注册表由 `sw-knowledge-agent` 扫描 `services/` 后生成到 `knowledge/service-registry.yaml`。注册表是运行时索引，不替代 `knowledge/` 中的人类可读知识。

### 文档契约边界

需求、特性设计、服务设计、E2E 设计、计划和项目文档属于正式文档产物，由各自产出 Skill 的定义包维护模板、门禁和验证器。组合运行时只传递 `document_type`、`contract`、`contract_version` 和稳定 `section-id`，不依赖标题或章节编号。

```text
项目 knowledge/templates/
        ↓ 覆盖
用户共享 templates/
        ↓ 覆盖
Skill 内置 document-definitions/
        ↓
统一解析 + 验证 → 文档产物
```

`sw-controller` 负责选择文档类型、编排 Skill 和汇总门禁，不直接读取其他 Skill 的模板文件。完整协议见 [document-contracts.md](document-contracts.md)。

---

## Worktree 状态合约

Worktree controller 向总控报告以下状态：

| Status | Meaning | Controller Action |
|--------|---------|-------------------|
| `DONE` | Task complete, all gates passed | Mark complete, check merge readiness |
| `DONE_WITH_CONCERNS` | Complete but has reservations | Log concerns, evaluate human review |
| `NEEDS_CONTEXT` | Blocked on missing information | Provide context or escalate |
| `BLOCKED` | Stuck on dependency or issue | Analyze cause, resolve or escalate |

---

## 目录结构

```
multiagents/
├── skills/                  # Agent skill definitions (BMAD module output)
│   ├── sw-controller/       # Top-level orchestrator (ENHANCED)
│   ├── sw-strategic-planner/ # Execution planner after design gates (NEW — Prometheus)
│   ├── sw-pre-planning-consultant/ # Pre-planning analyst (NEW — Metis)
│   ├── sw-plan-reviewer/    # Plan executability reviewer (NEW — Momus)
│   ├── sw-plan-executor/    # Plan execution orchestrator (NEW — Atlas)
│   ├── sw-codebase-explorer/ # Internal code search (NEW — Explore)
│   ├── sw-external-researcher/ # External docs/OSS research (NEW — Librarian)
│   ├── sw-strategic-advisor/ # Strategic technical advisor (NEW — Oracle)
│   ├── sw-multi-search/     # Multi-source search orchestrator (NEW)
│   ├── sw-media-interpreter/ # Media file interpreter (NEW — Multimodal Looker)
│   ├── sw-feature-designer/ # Cross-service feature design
│   ├── sw-service-designer/ # Single-service detailed design
│   ├── sw-e2e-designer/     # E2E integration test design
│   ├── sw-brainstorming/    # Pre-design exploration (NEW — Superpowers)
│   ├── sw-worktree-controller/ # Single-task execution coordinator
│   ├── sw-tdd-agent/        # TDD cycle execution (ENHANCED)
│   ├── sw-reviewer-logic/   # Logic and correctness review
│   ├── sw-reviewer-security/ # Security vulnerability review
│   ├── sw-reviewer-performance/ # Performance and scalability review
│   ├── sw-reviewer-context/ # Context mining — missed requirements discovery
│   ├── sw-receiving-review/ # Review feedback processing (NEW — Superpowers)
│   ├── sw-deployer/         # Deployment execution (NEW)
│   ├── sw-grill-docs/       # Documentation consistency griller (NEW)
│   ├── sw-setup/            # Module installation + package lifecycle
│   ├── sw-change-propagator/ # Requirement change propagation
│   ├── sw-knowledge-agent/  # Knowledge base management
│   ├── sw-value-judgment/   # Requirements value assessment
│   ├── sw-systematic-debugging/ # Systematic debugging
│   ├── sw-verification-before-completion/ # Pre-completion verification
│   ├── sw-finishing-branch/ # Branch completion (NEW — Superpowers)
│   ├── sw-writing-skills/   # Meta-skill (NEW — Superpowers)
│   ├── sw-lint-checker/     # Cross-language standards checker (NEW)
│   └── using-harness/       # Bootstrap skill
├── agents/                  # Standalone agent prompt templates
├── hooks/                   # Session-start bootstrap injection
├── knowledge/               # Project knowledge + workflow state (shared + sw-{agent}/)
├── _context/                # BMAD framework
│   ├── config.yaml          # Module configuration
│   ├── config.user.yaml     # User-specific settings
│   └── bmm/                 # BMAD module manager
├── docs/                    # Project documentation
├── .claude-plugin/          # Claude Code plugin manifest
├── .codex-plugin/           # Codex plugin manifest
├── .opencode/               # OpenCode plugin + config
├── .claude/                 # Claude Code settings
└── .remember/               # Session memory and logs
```

上面的 `multiagents/` 是框架源码仓库本身；使用框架的业务项目还必须遵循上一节的 `services/`、`knowledge/`、`_context/` 工作区边界。

---

## 记忆架构 (Memory Architecture)

```
services/                         # User-provided source repositories
knowledge/                        # Project knowledge + cross-agent workflow state
├── decisions/                    # Enterprise ADRs
├── patterns/                     # Cross-repository patterns
├── lessons/                      # Enterprise lessons
├── contracts/                    # Cross-repository contracts
├── domains/                      # Domain-scoped knowledge
├── services/{service-id}/        # Repository-scoped generated knowledge
├── requirements/{requirement-id}/ # Requirement bundle: spec, value, ROI, gate
├── requirements-tracker.yaml     # Requirement lifecycle tracking (phase status, progress, artifacts)
├── tasks.yaml                    # Task definitions and status
├── service-registry.yaml         # Generated index of services/
├── human-interventions.md        # Human intervention history
├── reviews/                      # Code review outputs
├── value-assessment/             # Cross-requirement value summaries (for example priority rankings)
└── sw-controller/                # Controller-private state
    ├── global-state.yaml         # Current phase, progress, blockers
    └── worktree-registry.yaml    # Worktree status and task assignments
```

---

## 下一步

| 我想… | 看这里 |
|-------|--------|
| 查看配置项详情 | [configuration.md →](configuration.md) |
| 深入了解知识库 | [knowledge-base.md →](knowledge-base.md) |
| 多平台技能开发 | [multi-platform.md →](multi-platform.md) |
| Works 动态路由目标架构 | [works-routing-target-architecture.md →](works-routing-target-architecture.md) |
