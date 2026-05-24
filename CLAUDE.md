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

> 配置驱动的业务适配机制详见 [docs/configuration.md](docs/configuration.md)。

## Agent Architecture

The system has 32 skills in v2:

```
hw-controller (增强: Intent Gate + Phase Transition + 委派纪律 — 只协调，不执行)
  │
  ├── [需求层 — Ideation]
  │     hw-requirements-clarifier (NEW: 需求澄清 — 4轮渐进对话→规格文档)
  │     hw-value-judgment (REVIVED: 需求价值评估)
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
  ├── [拆分层 — Decomposition]
  │     hw-task-decomposer (NEW: 任务拆分 — DAG+Wave+tasks.yaml+dependencies.json)
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
  ├── [测试层 — Test]
  │     hw-integration-tester (NEW: 集成测试 — 环境健康检查+执行+结果分析)
  │
  ├── [交付层 — Delivery]
  │     hw-delivery-manager (NEW: 交付管理 — 检查清单+Release Notes)
  │
  ├── [咨询层 — Consultation, 水平调用]
  │     hw-strategic-advisor (NEW: 战略技术顾问 — 只读深度推理)
  │     hw-codebase-explorer (NEW: 内部代码搜索)
  │     hw-external-researcher (NEW: 外部研究+证据引用)
  │     hw-media-interpreter (NEW: PDF/图片/图表解读)
  │
  └── [基础设施层 — Infrastructure]
        hw-setup (模块安装配置)
        hw-knowledge-agent (REVIVED: 知识库管理 — 查询+更新+索引)
        hw-systematic-debugging (系统化调试)
        hw-verification-before-completion (完成前验证)
        hw-finishing-branch (NEW: 分支收尾 — 4-option终端状态)
        hw-document-project (NEW: 项目文档生成 — brownfield scanning + 3-level scan)
        hw-writing-skills (NEW: 元技能 — TDD应用于文档编写)
        using-harness (bootstrap技能)
```

<!-- Agent Roles and E2E Phase Coverage extracted to standalone docs -->
> 全部 32 个 Agent 的角色、触发词和能力详见 [docs/agents.md](docs/agents.md)。
> E2E 阶段覆盖和门禁检查详见 [docs/architecture.md](docs/architecture.md)。

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
- Requirements clarification → `hw-requirements-clarifier` (4-step progressive dialogue → spec document)
- Value assessment → `hw-value-judgment` (ROI + strategic alignment + 5-dimension scoring)
- Knowledge base query/update → `hw-knowledge-agent` (ADR, patterns, lessons, service discovery)
- Task decomposition → `hw-task-decomposer` (service identification → DAG → Wave → tasks.yaml)
- Complex, multi-step code operations → `hw-tdd-agent` (via `hw-worktree-controller`)
- Code reviews → `hw-reviewer-logic`, `hw-reviewer-security`, `hw-reviewer-performance`, `hw-reviewer-context`
- Codebase exploration → `hw-codebase-explorer` (parallel with `hw-external-researcher`)
- External research → `hw-external-researcher`
- Strategic planning → `hw-strategic-planner`
- Plan execution → `hw-plan-executor`
- Integration testing → `hw-integration-tester` (env health check + execution + result analysis)
- Delivery management → `hw-delivery-manager` (checklist verification + release notes)
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
<!-- Multi-Platform Target extracted to docs/multi-platform.md -->
> 三平台对比、技能发现机制、平台无关技能设计规范详见 [docs/multi-platform.md](docs/multi-platform.md)。

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
├── skills/                  # 32 skill directories
├── agents/                  # Standalone agent prompt templates
├── docs/                    # Documentation
├── hooks/                   # Session-start bootstrap
├── _bmad/                   # BMAD framework (config + memory)
│   ├── config.yaml          # Module configuration
│   └── memory/              # Agent shared state
├── .claude-plugin/          # Claude Code plugin manifest
├── .codex-plugin/           # Codex plugin manifest
└── .opencode/               # OpenCode plugin + config
```

> 完整目录结构（含所有技能子目录）详见 [docs/architecture.md](docs/architecture.md)。

<!-- Skill Design Patterns and Platform-Agnostic Skill Design extracted to docs/multi-platform.md -->
> SKILL.md 模板、frontmatter 约束、跨平台设计规范详见 [docs/multi-platform.md](docs/multi-platform.md)。

> 记忆架构的完整目录结构详见 [docs/architecture.md](docs/architecture.md)。

> 业务模板定制详见 [docs/configuration.md](docs/configuration.md)。

## Configuration

常用配置项（完整配置参考见 [docs/configuration.md](docs/configuration.md)）：

| Key | Default | Description |
|-----|---------|-------------|
| `business_domain` | `general` | 业务领域: general, fintech, ecommerce, internal-tools |
| `enabled_reviewers` | `security,logic,performance` | 启用的审查类型 |
| `min_iteration_before_human` | 3 | AI 自主迭代几次后升级到人工 |
| `communication_language` | `Chinese` | Human-Agent 交互语言 |
| `worktree_base` | `{project-root}/.worktree` | Worktree 目录位置 |

## Worktree Status Contract

Worktree controllers report to the top controller using these states:

| Status | Meaning | Controller Action |
|--------|---------|-------------------|
| `DONE` | Task complete, all gates passed | Mark complete, check merge readiness |
| `DONE_WITH_CONCERNS` | Complete but has reservations | Log concerns, evaluate human review |
| `NEEDS_CONTEXT` | Blocked on missing information | Provide context or escalate |
| `BLOCKED` | Stuck on dependency or issue | Analyze cause, resolve or escalate |

## 安装脚本

`install.py` 用于将黑灯工厂 skills 安装到其他项目：

```bash
# 安装到当前目录（Claude Code 模式，默认全部 skill）
python install.py

# 安装到指定项目
python install.py --target /path/to/project

# 安装到用户全局目录
python install.py --user

# 安装到 Codex 平台
python install.py --codex

# 只安装核心 skill（hw-controller, hw-tdd-agent, hw-reviewer-logic, hw-worktree-controller）
python install.py --minimal

# 预览安装效果（不实际写入）
python install.py --target /path/to/project --dry-run

# 同时安装到 Claude Code + Codex
python install.py --claude --codex
```

参数说明：
- `--target PATH` — 安装到指定项目目录（默认当前目录）
- `--user` — 安装到用户全局目录（`~/.claude/skills/`）
- `--claude` / `--codex` — 目标平台（默认 `--claude`）
- `--minimal` — 只安装 4 个核心 skill
- `--dry-run` — 预览模式，不实际写入
- `--force` — 跳过确认提示

## Commit Conventions

- Prefix based on intent: `feat:`, `fix:`, `docs:`, `refactor:`, etc.
- Include agent scope: `feat(hw-controller):`, `fix(hw-reviewer-security):`, etc.
- Keep commits bisectable — one logical change per commit
- Skills are product code even though they are Markdown — use `feat:`/`fix:`, not `docs:`

