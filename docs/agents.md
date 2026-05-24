# Agent 目录 (Agent Catalog)

> **需要背景？** 先看 [concepts.md](concepts.md) 了解核心设计理念。本文列出了 v2 全部 32 个 Agent 的技能、角色和触发词。

---

## 核心编排 (Core Orchestration, 2 enhanced)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-controller` | Top-level orchestrator — Intent Gate + Phase Transition + delegation discipline. Routes to specialists, never executes phase work directly. Enhanced with Sisyphus DNA. | 黑灯工厂, orchestration, coordination |
| `hw-tdd-agent` | Autonomous TDD practitioner — RED→GREEN→REFACTOR with "Do NOT Ask" autonomy and TODO obsession. Enhanced with Hephaestus + Sisyphus-Junior DNA. | TDD, unit test, test-first |

## 需求层 (Ideation Layer, 1 NEW + 1 REVIVED)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-requirements-clarifier` | Requirements clarifier — 4-step progressive dialogue, ambiguity scan (10 dimensions), generates spec document. Stops when Substantiality Threshold met. (NEW) | 需求澄清, requirements clarification, clarify requirements |
| `hw-value-judgment` | Requirements value assessor — 5-dimension scoring (Impact/Effort/Risk/Dependencies/Strategic Fit), ROI evaluation, priority ranking. (REVIVED: was collapsed into controller) | 需求价值, ROI评估, 优先级判断 |

## 规划层 (Planning Layer, 4 NEW)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-strategic-planner` | Strategic planner — interviews, researches, generates executable work plans. Plans first, never implements. Based on Prometheus. | strategic planning, create work plan, 制定计划 |
| `hw-pre-planning-consultant` | Pre-planning analyst — classifies intent, detects ambiguities, identifies AI-slop risks. Based on Metis. | pre-planning, intent analysis, 预规划 |
| `hw-plan-reviewer` | Plan reviewer — blocker-finder, not perfectionist. Verifies plan executability. Based on Momus. | plan review, executability check, 计划审查 |
| `hw-plan-executor` | Plan execution orchestrator — delegates tasks in parallel waves with 4-phase verification. Never writes code. Based on Atlas. | plan execution, execute plan, 计划执行 |

## 设计层 (Design Layer, 4 — 3 existing + 1 NEW)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-brainstorming` | Pre-design exploration — Socratic questioning, alternative proposals, design document generation. HARD-GATE: no implementation without approved design. Based on Superpowers brainstorming. (NEW) | brainstorming, 头脑风暴, 设计讨论, idea exploration |
| `hw-feature-designer` | Stage 1: Cross-service feature design | feature design, 特性设计 |
| `hw-service-designer` | Stage 2: Per-service detailed design (parallel) | service design, 服务设计 |
| `hw-e2e-designer` | Stage 3: E2E integration test design | E2E design, 端到端测试设计 |

## 拆分层 (Decomposition Layer, 1 NEW)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-task-decomposer` | Task decomposer — 6-step process: service identification (4-level fallback) → DAG construction → test case assignment → wave batching → tasks.yaml → dependencies.json. No circular dependencies. Tasks 30min-3h. (NEW) | 任务拆分, task decomposition, 任务分解 |

## 执行层 (Execution Layer, 6 — 5 existing, 1 NEW)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-worktree-controller` | Single-task coordinator — drives one task through TDD + review + quality gates | worktree execution, 任务开发 |
| `hw-reviewer-logic` | Logic reviewer — finds correctness bugs and edge cases | logic review, 逻辑审核 |
| `hw-reviewer-security` | Security reviewer — finds vulnerabilities and data exposure | security review, 安全审核 |
| `hw-reviewer-performance` | Performance reviewer — finds bottlenecks and scalability issues | performance review, 性能审核 |
| `hw-reviewer-context` | Context miner — searches git/GitHub/Slack/codebase for missed requirements and background knowledge (NEW) | context mining, 上下文挖掘 |
| `hw-receiving-review` | Review feedback processor — technical verification before implementation, no performative agreement, pushback protocol. Based on Superpowers receiving-code-review. (NEW) | receiving review, 接收审查, review feedback, 审查反馈 |

