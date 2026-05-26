# 系统架构 (System Architecture)

> **需要背景？** 先看 [README.md](../README.md) 了解项目概览，[concepts.md](concepts.md) 了解设计理念，[agents.md](agents.md) 了解 Agent 目录。本文是完整的系统架构设计文档。

---

## Agent 架构 (v2, 33 skills)

```
sw-controller (Intent Gate + Phase Transition + 委派纪律 — 只协调，不执行)
  │
  ├── [需求层 — Ideation]
  │     sw-requirements-clarifier (NEW: 需求澄清 — 4轮渐进对话→规格文档)
  │     sw-value-judgment (REVIVED: 需求价值评估)
  │
  ├── [规划层 — Planning]
  │     sw-strategic-planner (NEW: 战略规划 — 访谈→计划生成)
  │       ├── sw-pre-planning-consultant (NEW: 预规划分析 — 意图分类+AI slop防护)
  │       ├── sw-plan-reviewer (NEW: 计划审查 — 阻断器发现者)
  │       ├── sw-codebase-explorer (NEW: 内部代码搜索)
  │       └── sw-external-researcher (NEW: 外部文档/OSS研究)
  │
  ├── [设计层 — Design]
  │     sw-brainstorming (NEW: 头脑风暴 — HARD-GATE: 设计批准前禁止实现)
  │     sw-feature-designer (Stage 1: 跨服务特性设计)
  │     ├── sw-service-designer × N (Stage 2: 单服务详细设计, 并行)
  │     └── sw-e2e-designer (Stage 3: E2E测试设计)
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
  │                   └── sw-reviewer-context (NEW: 上下文挖掘)
  │     sw-receiving-review (NEW: 审查反馈处理 — 验证后实现，禁止表演性同意)
  │     sw-lint-checker (NEW: 跨语言规范检查 — 自动检测→运行工具→修复→复查)
  │
  ├── [测试层 — Test]
  │     sw-integration-tester (NEW: 集成测试 — 环境检查→执行→结果分析)
  │
  ├── [交付层 — Delivery]
  │     sw-delivery-manager (NEW: 交付管理 — 检查清单+Release Notes)
  │
  ├── [咨询层 — Consultation, 水平调用]
  │     sw-strategic-advisor (NEW: 战略技术顾问 — 只读深度推理)
  │     sw-codebase-explorer (NEW: 内部代码搜索)
  │     sw-external-researcher (NEW: 外部研究+证据引用)
  │     sw-media-interpreter (NEW: PDF/图片/图表解读)
  │
  └── [基础设施层 — Infrastructure]
        sw-setup (模块安装配置)
        sw-knowledge-agent (REVIVED: 知识库管理)
        sw-systematic-debugging (系统化调试)
        sw-verification-before-completion (完成前验证)
        sw-finishing-branch (NEW: 分支收尾 — 4-option终端状态)
        sw-document-project (NEW: 项目文档生成 — brownfield scanning + 3-level scan)
        sw-writing-skills (NEW: 元技能 — TDD应用于文档编写)
        using-harness (bootstrap技能)
```

---

## E2E 阶段覆盖

每个阶段有结构化模板和质量门禁：

| Phase | Templates | Gate Check |
|-------|-----------|------------|
| **ideation (需求)** | `requirements-spec-template.md`, value assessment | `requirements-gate.md` |
| **design (设计)** | `design-doc-template.md`, `adr-template.md` | `design-gate.md` |
| **decomposition (拆分)** | `task-decomposition.md` → `tasks.yaml` | dependency check |
| **execution (执行)** | TDD cycles + lint check + parallel review | P0/P1/P2 gate |
| **merge (合并)** | `merge-management.md` | conflict-free merge |
| **test (测试)** | `integration-test-plan.md` | all IT PASS |
| **delivery (交付)** | `delivery-checklist.md`, `release-notes-template.md` | `delivery-acceptance-gate.md` |

知识库在所有阶段持续维护：ADR 在 `decisions/`、模式在 `patterns/`、经验教训在 `lessons/`。

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
│   ├── sw-strategic-planner/ # Strategic planner (NEW — Prometheus)
│   ├── sw-pre-planning-consultant/ # Pre-planning analyst (NEW — Metis)
│   ├── sw-plan-reviewer/    # Plan executability reviewer (NEW — Momus)
│   ├── sw-plan-executor/    # Plan execution orchestrator (NEW — Atlas)
│   ├── sw-codebase-explorer/ # Internal code search (NEW — Explore)
│   ├── sw-external-researcher/ # External docs/OSS research (NEW — Librarian)
│   ├── sw-strategic-advisor/ # Strategic technical advisor (NEW — Oracle)
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
│   ├── sw-setup/            # Module installation
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
├── _context/                   # BMAD framework
│   ├── config.yaml          # Module configuration
│   ├── config.user.yaml     # User-specific settings
│   ├── memory/              # Agent memory (sw-shared/, sw-controller/)
│   └── bmm/                 # BMAD module manager
├── docs/                    # Project documentation
├── .claude-plugin/          # Claude Code plugin manifest
├── .codex-plugin/           # Codex plugin manifest
├── .opencode/               # OpenCode plugin + config
├── .claude/                 # Claude Code settings
└── .remember/               # Session memory and logs
```

---

## 记忆架构 (Memory Architecture)

```
_context/memory/
├── sw-shared/                    # Cross-agent shared state
│   ├── tasks.yaml                # Task definitions and status
│   ├── design-decisions.md       # Architecture decision records
│   ├── human-interventions.md    # Human intervention history
│   ├── knowledge-base/           # Institutional knowledge
│   │   ├── index.md
│   │   ├── patterns/             # Reusable patterns
│   │   ├── decisions/            # Architecture decisions
│   │   ├── lessons/              # Lessons learned
│   │   └── api-contracts/        # API documentation
│   ├── reviews/                  # Code review outputs
│   └── value-assessment/         # Requirements value assessments
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
