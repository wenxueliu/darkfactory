# 黑灯工厂 (SW) — Harness Engineering 落地实现

## Overview

黑灯工厂 (Black-light Factory) is the implementation of **Harness Engineering** philosophy — a **human-AI collaborative software generation system**. It orchestrates multiple specialized AI Agents in a pipeline that combines human decision-making with AI execution, achieving end-to-end automation from requirements to delivery.

**Harness Engineering core principles:**
- **Human in the loop** — humans own value judgment, strategic decisions, final approval; AI executes, reviews, verifies
- **Agent orchestration** — multi-Agent collaboration with clear role boundaries and communication protocols
- **Gate-driven quality** — quality gates are non-negotiable; every phase must pass acceptance criteria to advance
- **Knowledge accumulation** — every development cycle deposits reusable knowledge; the knowledge base grows with the project

The platform follows **acceptance-driven development** with a strict TDD iron law: no production code without a failing test first.

### Multi-Language Support

- **Language-agnostic:** Agents don't bind to specific programming languages. TDD Agent adapts to pytest/Jest/JUnit/Go test/PHPUnit. Reviewer Agents load language-specific review patterns. Adding a language means extending `references/` pattern files — never modifying Agent core logic.
- **Natural language switching:** Agent communication and document output language is controlled by `communication_language` in `_context/config.user.yaml` (default: `Chinese`). Switch to `English`/`Japanese`/`Korean` for international teams.
- **Business scenario adaptation:** Configure via `_context/config.yaml` — enable/disable reviewers, adjust gate strictness, customize knowledge base structure. One set of Agent definitions serves web apps, API services, data pipelines, embedded systems.

> Config-driven business adaptation details: see [docs/configuration.md](docs/configuration.md).

## Agent Architecture

The system has 33 skills in v2:

```
sw-controller (增强: Intent Gate + Phase Transition + 委派纪律 — 只协调，不执行)
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
  │
  ├── [测试层 — Test]
  │     sw-integration-tester (NEW: 集成测试 — 环境健康检查+执行+结果分析)
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
        sw-knowledge-agent (REVIVED: 知识库管理 — 查询+更新+索引)
        sw-systematic-debugging (系统化调试)
        sw-verification-before-completion (完成前验证)
        sw-finishing-branch (NEW: 分支收尾 — 4-option终端状态)
        sw-document-project (NEW: 项目文档生成 — brownfield scanning + 3-level scan)
        sw-writing-skills (NEW: 元技能 — TDD应用于文档编写)
        sw-grill-docs (NEW: 文档对照质询 — 设计/计划 vs CONTEXT.md + ADRs)
        using-harness (bootstrap技能)
```

<!-- Agent Roles and E2E Phase Coverage extracted to standalone docs -->
> All 33 agent roles, triggers, and capabilities: [docs/agents.md](docs/agents.md).
> E2E phase coverage and gate checks: [docs/architecture.md](docs/architecture.md).

### Development Flow

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

### Intent Gate (Sisyphus → sw-controller)
Every activation begins with intent verification: classify the request type, check for ambiguity, and route to the appropriate agent layer. Implementation only proceeds when an explicit implementation verb is present, scope is concrete, requirement clarification has passed, and no specialist result is pending. Surface explicitness is not a substitute for requirements verification.

### Autonomous Execution (Hephaestus → sw-tdd-agent)
"Do NOT Ask — Just Do." The TDD agent exhausts the exploration hierarchy (direct tools → codebase search → external research → context inference) before asking any question. When blocked, it tries different approaches rather than stopping.

### Structured Planning (Prometheus → sw-strategic-planner)
Planning follows interview → research → plan generation → review. Drafts serve as working memory between turns. Plans include explicit QA scenarios that are agent-executable (no "user manually tests" criteria).

### Parallel Orchestration (Atlas → sw-plan-executor)
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

**The sw-controller and sw-plan-executor MUST delegate non-trivial work to specialized subagents.** Direct tool calls are for trivial tasks only. After 3+ direct tool calls without using the Agent tool, the hook injects a reminder.

When to delegate (MUST):
- Requirements clarification → `sw-requirements-clarifier` (4-step progressive dialogue → spec document)
- Value assessment → `sw-value-judgment` (ROI + strategic alignment + 5-dimension scoring)
- Knowledge base query/update → `sw-knowledge-agent` (ADR, patterns, lessons, service discovery)
- Task decomposition → `sw-task-decomposer` (service identification → DAG → Wave → tasks.yaml)
- Complex, multi-step code operations → `sw-tdd-agent` (via `sw-worktree-controller`)
- Code reviews → `sw-reviewer-logic`, `sw-reviewer-security`, `sw-reviewer-performance`, `sw-reviewer-context`
- Codebase exploration → `sw-codebase-explorer` (parallel with `sw-external-researcher`)
- External research → `sw-external-researcher`
- Strategic planning → `sw-strategic-planner`
- Plan execution → `sw-plan-executor`
- Integration testing → `sw-integration-tester` (env health check + execution + result analysis)
- Delivery management → `sw-delivery-manager` (checklist verification + release notes)
- Key design/plan document review → `sw-grill-docs` (grill against CONTEXT.md + ADRs, update docs inline)
- Deep technical consultation → `sw-strategic-advisor`
- Media file analysis → `sw-media-interpreter`

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

### Hook Language (`hooks/*`)

