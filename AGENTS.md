# 黑灯工厂 (HW) — Harness Engineering 落地实现

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
- **Natural language switching:** Agent communication and document output language is controlled by `communication_language` in `_bmad/config.user.yaml` (default: `Chinese`). Switch to `English`/`Japanese`/`Korean` for international teams.
- **Business scenario adaptation:** Configure via `_bmad/config.yaml` — enable/disable reviewers, adjust gate strictness, customize knowledge base structure. One set of Agent definitions serves web apps, API services, data pipelines, embedded systems.

### Rapid Business Adaptation

| Dimension | Mechanism | Example |
|-----------|-----------|---------|
| Tech stack | `references/` per-language pattern files | Python project loads `references/patterns-python.md` |
| Quality policy | `enabled_reviewers` config | Fintech: security+logic+performance; Internal tools: logic only |
| Workflow rhythm | `min_iteration_before_human` | Exploratory: high value; Critical: low value |
| Knowledge domain | `knowledge-base/` structure customization | Microservices: emphasize `api-contracts/`; Data projects: emphasize `patterns/` |
| Delivery strategy | `merge_strategy` | Continuous deploy: `rebase`; Conservative: `merge` |
| Natural language | `communication_language` | Chinese / English / Japanese teams |

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

| Phase | Templates | Gate Check |
|-------|-----------|------------|
| **ideation** | `requirements-spec-template.md`, value assessment | `requirements-gate.md` |
| **design** | `design-doc-template.md`, `adr-template.md` | `design-gate.md` |
| **decomposition** | `task-decomposition.md` → `tasks.yaml` | dependency check |
| **execution** | TDD cycles + parallel review | P0/P1/P2 gate |
| **merge** | `merge-management.md` | conflict-free merge |
| **test** | `integration-test-plan.md` | all IT PASS |
| **delivery** | `delivery-checklist.md`, `release-notes-template.md` | `delivery-acceptance-gate.md` |

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

This project's skills run identically on three agent platforms:

| Platform | Skill location | Config | Instruction file | Invocation |
|----------|---------------|--------|------------------|------------|
| **Claude Code** | `skills/<name>/SKILL.md` | `.claude/settings.json` | `CLAUDE.md` | `/<skill-name>` |
| **Codex (OpenAI)** | `.agents/skills/<name>/SKILL.md` | `~/.codex/config.toml` | `AGENTS.md` (this file) | `/skills` or `$skill-name` |
| **OpenCode** | `.opencode/skills/<name>/SKILL.md` | `opencode.json` | `opencode.json` instructions | via plugin agent |

### Cross-Platform Invocation

**Claude Code:** Skills auto-discovered from `skills/` at project root or `.claude/skills/`. Invoke via the Skill tool with the skill name (e.g., `Skill tool with skill="hw-tdd-agent"`).

**Codex:** Skills discovered from `.agents/skills/` (repo-scoped) or `~/.agents/skills/` (user-scoped). Invoke by referencing the skill name — Codex loads the full SKILL.md on invocation.

**OpenCode:** Skills loaded from `.opencode/skills/` (project) or `~/.config/opencode/skills/` (global). The Harness OpenCode plugin auto-registers skill paths and injects bootstrap context.

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
- **Delegate complex work:** Prefer delegating complex, multi-step, or cross-file search/analysis tasks to subagents. Run independent subagents in parallel to reduce main context window consumption.
- **Dual instruction files:** This repo maintains both `CLAUDE.md` (Claude Code) and `AGENTS.md` (Codex). `AGENTS.md` is the canonical instruction file — `CLAUDE.md` points to it via `@AGENTS.md`. Keep them in sync; when in doubt, `AGENTS.md` is the source of truth.
- **No platform-specific variables:** NEVER use `${CLAUDE_PLUGIN_ROOT}`, `${CODEX_SANDBOX}`, or any other platform-only environment variable in skill content. See Platform-Agnostic Skill Design below.
- **Cross-OS compatibility:** All skills, scripts, and tooling MUST run on **Windows**, **Linux**, and **macOS**. Use forward-slash (`/`) path separators. Avoid shell-specific syntax in skill scripts — prefer POSIX-compatible commands. When OS-specific behavior is unavoidable, use `references/` pattern files per OS. Never assume a case-sensitive filesystem.

## Directory Layout

