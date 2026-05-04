---
name: using-harness
description: Use when starting any conversation in the Harness project — establishes the multi-agent skill system, agent hierarchy, and requires Skill tool invocation before ANY response including clarifying questions. [trigger: bootstrap, initialization, 黑灯工厂, harness workflow]
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill and execute your assigned task directly.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a Harness skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A HARNESS SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Instruction Priority

Harness skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, AGENTS.md, _bmad/config.yaml, direct requests) — highest priority
2. **Harness skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If AGENTS.md says "skip TDD for this project" and a skill says "always use TDD," follow AGENTS.md. The user is in control.

## How to Access Skills

**In Claude Code:** Use the `Skill` tool. When you invoke a skill, its content is loaded — follow it directly. Never use the Read tool on skill files.

**In Codex:** Skills load natively. Reference the skill by name — Codex parses SKILL.md frontmatter at startup and loads full content on invocation. Use `$skill-name` or reference the skill's logical name.

**In OpenCode:** Use the native `skill` tool. Skills are auto-discovered from registered skill paths. List with `skill` tool and load by name.

**In other environments:** Check your platform's documentation for how skills are loaded. See `references/codex-tools.md` and `references/opencode-tools.md` for platform-specific tool mappings.

## Platform Adaptation

Skills describe intent, not tool names. When you encounter a platform-specific reference:
- Codex users: see `references/codex-tools.md`
- OpenCode users: see `references/opencode-tools.md`
- All platforms: the AGENTS.md Platform Feature Matrix has the canonical adaptation rules

# Using Harness Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

## The Harness Agent Hierarchy

Harness organizes agents in a tree — always start at the root and traverse down:

```
hw-controller (orchestrator — the entry point for any development workflow)
  ├── hw-setup (environment initialization)
  └── hw-worktree-controller (per-task coordinator) × N
        ├── hw-tdd-agent (RED → GREEN → REFACTOR)
        ├── hw-reviewer-logic (correctness + edge cases)
        ├── hw-reviewer-security (vulnerabilities + data exposure)
        └── hw-reviewer-performance (bottlenecks + scalability)
```

**Rule:** When a user asks to build, fix, or develop something, start with `hw-controller`. The controller assesses the request, runs value judgment, initiates design phases, decomposes into tasks, and dispatches worktree controllers. Never jump directly to `hw-tdd-agent` or reviewers — they expect to be invoked within the controller's workflow.

## Skill Priority

When multiple skills could apply, traverse the hierarchy from top to bottom:

1. **Orchestration first** — `hw-controller` for any development workflow; `hw-setup` for environment initialization
2. **Execution second** — `hw-worktree-controller` dispatches `hw-tdd-agent` per task
3. **Review third** — `hw-reviewer-logic`, `hw-reviewer-security`, `hw-reviewer-performance` run in parallel after TDD cycles
4. **Design skills** — `hw-feature-designer`, `hw-service-designer`, `hw-e2e-designer` are invoked by hw-controller during design phases

"Build a new feature" → hw-controller first.
"Fix a bug" → hw-controller first (it will assess and dispatch).
"Review this code" → hw-reviewer-logic + hw-reviewer-security + hw-reviewer-performance in parallel.

## Red Flags

These thoughts mean STOP — you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for Harness skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can just write the code directly" | TDD iron law: no production code without a failing test. |
| "This doesn't need the full workflow" | The controller decides scope. Don't pre-judge. |
| "I remember this skill" | Skills evolve. Read the current version. |
| "The review can wait" | Reviews are non-negotiable gates. No exceptions. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This is too small for multi-agent" | Even small changes benefit from TDD + review gates. |
| "I can skip the controller" | The controller owns phase transitions. Don't bypass it. |

## Skill Types

**Rigid** (TDD, reviews): Follow exactly. Don't adapt away discipline. The TDD iron law and review gates are non-negotiable.

**Flexible** (design, setup): Adapt principles to context. The designer agents present options for human judgment.

The skill itself tells you which type it is.

## Working with the Knowledge Base

The knowledge base (`_bmad/memory/hw-shared/knowledge-base/`) accumulates institutional knowledge:
- **Before starting work:** Check for relevant ADRs (`decisions/`), patterns (`patterns/`), and lessons (`lessons/`)
- **After completing work:** Deposit new patterns, decisions, and lessons
- **KB health:** Run `python scripts/kb-health.py` periodically to detect staleness and gaps

## Human in the Loop

Harness is a human-AI collaborative system. Key checkpoints where humans must be involved:
- Value judgment on requirements (P0/P1/P2/P3 prioritization)
- Design approval (after hw-feature-designer and hw-service-designer)
- Iteration limit reached (escalate, don't loop)
- P0/P1 review issues (human must decide on risk acceptance)
- Merge/delivery decisions (human owns the final approval)

Never remove the human from critical-path decisions. When in doubt, escalate.

## Configuration Awareness

Read `_bmad/config.yaml` and `_bmad/config.user.yaml` at session start. Key settings that affect behavior:
- `enabled_reviewers` — which reviews are active (don't run disabled reviewers)
- `business_domain` — drives template selection and gate strictness
- `min_iteration_before_human` — when to escalate
- `communication_language` — what language to use for human communication
