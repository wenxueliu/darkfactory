> This file delegates to the canonical `AGENTS.md` for comprehensive project guidelines.
> @AGENTS.md

# 黑灯工厂 (HW) — Harness Engineering 落地实现

## Overview

黑灯工厂 (Black灯 Factory) 是 **Harness Engineering** 理念的落地实现 —— 构建**人机协同的软件生成系统**。通过协调多个专业化 AI Agent 组成的流水线，将人类决策与 AI 执行能力结合，实现从需求到交付的端到端自动化。

**Harness Engineering 核心思想：**
- **Human in the loop** — 人类负责价值判断、战略决策、最终审核；AI 负责执行、审查、验证
- **Agent orchestration** — 多 Agent 协同工作，每个 Agent 有明确的职责边界和通信协议
- **Gate-driven quality** — 质量门禁不可妥协，每个阶段必须通过验收标准才能推进
- **Knowledge accumulation** — 每次开发都沉淀为可复用的知识，知识库随项目持续增长

The platform follows **acceptance-driven development** with a strict TDD iron law: no production code without a failing test first.

### Multi-Language Support

本系统设计目标是**支持任意编程语言和任意自然语言**的业务场景：

- **编程语言无关 (Language-agnostic):** Agent 不绑定特定编程语言。TDD Agent 适配 pytest/Jest/JUnit/Go test/PHPUnit 等主流测试框架；Reviewer Agent 按语言加载对应的审查模式。新增语言支持只需扩展 `references/` 下的模式文件，无需修改 Agent 核心逻辑。
- **自然语言灵活切换:** Agent 通信和文档输出语言由 `_bmad/config.user.yaml` 中的 `communication_language` 控制。当前默认为 `Chinese`，切换为 `English`/`Japanese`/`Korean` 等即可适配国际化团队。所有 Agent 的 SKILL.md 均使用双语描述（中文身份 + English trigger keywords），确保跨语言环境下的技能发现。
- **业务场景快速适配:** 通过 `_bmad/config.yaml` 配置不同业务领域 —— 启用/禁用特定 Reviewer（security/logic/performance），调整质量门禁严格度，定制知识库结构。一套 Agent 定义，适配 Web 应用、API 服务、数据管道、嵌入式系统等不同业务场景。

### Rapid Business Adaptation

黑灯工厂通过**配置驱动**实现业务场景的快速灵活适配，无需修改 Agent 代码：

| 适配维度 | 机制 | 示例 |
|----------|------|------|
| 技术栈 | `references/` 按语言加载模式文件 | Python 项目加载 `references/patterns-python.md` |
| 质量策略 | `enabled_reviewers` 配置 | 金融项目启用 security+logic；内部工具仅启用 logic |
| 流程节奏 | `min_iteration_before_human` | 探索性项目设高值（减少打断）；关键项目设低值（增加审核） |
| 知识领域 | `knowledge-base/` 结构定制 | 微服务项目强化 `api-contracts/`；数据项目强化 `patterns/` |
| 交付策略 | `merge_strategy` | 持续部署用 `rebase`；保守团队用 `merge` |
| 自然语言 | `communication_language` | 中文团队 / 英文团队 / 日文团队，切换即用

## Agent Architecture

The system has 28 skills in v2:

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

### Agent Roles (v2, 28 skills)