## 测试层 (Test Layer, 1 NEW)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-integration-tester` | Integration tester — env health check → smoke test → integration test execution → result analysis → test-results.yaml. Connects to real backends. (NEW) | 集成测试, integration test, 测试执行 |

## 交付层 (Delivery Layer, 1 NEW)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-delivery-manager` | Delivery manager — checklist verification (delivery-checklist.md) → release notes generation (release-notes-template.md) → delivery acceptance gate. (NEW) | 交付管理, delivery, release notes, 交付检查 |

## 咨询层 (Consultation Layer, 4 NEW)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-strategic-advisor` | Read-only strategic advisor — pragmatic minimalism, deep reasoning for complex decisions. Based on Oracle. | architecture advice, deep reasoning, 架构咨询 |
| `hw-codebase-explorer` | Internal codebase search specialist — intent analysis + structured results. Based on Explore. | code search, find in code, 代码搜索 |
| `hw-external-researcher` | External documentation/OSS researcher — evidence with citations. Based on Librarian. | external search, library docs, 外部搜索 |
| `hw-media-interpreter` | Media file interpreter — PDFs, images, diagrams. Based on Multimodal Looker. | PDF解读, image analysis, 图表解读 |

## 基础设施层 (Infrastructure Layer, 8 — 5 existing, 3 NEW)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-setup` | Module installer — configures directories and memory structure | setup, 安装配置 |
| `hw-knowledge-agent` | Knowledge base manager — query (knowledge-query.md), update (knowledge-update.md), index, service discovery. KB health checks, staleness detection, freshness decay. (REVIVED: was collapsed into controller) | knowledge query, 知识库, KB管理 |
| `hw-systematic-debugging` | Systematic debugging — root cause before fixes | debugging, 调试 |
| `hw-verification-before-completion` | Pre-completion verification gate | verification, 验证 |
| `hw-finishing-branch` | Branch completion — 4-option terminal state (merge/PR/keep/discard). Based on Superpowers finishing-a-development-branch. (NEW) | finish branch, 分支收尾, merge, 合并 |
| `hw-document-project` | Project documentation generator — brownfield scanning at 3 levels (quick/deep/exhaustive). Based on BMAD document-project. (NEW) | 项目文档生成, document project, brownfield documentation |
| `hw-writing-skills` | Meta-skill for skill authoring — TDD applied to process documentation. Based on Superpowers writing-skills. (NEW) | writing skills, 编写技能, create skill, skill authoring |
| `using-harness` | Bootstrap skill — injected at session start | bootstrap, 初始化 |

---

## 需求端到端流程 (E2E Requirements Flow)

一个需求从提出到交付，经过 7 个阶段，32 个 Agent 各司其职。

> **两条路径：** 简单需求走 设计(3-stage) → 拆分 路径；复杂/多步骤需求在头脑风暴后进入 **规划层** (hw-strategic-planner)，由规划层替代设计+拆分，直接产出可执行计划。