```
multiagents/
├── skills/                  # Agent skill definitions
│   ├── hw-controller/       # Top-level orchestrator (ENHANCED)
│   ├── hw-strategic-planner/ # Strategic planner (NEW — Prometheus)
│   ├── hw-pre-planning-consultant/ # Pre-planning analyst (NEW — Metis)
│   ├── hw-plan-reviewer/    # Plan executability reviewer (NEW — Momus)
│   ├── hw-plan-executor/    # Plan execution orchestrator (NEW — Atlas)
│   ├── hw-codebase-explorer/ # Internal code search (NEW — Explore)
│   ├── hw-external-researcher/ # External docs/OSS research (NEW — Librarian)
│   ├── hw-strategic-advisor/ # Strategic technical advisor (NEW — Oracle)
│   ├── hw-media-interpreter/ # Media file interpreter (NEW — Multimodal Looker)
│   ├── hw-brainstorming/    # Pre-design exploration (NEW)
│   ├── hw-feature-designer/ # Cross-service feature design
│   ├── hw-service-designer/ # Single-service detailed design
│   ├── hw-e2e-designer/     # E2E integration test design
│   ├── hw-worktree-controller/ # Single-task execution coordinator
│   ├── hw-tdd-agent/        # TDD cycle execution (ENHANCED)
│   ├── hw-reviewer-logic/   # Logic and correctness review
│   ├── hw-reviewer-security/ # Security vulnerability review
│   ├── hw-reviewer-performance/ # Performance and scalability review
│   ├── hw-reviewer-context/ # Context mining — missed requirements discovery
│   ├── hw-receiving-review/ # Review feedback processing (NEW)
│   ├── hw-setup/            # Module installation
│   ├── hw-knowledge-agent/  # Knowledge base management
│   ├── hw-value-judgment/   # Requirements value assessment
│   ├── hw-systematic-debugging/ # Systematic debugging
│   ├── hw-verification-before-completion/ # Pre-completion verification
│   ├── hw-finishing-branch/ # Branch completion (NEW)
│   ├── hw-writing-skills/   # Meta-skill for skill authoring (NEW)
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
- Language patterns go in `references/` — e.g., `references/patterns-python.md`. The SKILL.md routes to the correct pattern based on detected project language.
- Business domain config goes in `_bmad/config.yaml` — reviewer selection, gate strictness, knowledge structure. Agent behavior adapts to config, not hardcoded branches.

## Platform-Agnostic Skill Design

Skills are authored once and run on Claude Code, Codex, and OpenCode. Every design decision must work across all three.

### Frontmatter Constraints

YAML frontmatter is the universal metadata format across all three platforms. Constraints:

- **`name`** (required): ≤ 100 characters (Codex limit). kebab-case, ASCII only. Must match the skill directory name.
- **`description`** (required): ≤ 500 characters (Codex limit). Include trigger keywords in both Chinese and English for cross-platform discovery.
- **No platform-only frontmatter fields.** `allowed-tools` (Claude Code), `argument-hint` (Codex) — these break on other platforms.

```yaml
---
name: hw-tdd-agent
description: TDD execution agent. Use when executing TDD cycles, writing unit tests. [trigger: TDD, 单元测试, 测试先行, RED-GREEN-REFACTOR]
---
```

### File References: Relative Paths Only

All file references in SKILL.md MUST use relative paths from the skill directory:

```
# CORRECT — relative to skill directory
Run scripts/run-tests.sh
Load references/tdd-ut-cycle.md

# BROKEN — platform-specific variables
${CLAUDE_PLUGIN_ROOT}/skills/hw-tdd-agent/references/tdd-ut-cycle.md

# BROKEN — absolute paths
/home/user/.claude/skills/hw-tdd-agent/references/tdd-ut-cycle.md

# BROKEN — cross-skill traversal
../hw-controller/references/global-state.md
```

### State References: Token-Based, Not Path-Based

```
# CORRECT — token resolved by each platform
Load task from {project-root}/_bmad/memory/hw-shared/tasks.yaml

# BROKEN — assumes specific working directory
Load task from /home/user/project/_bmad/memory/hw-shared/tasks.yaml
```

### Tool Calls: Platform-Neutral Patterns

Describe intent, not tool names:

```
# CORRECT — describes what to do
Delegate the review to the security reviewer agent

# BROKEN — platform-specific tool name
Use the Agent tool with subagent_type=hw-reviewer-security
```

When agent-to-agent delegation is needed, describe the target agent by its logical name (`hw-reviewer-security`). Each platform's runtime resolves this to its native delegation mechanism.

### Bash Blocks: Self-Contained

- Each bash code block runs in a separate shell. Variables do not persist.
- Use natural language for logic and state, not shell variables.
- Keep bash blocks self-contained.
- Express conditionals as English, not nested `if/elif/else`.

### Character Encoding

- **Identifiers** (file names, agent names, command names): ASCII only.
- **Markdown tables:** Pipe-delimited, never box-drawing characters.
- **Prose:** Unicode is fine. Prefer ASCII arrows (`->`, `<-`) in code blocks.

### Parallel Execution: Describe Intent

```
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
| Instruction file | `CLAUDE.md` | `AGENTS.md` (this file) | instructions in JSON | Maintain `AGENTS.md` as canonical; `CLAUDE.md` delegates to it |
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

## Configuration

Default config (overridable in `_bmad/config.yaml` and `_bmad/config.user.yaml`):

| Key | Default | Description |
|-----|---------|-------------|
| `worktree_base` | `{project-root}/.worktree` | Worktree directory location |
| `min_iteration_before_human` | 3 | Iterations before escalating to human |
| `enabled_reviewers` | `security,logic,performance` | Active review types |
| `knowledge_base_auto_update` | `true` | Auto-update KB after development |
| `merge_strategy` | `merge` | Worktree merge strategy |
| `document_output_language` | `Chinese` | Agent communication and document output language |
| `communication_language` | `Chinese` | Human-Agent interaction language |
| `supported_languages` | `*` (auto-detect) | Target programming languages |
| `business_domain` | `general` | Business domain: `general`, `fintech`, `ecommerce`, `internal-tools`, `java-springboot-enterprise` |
| `custom_templates` | (empty) | Optional custom template paths |

## Worktree Status Contract

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