**Core Orchestration (2 enhanced)**

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-controller` | Top-level orchestrator — full E2E with Intent Gate, Phase 0-3 system, delegation discipline, and knowledge management. Enhanced with Sisyphus DNA. | 黑灯工厂, orchestration, coordination |
| `hw-tdd-agent` | Autonomous TDD practitioner — RED→GREEN→REFACTOR with "Do NOT Ask" autonomy and TODO obsession. Enhanced with Hephaestus + Sisyphus-Junior DNA. | TDD, unit test, test-first |

**Planning Layer (4 NEW)**

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-strategic-planner` | Strategic planner — interviews, researches, generates executable work plans. Plans first, never implements. Based on Prometheus. | strategic planning, create work plan, 制定计划 |
| `hw-pre-planning-consultant` | Pre-planning analyst — classifies intent, detects ambiguities, identifies AI-slop risks. Based on Metis. | pre-planning, intent analysis, 预规划 |
| `hw-plan-reviewer` | Plan reviewer — blocker-finder, not perfectionist. Verifies plan executability. Based on Momus. | plan review, executability check, 计划审查 |
| `hw-plan-executor` | Plan execution orchestrator — delegates tasks in parallel waves with 4-phase verification. Never writes code. Based on Atlas. | plan execution, execute plan, 计划执行 |

**Design Layer (4 — 3 existing + 1 NEW)**

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-brainstorming` | Pre-design exploration — Socratic questioning, alternative proposals, design document generation. HARD-GATE: no implementation without approved design. Based on Superpowers brainstorming. (NEW) | brainstorming, 头脑风暴, 设计讨论, idea exploration |
| `hw-feature-designer` | Stage 1: Cross-service feature design | feature design, 特性设计 |
| `hw-service-designer` | Stage 2: Per-service detailed design (parallel) | service design, 服务设计 |
| `hw-e2e-designer` | Stage 3: E2E integration test design | E2E design, 端到端测试设计 |

**Execution Layer (6 — 5 existing, 1 NEW)**

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-worktree-controller` | Single-task coordinator — drives one task through TDD + review + quality gates | worktree execution, 任务开发 |
| `hw-reviewer-logic` | Logic reviewer — finds correctness bugs and edge cases | logic review, 逻辑审核 |
| `hw-reviewer-security` | Security reviewer — finds vulnerabilities and data exposure | security review, 安全审核 |
| `hw-reviewer-performance` | Performance reviewer — finds bottlenecks and scalability issues | performance review, 性能审核 |
| `hw-reviewer-context` | Context miner — searches git/GitHub/Slack/codebase for missed requirements and background knowledge (NEW). Based on review-work Context Mining Agent. | context mining, 上下文挖掘 |
| `hw-receiving-review` | Review feedback processor — technical verification before implementation, no performative agreement, pushback protocol. Based on Superpowers receiving-code-review. (NEW) | receiving review, 接收审查, review feedback, 审查反馈 |

**Consultation Layer (4 NEW)**

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-strategic-advisor` | Read-only strategic advisor — pragmatic minimalism, deep reasoning for complex decisions. Based on Oracle. | architecture advice, deep reasoning, 架构咨询 |
| `hw-codebase-explorer` | Internal codebase search specialist — intent analysis + structured results. Based on Explore. | code search, find in code, 代码搜索 |
| `hw-external-researcher` | External documentation/OSS researcher — evidence with citations. Based on Librarian. | external search, library docs, 外部搜索 |
| `hw-media-interpreter` | Media file interpreter — PDFs, images, diagrams. Based on Multimodal Looker. | PDF解读, image analysis, 图表解读 |

**Infrastructure Layer (7 — 5 existing, 2 NEW)**

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-setup` | Module installer — configures directories and memory structure | setup, 安装配置 |
| `hw-knowledge-agent` | Knowledge base management (collapsed into controller) | knowledge query, 知识库 |
| `hw-value-judgment` | Requirements value assessment (collapsed into controller) | ROI评估, 价值判断 |
| `hw-systematic-debugging` | Systematic debugging — root cause before fixes | debugging, 调试 |
| `hw-verification-before-completion` | Pre-completion verification gate | verification, 验证 |
| `hw-finishing-branch` | Branch completion — 4-option terminal state (merge/PR/keep/discard). Based on Superpowers finishing-a-development-branch. (NEW) | finish branch, 分支收尾, merge, 合并 |
| `hw-document-project` | Project documentation generator — brownfield scanning at 3 levels (quick/deep/exhaustive), generates complete AI-readable docs (index, architecture, source tree, API/data/component docs, deployment guides). Based on BMAD document-project. (NEW) | 项目文档生成, document project, brownfield documentation |
| `hw-writing-skills` | Meta-skill for skill authoring — TDD applied to process documentation. Based on Superpowers writing-skills. (NEW) | writing skills, 编写技能, create skill, skill authoring |
| `using-harness` | Bootstrap skill — injected at session start | bootstrap, 初始化 |

