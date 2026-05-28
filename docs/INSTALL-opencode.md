# Installing Harness Multi-Agent System for OpenCode

> **New here?** See [README.md](../README.md#opencode) for the quick install. This is the detailed OpenCode installation and configuration guide.

Complete guide for using Harness with [OpenCode.ai](https://opencode.ai).

## Installation

Harness auto-installs via OpenCode's plugin system. Add to your `opencode.json` (global or project-level):

```json
{
  "plugin": ["harness@git+https://github.com/wenxueliu/harness.git"]
}
```

Or point to a local clone:

```json
{
  "plugin": ["./services/multiagents/.opencode/plugins"]
}
```

Restart OpenCode. The plugin auto-registers all skills and injects the bootstrap context.

Verify by asking: "Tell me about the Harness multi-agent system"

## Usage

### Finding Skills

Use OpenCode's native `skill` tool to list all available skills:

```
use skill tool to list skills
```

### Loading a Skill

```
use skill tool to load sw-controller
```

### Starting a Development Workflow

```
use skill tool to load sw-controller
```

The controller will guide you through ideation → design → decomposition → execution → delivery.

### Running Code Reviews

Harness provides three parallel reviewers:

```
use skill tool to load sw-reviewer-logic
use skill tool to load sw-reviewer-security
use skill tool to load sw-reviewer-performance
```

## Agent Roles

The `opencode.json` defines these agent roles in the `agents` section:

| Harness Agent | OpenCode Role | Purpose |
|---------------|---------------|---------|
| sw-controller | `controller` | Orchestrator |
| sw-tdd-agent | `tdd-agent` | TDD execution |
| sw-reviewer-logic | `reviewer-logic` | Logic review |
| sw-reviewer-security | `reviewer-security` | Security review |
| sw-reviewer-performance | `reviewer-performance` | Performance review |

## Configuration

Harness reads from `_context/config.yaml` and `_context/config.user.yaml`. Key settings:
- `communication_language` — response language (default: Chinese)
- `business_domain` — template selection (general, fintech, ecommerce, etc.)
- `enabled_reviewers` — which reviews are active

## Updating

Harness updates automatically when you restart OpenCode. The plugin is re-installed from the git repository on each launch.

To pin a specific version, use a branch or tag:

```json
{
  "plugin": ["harness@git+https://github.com/wenxueliu/harness.git#v1.0.0"]
}
```

## How It Works

The plugin does two things:

1. **Injects bootstrap context** via the `experimental.chat.messages.transform` hook, adding Harness awareness to every conversation.
2. **Registers the skills directory** via the `config` hook, so OpenCode discovers all Harness skills without symlinks or manual config.

### Tool Mapping

Skills written for Claude Code are automatically adapted for OpenCode:
- `TodoWrite` → `todowrite`
- `Agent` tool with subagents → OpenCode's subagent system (`@mention`)
- `Skill` tool → OpenCode's native `skill` tool
- File operations → Native OpenCode tools

## Troubleshooting

### Plugin not loading

1. Check OpenCode logs for Harness plugin messages
2. Verify the plugin path in your `opencode.json`
3. Make sure you're running a recent version of OpenCode

### Skills not found

1. Use OpenCode's `skill` tool to list available skills
2. Check that the plugin is loading
3. Each skill needs a `SKILL.md` file with valid YAML frontmatter

### Bootstrap not appearing

1. Restart OpenCode after config changes
2. Check that `skills/using-harness/SKILL.md` exists

## Getting Help

- Report issues: https://github.com/wenxueliu/harness/issues
- Main documentation: `services/multiagents/CLAUDE.md`
- OpenCode docs: https://opencode.ai/docs/
