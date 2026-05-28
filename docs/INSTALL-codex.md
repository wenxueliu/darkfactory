# Installing Harness Multi-Agent System for Codex

> **New here?** See [README.md](../README.md#codex-openai) for the quick install. This is the detailed Codex installation and configuration guide.

Enable Harness skills in Codex via native skill discovery.

## Prerequisites

- Git
- OpenAI Codex CLI

## Installation

### Option 0: One-click install (recommended)

If you already have the Harness repo cloned:

```bash
python /path/to/harness/services/multiagents/install.py --codex --user
```

This copies all skills to `~/.agents/skills/`. Add `--minimal` for just the 4 core skills, or `--target /path/to/project` for project-local install.

### Option 1: Symlink from existing clone

If you already have the Harness repo cloned:

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/harness/services/multiagents/skills ~/.agents/skills/harness
```

### Option 2: Clone directly

```bash
git clone https://github.com/wenxueliu/harness.git ~/.codex/harness
mkdir -p ~/.agents/skills
ln -s ~/.codex/harness/services/multiagents/skills ~/.agents/skills/harness
```

### Windows (PowerShell)

Use a junction instead of a symlink (works without Developer Mode):

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
cmd /c mklink /J "$env:USERPROFILE\.agents\skills\harness" "C:\path\to\harness\services\multiagents\skills"
```

## Enable Multi-Agent Support

Harness heavily uses subagent dispatch. Add to your Codex config:

```toml
# ~/.codex/config.toml
[features]
multi_agent = true
```

## Verify

```bash
ls -la ~/.agents/skills/harness
```

You should see the Harness skills directory with all sw-* skill directories and SKILL.md files. Restart Codex and ask:

```
What Harness skills are available?
```

Codex should discover all Harness skills. The `using-harness` bootstrap skill establishes the full skill system.

## Usage

Skills are discovered automatically. Invoke by name:
- `sw-controller` — start a development workflow
- `sw-tdd-agent` — TDD cycle execution
- `sw-reviewer-security` — security review

The `using-harness` skill loads automatically and directs proper skill usage.

## Stage-Bridge Integration

If you're using the Harness Framework (Consul KV-based orchestration), the stage-bridge skill provides Agent↔Framework communication. See `services/harness_framework/skills/stage-bridge/` for scripts and platform-specific prompt templates.

## Updating

```bash
cd ~/.codex/harness && git pull
```

Skills update instantly through the symlink.

## Uninstalling

```bash
rm ~/.agents/skills/harness
```

Optionally delete the clone: `rm -rf ~/.codex/harness`