### E2E Phase Coverage

Each phase has structured templates and gate checks wired into hw-controller:

| Phase | Templates | Gate Check |
|-------|-----------|------------|
| **ideation (需求)** | `requirements-spec-template.md`, value assessment | `requirements-gate.md` |
| **design (设计)** | `design-doc-template.md`, `adr-template.md` | `design-gate.md` |
| **decomposition (拆分)** | `task-decomposition.md` → `tasks.yaml` | dependency check |
| **execution (执行)** | TDD cycles + parallel review | P0/P1/P2 gate |
| **merge (合并)** | `merge-management.md` | conflict-free merge |
| **test (测试)** | `integration-test-plan.md` | all IT PASS |
| **delivery (交付)** | `delivery-checklist.md`, `release-notes-template.md` | `delivery-acceptance-gate.md` |

Knowledge base is maintained throughout: ADRs in `decisions/`, patterns in `patterns/`, lessons learned in `lessons/`.

### Development Flow (Phase Transitions)

```
ideation → design → decomposition → execution → merge → test → delivery
```

Each phase transition requires explicit acceptance criteria verification. No phase advances without passing its gates. Human judgment is the ultimate backstop — escalate when iteration limits are reached; never proceed with unresolved P0/P1/P2 issues.

### Issue Severity (all reviewers)

| Level | Name | Action |
|-------|------|--------|
| P0 | Fatal | Must fix, blocks all phases |
| P1 | Severe | Must fix, blocks next phase |
| P2 | General | Must fix, blocks next phase |
| P3 | Suggestion | Document only |

## Key Design Patterns (from oh-my-openagent integration)

### Intent Gate (Sisyphus → hw-controller)
Every activation begins with intent verification: classify the request type, check for ambiguity, and route to the appropriate agent layer. Implementation only proceeds when an explicit implementation verb is present, scope is concrete, and no specialist result is pending.

### Autonomous Execution (Hephaestus → hw-tdd-agent)
"Do NOT Ask — Just Do." The TDD agent exhausts the exploration hierarchy (direct tools → codebase search → external research → context inference) before asking any question. When blocked, it tries different approaches rather than stopping.

### Structured Planning (Prometheus → hw-strategic-planner)
Planning follows interview → research → plan generation → review. Drafts serve as working memory between turns. Plans include explicit QA scenarios that are agent-executable (no "user manually tests" criteria).

### Parallel Orchestration (Atlas → hw-plan-executor)
Plan execution fans out tasks in parallel waves by default, with 4-phase verification per task. The executor delegates all code work and verifies everything independently — never trusting subagent self-reports.

### Evidence-Driven Verification (Sisyphus → all agents)
"NO EVIDENCE = NOT COMPLETE." Every completion claim must be backed by fresh verification evidence: diagnostics clean, build passing, tests passing. Re-run verification immediately before reporting DONE.

## Agent Behavior Rules (Hook Equivalents)

These rules are enforced by Claude Code hooks (`hooks/hooks.json` → PreToolUse + PostToolUse events) and documented here as binding instructions for all platforms including Codex.

### Write Safety Rule (`write-safety-guard` hook)

**Before using Write or Edit on an existing file, you MUST have read that file first in the current conversation.** This ensures you understand current content before modifying it.

- **New files:** Can create without reading (file does not exist yet).
- **Existing files:** MUST read first using the Read tool. The Claude Code hook actively blocks unread writes.
- **Infrastructure paths:** `.sisyphus/` and workspace-external paths are exempt.
- If blocked: read the file, then write.

