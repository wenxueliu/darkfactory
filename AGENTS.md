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

The system has 7 active agents in v1 (hw-value-judgment and hw-knowledge-agent are collapsed into hw-controller, with references wired as controller capabilities):

```
hw-controller (Orchestrator: requirements + design + knowledge + orchestration + delivery)
  ├── hw-setup (Module installation and configuration)
  └── hw-worktree-controller (Single-task coordinator) × N
        ├── hw-tdd-agent (TDD execution)
        ├── hw-reviewer-logic (Logic review)
        ├── hw-reviewer-security (Security review)
        └── hw-reviewer-performance (Performance review)
```

### Agent Roles (v1, 7 agents)

| Agent | Role | Trigger |
|-------|------|---------|
| `hw-controller` | Top-level orchestrator — full E2E: requirements → design → decomposition → execution → merge → test → delivery. Also handles value judgment and knowledge management. | 黑灯工厂, orchestration, coordination |
| `hw-setup` | Module installer — configures worktree directories and memory structure | 安装黑灯工厂, setup, configuration |
| `hw-worktree-controller` | Task executor — drives single task through TDD + review + quality gates | worktree execution, task development |
| `hw-tdd-agent` | TDD practitioner — enforces RED→GREEN→REFACTOR cycle (UT + API layers) | TDD, unit test, test-first |
| `hw-reviewer-logic` | Logic reviewer — finds correctness bugs and edge cases | logic review, correctness review |
| `hw-reviewer-security` | Security reviewer — finds vulnerabilities and data exposure | security review, vulnerability scan |
| `hw-reviewer-performance` | Performance reviewer — finds bottlenecks and scalability issues | performance review, bottleneck analysis |

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
│   ├── hw-controller/       # Top-level orchestrator
│   ├── hw-setup/            # Module installation and configuration
│   ├── hw-worktree-controller/ # Single-task execution coordinator
│   ├── hw-tdd-agent/        # TDD cycle execution
│   ├── hw-reviewer-logic/   # Logic and correctness review
│   ├── hw-reviewer-security/ # Security vulnerability review
│   ├── hw-reviewer-performance/ # Performance and scalability review
│   ├── hw-feature-designer/ # Cross-service feature design
│   ├── hw-service-designer/ # Single-service detailed design
│   ├── hw-e2e-designer/     # E2E integration test design
│   ├── hw-value-judgment/   # Requirements value assessment
│   ├── hw-knowledge-agent/  # Knowledge base management
│   └── using-harness/       # Bootstrap skill (injected at session start)
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