```
用户需求
  │
  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Phase 1: ideation (需求澄清)                                          │
│                                                                      │
│   hw-controller 委托给专门 Agent:                                     │
│   ├── hw-requirements-clarifier → 4-step progressive dialogue       │
│   │     └── requirements-spec-template.md → requirements/{id}.md    │
│   ├── hw-value-judgment → value-assessment/{id}.md                  │
│   └── hw-knowledge-agent → KB pre-query (ADR/patterns/lessons)      │
│                                                                      │
│   hw-controller: 检查 requirements-gate.md (G1-G4) 结果              │
│   Output: requirements/{id}.md, value-assessment/{id}.md            │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ ✅ Requirements gate PASS
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Phase 2: design (设计)                                                │
│                                                                      │
│   Pre-design:                                                        │
│     hw-brainstorming → Socratic questioning + alternatives          │
│     hw-codebase-explorer + hw-external-researcher (并行研究)         │
│                                                                      │
│   3-Stage delegation:                                                │
│     Stage 1: hw-feature-designer → designs/{id}-design.md           │
│     Stage 2: hw-service-designer × N (并行) → per-service design    │
│     Stage 3: hw-e2e-designer → designs/{id}-e2e-design.md           │
│                                                                      │
│   Consultation: hw-strategic-advisor (只读深度推理)                  │
│                                                                      │
│   hw-controller: 检查 design-gate.md → design-validator.md 结果      │
│   Output: designs/*.md, ADR documents (adr-template.md)             │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ ✅ Design gate PASS
                   ▼
         ┌─────────────────┐
         │ 简单 or 复杂需求？ │
         └────────┬────────┘
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
┌─────────────────┐  ┌─────────────────────────────────────────────────┐
│ 简单: Phase 3    │  │ 复杂: 规划层 (Planning) → 替代设计拆分           │
│ decomposition   │  │                                                 │
│ (走任务拆分 ↓)   │  │   hw-strategic-planner (访谈 → 研究 → 生成计划)  │
│                 │  │     ├── hw-pre-planning-consultant               │
│                 │  │     │   (意图分类 + AI-slop 检测)                 │
│                 │  │     ├── hw-plan-reviewer                         │
│                 │  │     │   (可执行性审查 + 阻断器发现)               │
│                 │  │     └── hw-codebase-explorer +                   │
│                 │  │         hw-external-researcher (并行研究)         │
│                 │  │                                                 │
│                 │  │   Gate: plan review PASS                         │
│                 │  │   Output: 结构化执行计划 (含任务拆分 + 并行策略)   │
└────────┬────────┘  └──────────────────────┬──────────────────────────┘
         │                                  │
         ▼                                  │
┌──────────────────────────────────────────┼──────────────────────────────┐
│ Phase 3: decomposition (任务拆分)          │                            │
│                                          │ (来自规划层的计划已含拆分)    │
│   hw-task-decomposer:                    ▼                            │
│   ├── 6-step process: 服务识别→DAG→Wave→tasks.yaml+dependencies.json  │
│   └── 能力校验: 语言匹配+路径存在+能力覆盖                              │
│                                                                        │
│   hw-controller: 检查 dependency check (无循环依赖 + 每任务有 AC)       │
│   Output: tasks.yaml                                                   │
└──────────────────────┬─────────────────────────────────────────────────┘
                       │ ✅ Dependency check PASS (or plan review OK)
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Phase 4: execution (执行)                                             │
│                                                                      │
│   hw-plan-executor (编排层)                                          │
│     └── hw-worktree-controller × N (每任务一个 worktree，并行)       │
│           └── hw-tdd-agent (RED → GREEN → REFACTOR)                 │
│                 ├── hw-reviewer-logic (P0/P1 correctness bugs)      │
│                 ├── hw-reviewer-security (vulnerabilities)          │
│                 ├── hw-reviewer-performance (bottlenecks)           │
│                 └── hw-reviewer-context (missed requirements)       │
│                                                                      │
│   Feedback loop: hw-receiving-review → pushback protocol            │
│   Debug:   hw-systematic-debugging (根因优先于修复)                  │
│   Verify:  hw-verification-before-completion                         │
│                                                                      │
│   hw-plan-executor: 检查 P0/P1/P2 gate (0 P0, 0 P1)                 │
│   Output: 通过审查的代码变更 (各 worktree)                            │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ ✅ All worktrees DONE
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Phase 5: merge (合并)                                                 │
│                                                                      │
│   hw-finishing-branch → 4-option terminal state                     │
│     (merge / create PR / keep branch / discard)                     │
│                                                                      │
│   Gate: conflict-free merge                                          │
│   Output: 合并后的 feature 分支                                       │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ ✅ Merge complete
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Phase 6: test (测试)                                                  │
│                                                                      │
│   hw-integration-tester:                                             │
│   ├── 集成环境健康检查 (test-environment.md)                          │
│   ├── 集成测试执行 (integration-test-plan.md)                         │
│   └── API 测试 (api-test-postman-schema.md)                          │
│                                                                      │
│   Gate: all integration tests PASS                                   │
│   Output: test-results.yaml                                          │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ ✅ All IT PASS
                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Phase 7: delivery (交付)                                              │
│                                                                      │
│   hw-delivery-manager:                                               │
│   ├── 交付检查清单 (delivery-checklist.md)                            │
│   └── Release Notes (release-notes-template.md)                     │
│                                                                      │
│   hw-knowledge-agent → KB 全量更新 (knowledge-update.md)             │
│                                                                      │
│   hw-controller: 检查 delivery-acceptance-gate.md 结果                │
│   Output: 发布就绪代码 + Release Notes + 更新后的知识库              │
└──────────────────┬───────────────────────────────────────────────────┘
                   │ ✅ Delivery gate PASS
                   ▼
               🚀 交付完成
```