### Delegation Discipline (`delegation-reminder` hook)

**The hw-controller and hw-plan-executor MUST delegate non-trivial work to specialized subagents.** Direct tool calls are for trivial tasks only. After 3+ direct tool calls without using the Agent tool, the hook injects a reminder.

When to delegate (MUST):
- Complex, multi-step operations → `hw-tdd-agent` (via `hw-worktree-controller`)
- Code reviews → `hw-reviewer-logic`, `hw-reviewer-security`, `hw-reviewer-performance`, `hw-reviewer-context`
- Codebase exploration → `hw-codebase-explorer` (parallel with `hw-external-researcher`)
- External research → `hw-external-researcher`
- Strategic planning → `hw-strategic-planner`
- Plan execution → `hw-plan-executor`
- Deep technical consultation → `hw-strategic-advisor`
- Media file analysis → `hw-media-interpreter`

When direct work is OK:
- Single file, known location, trivial change (<10 lines)
- Reading a specific known file path
- Simple configuration validation

If you find yourself making 3+ direct tool calls without delegation: STOP. Ask yourself — am I doing work that a specialized subagent should handle?

### Rules Awareness (`rules-injector` hook)

**After reading or modifying a file, you SHOULD check for nearby instruction files** that may apply to that file's directory tree:
- `AGENTS.md` or `CLAUDE.md` in the file's directory or parent directories
- `.claude/rules/*.md` for Claude Code file-type rules
- `.cursor/rules/*.md` for Cursor editor rules
- `.github/instructions/*.md` for repository workflow instructions

The Claude Code hook automatically scans and injects matching rules (filtered by `globs` / `alwaysApply` frontmatter). On Codex, proactively check for `AGENTS.md` in the file's directory tree.

### State Cleanup (`hook-cleanup` hook)

Hook state files in `hooks/hook-state/*.json` are automatically cleaned on `PreCompact` (before context compaction) and on `SessionStart` (`startup|clear|compact` matchers). Files older than 7 days are auto-pruned.

---

## Multi-Platform Target

This project's skills MUST run identically on three agent platforms:

| Platform | Skill location | Config | Instruction file | Invocation |
|----------|---------------|--------|------------------|------------|
| **Claude Code** | `skills/<name>/SKILL.md` | `.claude/settings.json` | `CLAUDE.md` | `/<skill-name>` |
| **Codex (OpenAI)** | `.agents/skills/<name>/SKILL.md` | `~/.codex/config.toml` | `AGENTS.md` | `/skills` or `$skill-name` |
| **OpenCode** | `.opencode/skills/<name>/SKILL.md` | `opencode.json` | `opencode.json` instructions | via plugin agent |

### Platform Skill Discovery

- **Claude Code:** Auto-discovers skills under `skills/` at project root or `.claude/skills/`. Skills are directories containing `SKILL.md` + optional `references/`, `scripts/`, `assets/`.
- **Codex:** Auto-discovers skills under `.agents/skills/` (repo-scoped) or `~/.agents/skills/` (user-scoped). Loads only name/description at startup; full content injected on invocation.
- **OpenCode:** Loads skills from `.opencode/skills/` (project) or `~/.config/opencode/skills/` (global). Plugins list npm packages in `opencode.json`.

## Working Agreement

