# Codex Tool Mapping

Harness skills use platform-neutral intent descriptions. When you encounter these patterns in a skill, use your Codex equivalent:

## Core Tool Mapping

| Skill references | Codex equivalent |
|-----------------|------------------|
| Subagent delegation (dispatch to another agent) | `spawn_agent` — see [Named agent dispatch](#named-agent-dispatch) below |
| Multiple parallel subagent dispatches | Multiple `spawn_agent` calls |
| Wait for subagent result | `wait` |
| Release subagent slot | `close_agent` |
| Task tracking (TodoWrite) | `update_plan` |
| Skill tool (invoke a skill) | Skills load natively — just follow the instructions |
| Read, Write, Edit (file ops) | Use your native file tools |
| Bash (run commands) | Use your native shell tools |

## Multi-Agent Support

Harness heavily uses subagent dispatch (hw-controller → worktree-controller → tdd-agent / reviewers). Enable multi-agent support in your Codex config:

```toml
# ~/.codex/config.toml
[features]
multi_agent = true
```

This enables `spawn_agent`, `wait`, and `close_agent`.

## Named Agent Dispatch

Harness skills reference named agent types like `hw-reviewer-security`, `hw-tdd-agent`, etc. Codex does not have a named agent registry — `spawn_agent` creates generic agents from built-in roles (`default`, `explorer`, `worker`).

When a skill says to dispatch a named agent:

1. Find the agent's prompt template — either in `agents/<agent-name>.md` or in the skill's `references/` directory
2. Read the prompt content
3. Fill any template placeholders (e.g., `{TASK_NAME}`, `{REQ_ID}`, `{REPO_PATH}`)
4. Spawn a `worker` agent with the filled content as the `message`

| Skill instruction | Codex equivalent |
|-------------------|------------------|
| "Dispatch hw-reviewer-logic" | `spawn_agent(agent_type="worker", message=...)` with `agents/hw-reviewer-logic.md` content |
| "Dispatch hw-tdd-agent for this task" | `spawn_agent(agent_type="worker", message=...)` with `agents/hw-tdd-agent.md` content |
| "Run reviews in parallel" | Multiple simultaneous `spawn_agent` calls |
| "Delegate to hw-worktree-controller" | `spawn_agent(agent_type="worker", message=...)` with worktree-controller prompt |

### Message Framing

The `message` parameter is user-level input. Structure it for maximum instruction adherence:

```
Your task is to perform the following. Follow the instructions below exactly.

<agent-instructions>
[filled prompt content from the agent's .md file]
</agent-instructions>

Execute this now. Output ONLY the structured response following the format
specified in the instructions above.
```

- Use task-delegation framing ("Your task is...") rather than persona framing
- Wrap instructions in XML tags — the model treats tagged blocks as authoritative
- End with an explicit execution directive

## Environment Detection

Skills that create worktrees or finish branches should detect their environment:

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```

- `GIT_DIR != GIT_COMMON` → already in a linked worktree (skip creation)
- `BRANCH` empty → detached HEAD (cannot branch/push/PR from sandbox)

## Codex App Finishing

When the Codex sandbox blocks branch/push operations (detached HEAD in an externally managed worktree), commit all work and inform the user to use the App's native controls:

- **"Create branch"** — name the branch, then commit/push/PR via App UI
- **"Hand off to local"** — transfer work to the user's local checkout

The agent can still run tests, stage files, and output suggested branch names, commit messages, and PR descriptions.

## Stage-Bridge Integration

When the Harness framework (Consul KV) is running, Codex agents communicate via the stage-bridge scripts. The platform-specific prompt template is at `skills/stage-bridge/templates/codex_prompt.md` in the harness_framework project. Key workflow phases:

1. **Bootstrap:** Register agent + start heartbeat
2. **Task Loop:** Claim task via CAS → read context → execute → log → complete
3. **Repair Loop:** Listen for feedback → diagnose → fix → resolve
4. **Shutdown:** Deregister agent + cleanup
