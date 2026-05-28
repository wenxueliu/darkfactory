# OpenCode Tool Mapping

Harness skills use platform-neutral intent descriptions. When you encounter these patterns in a skill, use your OpenCode equivalent:

## Core Tool Mapping

| Skill references | OpenCode equivalent |
|-----------------|---------------------|
| `Skill` tool (invoke a skill) | OpenCode's native `skill` tool — list and load skills |
| `Agent` tool (dispatch subagent) | OpenCode's subagent system (`@agent-name` or agent config in `opencode.json`) |
| `Task` tool with `run_in_background` | OpenCode async operations or parallel subagent dispatch |
| `TodoWrite` (task tracking) | `todowrite` — OpenCode's native task tracking |
| `Read`, `Write`, `Edit` (file ops) | Your native tools |
| `Bash` (run commands) | Your native shell tools |
| `WebFetch` / `WebSearch` | Your native web tools |
| `EnterPlanMode` / `ExitPlanMode` | OpenCode's plan/research mode |

## Subagent Dispatch

OpenCode supports subagent dispatch through agent configurations. When a Harness skill says to dispatch a named agent type:

1. Check if the agent is defined in `.opencode/opencode.json` under `agents`
2. Use OpenCode's subagent dispatch mechanism to invoke it
3. Pass the task context from the skill's instructions

### Agent Role Mapping

| Harness agent | OpenCode agent | Purpose |
|---------------|----------------|---------|
| sw-controller | `controller` (in opencode.json) | Top-level orchestrator |
| sw-tdd-agent | `tdd-agent` (in opencode.json) | TDD cycle execution |
| sw-reviewer-logic | `reviewer-logic` (in opencode.json) | Logic review |
| sw-reviewer-security | `reviewer-security` (in opencode.json) | Security review |
| sw-reviewer-performance | `reviewer-performance` (in opencode.json) | Performance review |
| sw-worktree-controller | Custom subagent with worktree-controller prompt | Task execution coordinator |

## Parallel Dispatch

When a skill says to run reviews in parallel:

```
# Dispatch all three reviewers simultaneously:
- reviewer-logic
- reviewer-security
- reviewer-performance
```

OpenCode handles parallelism through its agent system. Each reviewer subagent receives the same code context but applies different review criteria.

## Plugin System

The Harness OpenCode plugin (`.opencode/plugins/harness.js`) automatically:
1. Registers the `skills/` directory so all Harness skills are discoverable
2. Injects the `using-harness` bootstrap into the first user message of each session

Skills are auto-discovered — no symlinks or manual config needed.

## Skill Discovery

Use the native `skill` tool to:
- List all available skills (includes all Harness + any personal/project skills)
- Load a specific skill by name

Skill priority: Project skills (`.opencode/skills/`) > Personal skills (`~/.config/opencode/skills/`) > Harness skills (registered by plugin)

## Configuration Files

Harness uses YAML config files in `_context/`. OpenCode can read these natively:

- `_context/config.yaml` — module configuration (reviewers, business domain, gates)
- `_context/config.user.yaml` — user-specific settings (language, user name)

Read these at session start to adapt behavior. The `communication_language` field controls what language to use for responses.

## Stage-Bridge Integration

When the Harness framework (Consul KV) is running, OpenCode agents communicate via the stage-bridge scripts. The platform-specific prompt template is at `skills/stage-bridge/templates/opencode_prompt.md` in the harness_framework project.

The template recommends wrapping each stage-bridge script as an OpenCode tool with explicit exit-code handling. Four phases:
1. Bootstrap (register agent + heartbeat)
2. Task loop (claim → read context → execute → log → complete)
3. Repair loop (feedback listen → diagnose → fix → resolve)
4. Shutdown (deregister + cleanup)