- **Harness Engineering first:** This is a human-AI collaborative system. Human judgment is the ultimate backstop on strategic decisions, value trade-offs, and final approval. AI agents handle execution, review, and verification. Never remove the human from critical-path decisions.
- **Language-agnostic design:** Agent core logic MUST not assume a specific programming language. Language-specific patterns live in `references/` and are loaded on activation. When adding a new language, add pattern files — do not modify agent SKILL.md.
- **Business scenario flexibility:** Agents are configured, not rewritten, for different business domains. Every behavioral difference between scenarios should be expressed as a config value, not a code branch.
- **Skill isolation:** Each skill directory (`skills/hw-*/`) is self-contained. Skills reference only files within their own directory tree. If two skills need the same supporting file, duplicate it into each skill's directory.
- **No cross-skill references:** NEVER use `../other-skill/references/`, absolute paths, or platform-cache paths to reference sibling skill files. Skill directories are the unit of portability — when converted/copied to another platform, sibling directories may not exist.
- **Branching:** Create a feature branch for non-trivial changes. If already on the correct branch, keep using it — do not create additional branches or worktrees unless requested.
- **Safety:** Do not delete or overwrite user data. Avoid destructive commands.
- **Configuration:** Project config lives in `_bmad/config.yaml` and `_bmad/config.user.yaml`. Read config before assuming defaults.
- **Shared state:** All cross-agent state lives in `_bmad/memory/hw-shared/`. Agent-private state lives in `_bmad/memory/hw-{agent}/`.
- **Worktrees:** Isolated task execution happens in `{worktree_base}` (default: `.worktree/` at project root). This directory must be gitignored.
- **Language:** This project uses Chinese for agent communication and documentation. Config defaults to `document_output_language: Chinese`.
- **Use subagents:** Prefer delegating complex, multi-step, or cross-file search/analysis tasks to subagents via the Agent tool. Run independent subagents in parallel to reduce main context window consumption. 尽量使用 subagent 执行复杂任务。
- **KB health check:** Run `python scripts/kb-health.py` periodically to monitor KB growth, staleness, and gaps. Run `python scripts/kb-index.py --check-staleness` to detect decayed entries. Use `python scripts/kb-distill.py batch` to compress KB entries for reduced token consumption. Use `python scripts/kb-freshness.py` to compute confidence decay.
- **KB lifecycle:** Entries have status (`active`/`deprecated`/`superseded`/`expired`), support `supersedes`/`expires` fields, and confidence auto-decays by source type (observed: -1/60d, inferred: -1/30d, cross-model: -1/30d, user-stated: no decay). Configured via `_bmad/config.yaml` → `hw.kb.freshness`.
- **Dual instruction files:** This repo maintains both `CLAUDE.md` (Claude Code) and `AGENTS.md` (Codex). `AGENTS.md` is the canonical instruction file — `CLAUDE.md` points to it via `@AGENTS.md`. Keep them in sync; when in doubt, `AGENTS.md` is the source of truth.
- **No platform-specific variables:** NEVER use `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_SKILL_DIR}`, `${CLAUDE_SESSION_ID}`, `${CODEX_SANDBOX}`, `${CODEX_SESSION_ID}`, or any other platform-only environment variable in skill content. See Platform-Agnostic Skill Design below.
- **Cross-OS compatibility:** All skills, scripts, and tooling MUST run on **Windows**, **Linux**, and **macOS**. Use forward-slash (`/`) path separators (works on all three OSes with modern tooling). Avoid shell-specific syntax (bashisms, PowerShell-only constructs) in skill scripts — prefer POSIX-compatible commands. When OS-specific behavior is unavoidable, use `references/` pattern files per OS (e.g., `references/setup-windows.md`, `references/setup-linux.md`, `references/setup-macos.md`), not code branches in agent core logic. Never assume a case-sensitive filesystem — verify file existence rather than relying on case distinctions.

