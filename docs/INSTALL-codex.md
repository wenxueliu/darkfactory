# Installing Harness Multi-Agent System for Codex

> **New here?** See [README.md](../README.md#codex-openai) for the quick install. This is the detailed Codex installation and configuration guide.

Enable Harness skills, lifecycle hooks, and multi-agent orchestration in Codex.

## Prerequisites

- Git
- OpenAI Codex CLI

## Installation

### Option 0: One-click install (recommended)

If you already have the Harness repo cloned:

```bash
python /path/to/harness/services/multiagents/install.py --codex --user
```

This copies all skills to `~/.agents/skills/`, installs the Python hooks under
`~/.codex/hooks/`, and writes `~/.codex/hooks.json`. Add `--minimal` for just
the 4 core skills, or `--target /path/to/project` for a project-local install.
The legacy `agents/*.md` templates are Claude-specific and are not copied into
Codex's skill directory; Codex multi-agent delegation is driven by the Harness
skills and Codex's native `multi_agent` tools.

For project-local installation, Codex writes hooks to `<project>/.codex/`.
Trust the project, restart Codex, then use `/hooks` to review and trust the
installed hook definitions. Codex records trust against the exact hook hash,
so updated hooks must be reviewed again.

If Harness is installed as a Codex plugin instead, Codex discovers
`skills/` and `hooks/hooks.json` directly from the plugin. Do not also run the
standalone installer for the same scope, or every hook will run twice.

### Option 1: Symlink from existing clone

If you already have the Harness repo cloned:

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/harness/services/multiagents/skills ~/.agents/skills/harness
```

This option installs skills only. Use Option 0 or install the repository as a
Codex plugin when lifecycle enforcement is required.

### Option 2: Clone directly

```bash
git clone https://github.com/wenxueliu/harness.git ~/.codex/harness
mkdir -p ~/.agents/skills
ln -s ~/.codex/harness/services/multiagents/skills ~/.agents/skills/harness
```

This option also installs skills only.

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
hooks = true
```

Both features are enabled by default in current Codex releases, but declaring
them explicitly makes the Harness dependency visible. Hooks require a Codex
version that supports lifecycle hooks; verify with `codex features list`.

## Verify

```bash
ls -la ~/.agents/skills/
ls -la ~/.codex/hooks/
python -m json.tool ~/.codex/hooks.json
```

You should see the Harness skills directory with all sw-* skill directories and SKILL.md files. Restart Codex and ask:

```
What Harness skills are available?
```

Codex should discover all Harness skills. Open `/hooks` and confirm the Harness
hooks are enabled and trusted. The `using-harness` bootstrap skill establishes
the full skill system, while lifecycle hooks enforce ideation and write-safety
gates around `apply_patch` and other supported local tools.

For Codex edits, the write-safety hook accepts an `apply_patch` update when it
contains matching original-file context. File deletion still requires a prior
file-read event. This adapts the Claude `Read`-then-`Write` contract to Codex's
context-aware patch tool without silently allowing context-free overwrites.

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
rm -rf ~/.agents/skills/sw-* ~/.agents/skills/using-harness
```

Then remove the Harness Python files from `~/.codex/hooks/` and the matching
Harness groups from `~/.codex/hooks.json`. Do not delete those locations
wholesale if they also contain hooks from other tools.

Optionally delete the clone: `rm -rf ~/.codex/harness`
