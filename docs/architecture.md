# 系统架构 (System Architecture)

> **需要背景？** 先看 [README.md](../README.md) 了解项目概览，[concepts.md](concepts.md) 了解设计理念，[agents.md](agents.md) 了解 Agent 目录。本文是完整的系统架构设计文档。

---

## Agent 架构 (v2, 28 skills)

```
hw-controller (增强: Intent Gate + Phase 0-3 + 委派纪律 + 知识管理 + 价值判断)
  │
  ├── [规划层 — Planning]
  │     hw-strategic-planner (NEW: 战略规划 — 访谈→计划生成)
  │       ├── hw-pre-planning-consultant (NEW: 预规划分析 — 意图分类+AI slop防护)
  │       ├── hw-plan-reviewer (NEW: 计划审查 — 阻断器发现者)
  │       ├── hw-codebase-explorer (NEW: 内部代码搜索)
  │       └── hw-external-researcher (NEW: 外部文档/OSS研究)
  │
  ├── [设计层 — Design]
  │     hw-brainstorming (NEW: 头脑风暴 — HARD-GATE: 设计批准前禁止实现)
  │     hw-feature-designer (Stage 1: 跨服务特性设计)
  │     ├── hw-service-designer × N (Stage 2: 单服务详细设计, 并行)
  │     └── hw-e2e-designer (Stage 3: E2E测试设计)
  │
  ├── [执行层 — Execution]
  │     hw-plan-executor (NEW: 多任务计划执行 — 并行fan-out + 4阶段验证)
  │       └── hw-worktree-controller × N (单任务协调)
  │             └── hw-tdd-agent (增强: 自主深度工作 + TODO执念)
  │                   ├── hw-reviewer-logic (逻辑审查)
  │                   ├── hw-reviewer-security (安全审查)
  │                   ├── hw-reviewer-performance (性能审查)
  │                   └── hw-reviewer-context (NEW: 上下文挖掘)
  │     hw-receiving-review (NEW: 审查反馈处理 — 验证后实现，禁止表演性同意)
  │
  ├── [咨询层 — Consultation, 水平调用]
  │     hw-strategic-advisor (NEW: 战略技术顾问 — 只读深度推理)
  │     hw-codebase-explorer (NEW: 内部代码搜索)
  │     hw-external-researcher (NEW: 外部研究+证据引用)
  │     hw-media-interpreter (NEW: PDF/图片/图表解读)
  │
  └── [基础设施层 — Infrastructure]
        hw-setup (模块安装配置)
        hw-knowledge-agent (知识库管理, collapsed into controller)
        hw-value-judgment (需求价值评估, collapsed into controller)
        hw-systematic-debugging (系统化调试)
        hw-verification-before-completion (完成前验证)
        hw-finishing-branch (NEW: 分支收尾 — 4-option终端状态)
        hw-document-project (NEW: 项目文档生成 — brownfield scanning + 3-level scan)
        hw-writing-skills (NEW: 元技能 — TDD应用于文档编写)
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
| **execution (执行)** | TDD cycles + parallel review | P0/P1/P2 gate |
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
│   ├── hw-controller/       # Top-level orchestrator (ENHANCED)
│   ├── hw-strategic-planner/ # Strategic planner (NEW — Prometheus)
│   ├── hw-pre-planning-consultant/ # Pre-planning analyst (NEW — Metis)
│   ├── hw-plan-reviewer/    # Plan executability reviewer (NEW — Momus)
│   ├── hw-plan-executor/    # Plan execution orchestrator (NEW — Atlas)
│   ├── hw-codebase-explorer/ # Internal code search (NEW — Explore)
│   ├── hw-external-researcher/ # External docs/OSS research (NEW — Librarian)
│   ├── hw-strategic-advisor/ # Strategic technical advisor (NEW — Oracle)
│   ├── hw-media-interpreter/ # Media file interpreter (NEW — Multimodal Looker)
│   ├── hw-feature-designer/ # Cross-service feature design
│   ├── hw-service-designer/ # Single-service detailed design
│   ├── hw-e2e-designer/     # E2E integration test design
│   ├── hw-brainstorming/    # Pre-design exploration (NEW — Superpowers)
│   ├── hw-worktree-controller/ # Single-task execution coordinator
│   ├── hw-tdd-agent/        # TDD cycle execution (ENHANCED)
│   ├── hw-reviewer-logic/   # Logic and correctness review
│   ├── hw-reviewer-security/ # Security vulnerability review
│   ├── hw-reviewer-performance/ # Performance and scalability review
│   ├── hw-reviewer-context/ # Context mining — missed requirements discovery
│   ├── hw-receiving-review/ # Review feedback processing (NEW — Superpowers)
│   ├── hw-setup/            # Module installation
│   ├── hw-knowledge-agent/  # Knowledge base management
│   ├── hw-value-judgment/   # Requirements value assessment
│   ├── hw-systematic-debugging/ # Systematic debugging
│   ├── hw-verification-before-completion/ # Pre-completion verification
│   ├── hw-finishing-branch/ # Branch completion (NEW — Superpowers)
│   ├── hw-writing-skills/   # Meta-skill (NEW — Superpowers)
│   └── using-harness/       # Bootstrap skill
├── agents/                  # Standalone agent prompt templates
├── hooks/                   # Session-start bootstrap injection
├── _bmad/                   # BMAD framework
│   ├── config.yaml          # Module configuration
│   ├── config.user.yaml     # User-specific settings
│   ├── memory/              # Agent memory (hw-shared/, hw-controller/)
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
_bmad/memory/
├── hw-shared/                    # Cross-agent shared state
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
└── hw-controller/                # Controller-private state
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