## Directory Layout

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
│   ├── using-harness/       # Bootstrap skill
│   └── reports/             # Generated reports
├── _bmad/                   # BMAD framework
│   ├── config.yaml          # Module configuration
│   ├── config.user.yaml     # User-specific settings
│   ├── memory/              # Agent memory (hw-shared/, hw-controller/)
│   ├── bmm/                 # BMAD module manager
│   └── tea/                 # Test architecture
├── _bmad-output/            # BMAD output directory
├── docs/                    # Project documentation
├── .claude/                 # Claude Code settings
│   └── settings.local.json  # Local permissions
├── .remember/               # Session memory and logs
└── .omc/                    # OMC configuration
```

## Skill Design Patterns

Each skill (`skills/hw-*/SKILL.md`) follows a consistent template:

1. **YAML frontmatter** — name, description with trigger keywords
2. **Overview** — agent purpose and mission statement
3. **Identity** — agent persona and mindset
4. **Communication Style** — how the agent communicates
5. **Principles** — non-negotiable behavioral rules
6. **On Activation** — initialization steps when the skill is invoked
7. **Capabilities table** — routes to reference files for detailed instructions
8. **Memory/State files** — which shared files the agent reads/writes
9. **Output** — where results are written

When creating or modifying a skill:
- `references/` directory contains the detailed capability instructions loaded at runtime
- Keep SKILL.md as the high-level agent definition; put procedural details in `references/`
- Trigger keywords in the description enable automatic skill discovery
- **Language patterns go in `references/`** — e.g., `references/patterns-python.md`, `references/patterns-go.md`. The SKILL.md routes to the correct pattern based on detected project language.
- **Business domain config goes in `_bmad/config.yaml`** — reviewer selection, gate strictness, knowledge structure. Agent behavior adapts to config, not hardcoded branches.

## Platform-Agnostic Skill Design

Skills are authored once and run on Claude Code, Codex, and OpenCode. Every design decision must work across all three.

### Frontmatter Constraints

YAML frontmatter is the universal metadata format across all three platforms. Constraints:

- **`name`** (required): ≤ 100 characters (Codex limit). kebab-case, ASCII only. Must match the skill directory name.
- **`description`** (required): ≤ 500 characters (Codex limit). Include trigger keywords in both Chinese and English for cross-platform discovery. This is the ONLY content loaded at startup by Codex — make it count.
- **No platform-only frontmatter fields.** `allowed-tools` (Claude Code), `disable-model-invocation` (Claude Code), `argument-hint` (Codex) — these break on other platforms. If a field is unavoidable, document the fallback behavior.

```yaml
---
name: hw-tdd-agent
description: TDD执行Agent. Use when executing TDD cycles, writing unit tests. [trigger: TDD, 单元测试, 测试先行, RED-GREEN-REFACTOR]
---
```

### File References: Relative Paths Only

All file references in SKILL.md MUST use relative paths from the skill directory. This is the only pattern that works on all three platforms:

```
# CORRECT — relative to skill directory
bash scripts/run-tests.sh
Load references/tdd-ut-cycle.md

# BROKEN — platform-specific variables
${CLAUDE_PLUGIN_ROOT}/skills/hw-tdd-agent/references/tdd-ut-cycle.md
${CODEX_SANDBOX}/.agents/skills/hw-tdd-agent/references/tdd-ut-cycle.md

# BROKEN — absolute paths (differ per platform install location)
/home/user/.claude/skills/hw-tdd-agent/references/tdd-ut-cycle.md

# BROKEN — cross-skill traversal (sibling may not exist on target platform)
../hw-controller/references/global-state.md
```

Rationale:
- Claude Code caches plugins at versioned paths; `CLAUDE_PLUGIN_ROOT` resolves unpredictably.
- Codex sandboxes skills; absolute paths point nowhere.
- OpenCode merges configs from multiple sources; hardcoded paths break.
- Each platform resolves `scripts/foo.sh` relative to the SKILL.md location — this is the only portable pattern.

### State References: Token-Based, Not Path-Based

Skills reference shared state (tasks, memory, reviews) via logical tokens, not filesystem paths:

```
# CORRECT — token that each platform resolves to its own memory root
Load task from {project-root}/_bmad/memory/hw-shared/tasks.yaml