**All hook scripts MUST be written in Python, not bash.** Use `python3` to invoke them directly (e.g., `python3 "${workspaceFolder}/hooks/ideation-gate.py"`). No new bash hooks. When modifying existing bash hooks, convert them to Python first.

---

## Multi-Platform Target

> Multi-platform comparison, skill discovery, and platform-agnostic skill design: [docs/multi-platform.md](docs/multi-platform.md).

## Working Agreement

- **Harness Engineering first:** This is a human-AI collaborative system. Human judgment is the ultimate backstop on strategic decisions, value trade-offs, and final approval. AI agents handle execution, review, and verification. Never remove the human from critical-path decisions.
- **Language-agnostic design:** Agent core logic MUST not assume a specific programming language. Language-specific patterns live in `references/` and are loaded on activation. When adding a new language, add pattern files — do not modify agent SKILL.md.
- **Business scenario flexibility:** Agents are configured, not rewritten, for different business domains. Every behavioral difference between scenarios should be expressed as a config value, not a code branch.
- **Skill isolation:** Each skill directory (`skills/sw-*/`) is self-contained. Skills reference only files within their own directory tree. If two skills need the same supporting file, duplicate it into each skill's directory.
- **No cross-skill references:** NEVER use `../other-skill/references/`, absolute paths, or platform-cache paths to reference sibling skill files. Skill directories are the unit of portability — when converted/copied to another platform, sibling directories may not exist.
- **Branching:** Create a feature branch for non-trivial changes. If already on the correct branch, keep using it — do not create additional branches or worktrees unless requested.
- **Safety:** Do not delete or overwrite user data. Avoid destructive commands.
- **Configuration:** Project config lives in `_context/config.yaml` and `_context/config.user.yaml`. Read config before assuming defaults.
- **Shared state:** All cross-agent state lives in `_context/memory/sw-shared/`. Agent-private state lives in `_context/memory/sw-{agent}/`.
- **Worktrees:** Isolated task execution happens in `{worktree_base}` (default: `.worktree/` at project root). This directory must be gitignored.
- **Language:** This project uses Chinese for agent communication and documentation. Config defaults to `document_output_language: Chinese`.
- **Delegate complex work:** Prefer delegating complex, multi-step, or cross-file search/analysis tasks to subagents. Run independent subagents in parallel to reduce main context window consumption.
- **Dual instruction files:** This repo maintains both `CLAUDE.md` (Claude Code) and `AGENTS.md` (Codex). `AGENTS.md` is the canonical instruction file — `CLAUDE.md` points to it via `@AGENTS.md`. Keep them in sync; when in doubt, `AGENTS.md` is the source of truth.
- **No platform-specific variables:** NEVER use `${CLAUDE_PLUGIN_ROOT}`, `${CODEX_SANDBOX}`, or any other platform-only environment variable in skill content.
- **Cross-OS compatibility:** All skills, scripts, and tooling MUST run on **Windows**, **Linux**, and **macOS**. Use forward-slash (`/`) path separators. Avoid shell-specific syntax in skill scripts — prefer POSIX-compatible commands. When OS-specific behavior is unavoidable, use `references/` pattern files per OS. Never assume a case-sensitive filesystem.

## Directory Layout

```
multiagents/
├── skills/                  # 32 skill directories
├── agents/                  # Standalone agent prompt templates
├── docs/                    # Documentation
├── hooks/                   # Session-start bootstrap
├── _context/                   # BMAD framework (config + memory)
│   ├── config.yaml              # Module configuration
│   └── memory/                  # Agent shared state
│       └── sw-shared/
│           ├── requirements-tracker.yaml  # Requirement lifecycle tracking
│           ├── tasks.yaml                 # Task definitions
│           └── ...
├── .claude-plugin/          # Claude Code plugin manifest
├── .codex-plugin/           # Codex plugin manifest
└── .opencode/               # OpenCode plugin + config
```

> Full directory tree with per-skill entries: [docs/architecture.md](docs/architecture.md).

> SKILL.md template, frontmatter constraints, and cross-platform design rules: [docs/multi-platform.md](docs/multi-platform.md).

> Memory architecture: [docs/architecture.md](docs/architecture.md).

## Configuration

Commonly used config keys (full reference: [docs/configuration.md](docs/configuration.md)):

| Key | Default | Description |
|-----|---------|-------------|
| `business_domain` | `general` | Domain: general, fintech, ecommerce, internal-tools |
| `enabled_reviewers` | `security,logic,performance` | Active review types |
| `min_iteration_before_human` | 3 | Iterations before human escalation |
| `communication_language` | `Chinese` | Human-Agent interaction language |
| `worktree_base` | `{project-root}/.worktree` | Worktree directory location |

## Worktree Status Contract

| Status | Meaning | Controller Action |
|--------|---------|-------------------|
| `DONE` | Task complete, all gates passed | Mark complete, check merge readiness |
| `DONE_WITH_CONCERNS` | Complete but has reservations | Log concerns, evaluate human review |
| `NEEDS_CONTEXT` | Blocked on missing information | Provide context or escalate |
| `BLOCKED` | Stuck on dependency or issue | Analyze cause, resolve or escalate |

## Commit Conventions

- Prefix based on intent: `feat:`, `fix:`, `docs:`, `refactor:`, etc.
- Include agent scope: `feat(sw-controller):`, `fix(sw-reviewer-security):`, etc.
- Keep commits bisectable — one logical change per commit
- Skills are product code even though they are Markdown — use `feat:`/`fix:`, not `docs:`