### 阶段-Agent 映射

| Phase | Owner | Active Agents | Key References | Gate |
|-------|-------|---------------|----------------|------|
| **ideation** | hw-requirements-clarifier | hw-value-judgment, hw-knowledge-agent | requirement-clarification.md, requirements-spec-template.md | requirements-gate.md |
| **design** | hw-feature-designer | hw-service-designer, hw-e2e-designer, hw-brainstorming, hw-strategic-advisor, hw-codebase-explorer, hw-external-researcher | design-coordination.md, adr-template.md | design-gate.md |
| **planning** (复杂需求) | hw-strategic-planner | hw-pre-planning-consultant, hw-plan-reviewer, hw-codebase-explorer, hw-external-researcher | interview→research→plan gen→review | plan review PASS |
| **decomposition** (简单需求) | hw-task-decomposer | — | task-decomposition.md, parallel-execution.md | dependency check |
| **execution** | hw-plan-executor | hw-worktree-controller, hw-tdd-agent, hw-reviewer-logic, hw-reviewer-security, hw-reviewer-performance, hw-reviewer-context, hw-receiving-review, hw-verification-before-completion, hw-systematic-debugging | worktree-management.md, quality-gates.md | P0/P1/P2 gate |
| **merge** | hw-finishing-branch | — | merge-management.md | conflict-free |
| **test** | hw-integration-tester | — | test-environment.md, integration-test-plan.md, api-test-postman-schema.md | all IT PASS |
| **delivery** | hw-delivery-manager | hw-knowledge-agent | delivery-checklist.md, release-notes-template.md | delivery-acceptance-gate.md |

> 详细阶段转换规则（含每阶段的具体检查项和失败处理）见 `skills/hw-controller/SKILL.md` → Phase Transition Rules。

### 水平支撑 (贯穿全流程)

以下 Agent 不绑定特定阶段，由 hw-controller 按需在任意阶段水平调用：

| Agent | 调用时机 |
|-------|---------|
| `hw-codebase-explorer` | 需要搜索代码库时（设计前、实现时、调试时） |
| `hw-external-researcher` | 需要查外部文档/OSS 时，与 codebase-explorer 并行 |
| `hw-strategic-advisor` | 复杂架构决策、3+ 次连续失败后的深度推理 |
| `hw-media-interpreter` | 需要解读 PDF/图片/图表时 |

---

## 下一步

| 我想… | 看这里 |
|-------|--------|
| 了解系统架构和阶段门禁 | [architecture.md →](architecture.md) |
| 查看配置项详情 | [configuration.md →](configuration.md) |
| 了解 Agent 编写规范 | [multi-platform.md →](multi-platform.md) |