# BROKEN — assumes a specific working directory
Load task from /home/user/project/_bmad/memory/hw-shared/tasks.yaml
```

The `{project-root}` token is resolved by each skill's "On Activation" step by reading the platform's project root concept (Claude Code: working directory; Codex: repo root; OpenCode: project config path).

### Tool Calls: Platform-Neutral Patterns

Different platforms have different tool names. Skills MUST describe intent, not tool names:

```
# CORRECT — describes what to do, platform resolves to its native tool
Delegate the review to the security reviewer agent

# BROKEN — Claude Code-specific tool name
Use the Agent tool with subagent_type=hw-reviewer-security

# BROKEN — Codex-specific invocation
Run /skills:hw-reviewer-security
```

When agent-to-agent delegation is needed, describe the target agent by its **logical name** (`hw-reviewer-security`). Each platform's runtime resolves this to its native delegation mechanism (Claude Code: `Agent` tool; Codex: `$skill-name`; OpenCode: agent config).

### Bash Blocks: Self-Contained, No Platform State

Each bash code block runs in a separate shell. Variables do not persist between blocks. Rules:

- **Use natural language for logic and state**, not shell variables.
- **Keep bash blocks self-contained.** If a block needs context from a previous step, restate it in prose.
- **Express conditionals as English**, not nested `if/elif/else`.
- **No platform-specific CLI flags.** `claude -p`, `codex exec`, `opencode run` — these don't exist on other platforms.

### Character Encoding

- **Identifiers** (file names, agent names, command names): ASCII only. Converters and regex patterns depend on this.
- **Markdown tables:** Pipe-delimited (`| col | col |`), never box-drawing characters.
- **Prose and skill content:** Unicode is fine. Prefer ASCII arrows (`->`, `<-`) over Unicode arrows in code blocks and terminal examples.

### Parallel Execution: Describe Intent, Not Mechanism

```markdown
# CORRECT
Run the three code reviews in parallel:
- Security review
- Logic review
- Performance review

