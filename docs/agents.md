# Agent 目录 (Agent Catalog)

> **需要背景？** 先看 [concepts.md](concepts.md) 了解核心设计理念。本文列出了 v2 全部 28 个 Agent 的技能、角色和触发词。

---

## 核心编排 (Core Orchestration, 2 enhanced)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-controller` | Top-level orchestrator — full E2E with Intent Gate, Phase 0-3 system, delegation discipline, and knowledge management. Enhanced with Sisyphus DNA. | 黑灯工厂, orchestration, coordination |
| `hw-tdd-agent` | Autonomous TDD practitioner — RED→GREEN→REFACTOR with "Do NOT Ask" autonomy and TODO obsession. Enhanced with Hephaestus + Sisyphus-Junior DNA. | TDD, unit test, test-first |

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

## 执行层 (Execution Layer, 6 — 5 existing, 1 NEW)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-worktree-controller` | Single-task coordinator — drives one task through TDD + review + quality gates | worktree execution, 任务开发 |
| `hw-reviewer-logic` | Logic reviewer — finds correctness bugs and edge cases | logic review, 逻辑审核 |
| `hw-reviewer-security` | Security reviewer — finds vulnerabilities and data exposure | security review, 安全审核 |
| `hw-reviewer-performance` | Performance reviewer — finds bottlenecks and scalability issues | performance review, 性能审核 |
| `hw-reviewer-context` | Context miner — searches git/GitHub/Slack/codebase for missed requirements and background knowledge (NEW) | context mining, 上下文挖掘 |
| `hw-receiving-review` | Review feedback processor — technical verification before implementation, no performative agreement, pushback protocol. Based on Superpowers receiving-code-review. (NEW) | receiving review, 接收审查, review feedback, 审查反馈 |

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
| `hw-knowledge-agent` | Knowledge base management (collapsed into controller) | knowledge query, 知识库 |
| `hw-value-judgment` | Requirements value assessment (collapsed into controller) | ROI评估, 价值判断 |
| `hw-systematic-debugging` | Systematic debugging — root cause before fixes | debugging, 调试 |
| `hw-verification-before-completion` | Pre-completion verification gate | verification, 验证 |
| `hw-finishing-branch` | Branch completion — 4-option terminal state (merge/PR/keep/discard). Based on Superpowers finishing-a-development-branch. (NEW) | finish branch, 分支收尾, merge, 合并 |
| `hw-document-project` | Project documentation generator — brownfield scanning at 3 levels (quick/deep/exhaustive). Based on BMAD document-project. (NEW) | 项目文档生成, document project, brownfield documentation |
| `hw-writing-skills` | Meta-skill for skill authoring — TDD applied to process documentation. Based on Superpowers writing-skills. (NEW) | writing skills, 编写技能, create skill, skill authoring |
| `using-harness` | Bootstrap skill — injected at session start | bootstrap, 初始化 |

---

## 下一步

| 我想… | 看这里 |
|-------|--------|
| 了解系统架构 | [architecture.md →](architecture.md) |
| 查看配置项详情 | [configuration.md →](configuration.md) |
| 了解 Agent 编写规范 | [multi-platform.md →](multi-platform.md) |