# BROKEN — platform-specific
Use Task tool with run_in_background for each review
```

### Platform Feature Matrix

| Feature | Claude Code | Codex | OpenCode | Portable approach |
|---------|-------------|-------|----------|-------------------|
| Skill dir | `skills/<name>/` | `.agents/skills/<name>/` | `.opencode/skills/<name>/` | Use relative paths from SKILL.md |
| Agent delegation | `Agent` tool | `$skill-name` | agent config | Describe intent, not tool name |
| Background tasks | `run_in_background` | N/A | N/A | Describe parallelism, not mechanism |
| Permissions | `.claude/settings.json` | `config.toml` | `opencode.json` | Document needed perms; each platform configures separately |
| Hooks | `hooks/hooks.json` | N/A | plugin events | Avoid hook-dependent logic in skills |
| MCP servers | `.mcp.json` | `[mcp_servers]` in TOML | `mcp` in JSON | Define MCP config per platform; skills reference MCP tools by name only |
| Instruction file | `CLAUDE.md` | `AGENTS.md` | instructions in JSON | Maintain `AGENTS.md` as canonical; `CLAUDE.md` delegates to it |
| Frontmatter extras | `allowed-tools` | `argument-hint` | N/A | Keep frontmatter to `name` + `description` only |

## Memory Architecture

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

## Template Customization (业务模板定制)

不同业务领域使用不同的需求模板。通过 `business_domain` 配置自动切换，无需修改 Agent 代码：

| business_domain | 需求模板 | 特点 |
|-----------------|---------|------|
| `general` | `requirements-spec-template.md` | 通用 10 章节，适用大多数场景 |
| `fintech` | `requirements-spec-template-fintech.md` | 增加合规/监管/审计追踪/交易一致性/SLA 章节 |
| `ecommerce` | `requirements-spec-template-ecommerce.md` | 增加用户旅程/转化指标/支付结算/A/B 测试/库存状态机 |
| `internal-tools` | `requirements-spec-template-internal-tools.md` | 简化版，减少 ceremony，专注集成点和运维手册 |

**新增业务领域:** 创建 `requirements-spec-template-{domain}.md` → 在 `template-router.md` 添加一行映射 → 提交 PR。Agent 核心逻辑零改动。

**完全自定义模板:** 在 `_bmad/config.yaml` 中指定 `custom_templates.requirements` 路径，覆盖内置模板。

## Configuration

黑灯工厂通过配置驱动行为适配，实现一套 Agent 定义支撑多种语言、多种业务场景：

Default config (overridable in `_bmad/config.yaml` and `_bmad/config.user.yaml`):

| Key | Default | Description |
|-----|---------|-------------|
| `worktree_base` | `{project-root}/.worktree` | Worktree directory location |
| `min_iteration_before_human` | 3 | Iterations before escalating to human |
| `enabled_reviewers` | `security,logic,performance` | Active review types |
| `knowledge_base_auto_update` | `true` | Auto-update KB after development |
| `merge_strategy` | `merge` | Worktree merge strategy |
| `document_output_language` | `Chinese` | Agent 通信和文档输出语言 |
| `communication_language` | `Chinese` | Human-Agent 交互语言 |
| `supported_languages` | `*` (auto-detect) | 目标编程语言列表，`*` 表示自动检测 |
| `business_domain` | `general` | 业务领域标记，驱动模板选择 + Reviewer 策略 + 门禁严格度。支持: `general`, `fintech`, `ecommerce`, `internal-tools`, `java-springboot-enterprise` |
| `kb.freshness.confidence_decay.observed` | 60 | observed 来源衰减：每 N 天 -1 confidence |
| `kb.freshness.confidence_decay.inferred` | 30 | inferred 来源衰减：每 N 天 -1 confidence |
| `kb.freshness.confidence_decay.cross-model` | 30 | cross-model 来源衰减：每 N 天 -1 confidence |
| `kb.freshness.confidence_decay.user-stated` | 0 | user-stated 不衰减（人类知识稳定） |
| `kb.freshness.stale_threshold_days` | 90 | 超过此天数 + effective confidence ≤5 即标记 stale |
| `kb.freshness.auto_expire_days` | 365 | 超过此天数标记为 expired，触发审查 |
| `custom_templates` | (空) | 可选。覆盖内置模板的自定义路径，如 `custom_templates.requirements: "./templates/our-spec.md"`。优先级高于 business_domain |

### 业务场景适配示例

```yaml
# _bmad/config.yaml — 金融 API 服务场景
hw:
  enabled_reviewers: "security,logic,performance"  # 金融项目全开
  business_domain: "fintech"
  knowledge_base_auto_update: true
  min_iteration_before_human: 2  # 关键项目加强人工介入

# _bmad/config.user.yaml — 日文团队
communication_language: Japanese
user_name: Tanaka
```

```yaml
# _bmad/config.yaml — 内部工具脚本场景
hw:
  enabled_reviewers: "logic"  # 仅逻辑审查
  business_domain: "internal-tools"
  knowledge_base_auto_update: false
  min_iteration_before_human: 5  # 减少打断
```

## Worktree Status Contract

Worktree controllers report to the top controller using these states:

| Status | Meaning | Controller Action |
|--------|---------|-------------------|
| `DONE` | Task complete, all gates passed | Mark complete, check merge readiness |
| `DONE_WITH_CONCERNS` | Complete but has reservations | Log concerns, evaluate human review |
| `NEEDS_CONTEXT` | Blocked on missing information | Provide context or escalate |
| `BLOCKED` | Stuck on dependency or issue | Analyze cause, resolve or escalate |

## Commit Conventions

- Prefix based on intent: `feat:`, `fix:`, `docs:`, `refactor:`, etc.
- Include agent scope: `feat(hw-controller):`, `fix(hw-reviewer-security):`, etc.
- Keep commits bisectable — one logical change per commit
- Skills are product code even though they are Markdown — use `feat:`/`fix:`, not `docs:`

