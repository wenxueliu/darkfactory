---
name: sw-setup
description: "黑灯工厂安装、升级与工作区初始化 Agent。Use when installing, downloading, packaging, publishing, upgrading, or conversationally initializing Harness in a project or user directory. [trigger: 安装黑灯工厂, 配置hw, 初始化, 打包, 发布, 下载, 升级]"
metadata:
  version: "2.0.0"
  external_dependencies:
    - name: git
      version: ">=2.30"
      type: TOOL
      required: false
      purpose: remote Git package publishing and repository download
    - name: package.py
      version: "1.0.0"
      type: TOOL
      required: true
      purpose: verified package build, download, install, and workspace initialization
    - name: sw-knowledge-agent
      version: "*"
      type: SKILL
      required: false
      purpose: post-initialization service discovery and knowledge registration
---

# 黑灯工厂安装与初始化 (sw-setup)

## Overview

This Skill owns the Harness lifecycle before development starts: selecting a
package source, verifying and installing it, creating the shared workspace,
and handing control to `sw-controller`. It supports both a terminal command
and an Agent-led interview. The Agent interview is the user-facing entrypoint;
`package.py` is the deterministic execution layer.

**Contract version:** `2.0.0` (frontmatter metadata).

## Input Contract

The Agent must collect or resolve these values before writing files:

| Input | Required | Default / rule |
|---|---:|---|
| `target` | Yes | Project directory to initialize or install into. |
| `source` | No | Current Harness checkout, local package repository, archive URL, or remote Git package repository. |
| `scope` | No | `project`; `user` installs to the user directory when no explicit target is supplied. |
| `platforms` | No | `claude,codex,opencode`; the user may choose a subset. |
| `business_domain` | No | `general`; supported project variants are resolved by downstream skills. |
| `communication_language` | No | `Chinese`. |
| `user_name` | No | Empty string; never infer identity. |
| `worktree_base` | No | `{project-root}/.worktree`. |
| `enabled_reviewers` | No | `security,logic,performance`. |
| `merge_strategy` | No | `merge`. |
| `version` | No | Repository `latest`, or the explicit package version. |

Do not ask for values that can be safely defaulted. Do ask before a write if
the target, scope, package source, platform, or an existing configuration
would materially change the result.

## Agent Conversation Protocol

Start with a compact interview, then show a plan for confirmation:

1. Where should Harness be installed or initialized?
2. Is the source the current checkout, a local package repository, a remote
   Git repository, or a direct archive URL? Which version, if not `latest`?
3. Which agent platforms should be enabled: Claude Code, Codex, OpenCode, or
   all three?
4. What business domain, communication language, reviewer set, and worktree
   directory should the workspace use?
5. Are the proposed writes acceptable, including project config, hooks, skills,
   and `knowledge/` skeleton?

After confirmation, run the CLI in non-interactive mode. Never ask the user to
manually copy skill directories as part of this flow. If `services/` is empty,
finish initialization but clearly report that the user must place one or more
independent Git source repositories under `services/{repository-name}/` before
development can start.

## Package Lifecycle

Use [references/package-lifecycle.md](references/package-lifecycle.md) for the
package manifest, repository index, command matrix, and failure handling.

The normal sequence is:

1. `build` creates a checksum-tracked `.tar.gz` package.
2. `publish` copies it to a local repository or commits and pushes it to a
   remote Git repository.
3. `download` resolves an explicit version or the repository's `latest` entry.
4. `install` verifies the archive, installs selected platforms, and records
   `.harness/installation.json`.
5. `init` creates the workspace skeleton and then installs the package.
6. Verify the target, report the package version, and route to
   `sw-controller`/`sw-knowledge-agent` for service discovery.

Examples:

```bash
python package.py build --version 2.0.0 --output dist
python package.py publish --package dist/harness-multiagents-2.0.0.tar.gz --repository /srv/harness-packages
python package.py download --source /srv/harness-packages --version 2.0.0 --output /tmp/downloads
python package.py install --source /srv/harness-packages --target /workspace/app --platform claude,codex
python package.py init --target /workspace/app --platform all --business-domain general
```

Remote publishing requires Git credentials and explicit user authorization at
the time the `publish` command is run. A failed clone, push, checksum, or
manifest validation is a blocked setup—not permission to fall back to an
unverified archive.

## Workspace Setup Tasks

`init` creates these paths if absent and never overwrites existing config:

```text
{project-root}/
├── services/
├── knowledge/
│   ├── index.md
│   ├── requirements-tracker.yaml
│   ├── {patterns,decisions,lessons,contracts}/
│   ├── domains/
│   ├── services/
│   └── sw-controller/{global-state.yaml,worktree-registry.yaml}
├── _context/{config.yaml,config.user.yaml}
└── .worktree/
```

The user must put source repositories under `services/` after initialization.
Project knowledge and workflow state stay under `knowledge/`; `_context/` is
reserved for configuration.

## Output Contract

Return a machine-readable summary and a short human report containing:

| Output | Required |
|---|---:|
| `status` | `READY`, `BLOCKED`, or `NEEDS_USER_INPUT`. |
| `package` / `version` | Resolved package identity and version when installation was requested. |
| `target` / `scope` / `platforms` | Exact installation destination and selected platforms. |
| `created_paths` | New workspace paths; existing paths are not claimed as created. |
| `verification` | Manifest/checksum, installed entrypoints, config, and Git-ignore checks. |
| `next_action` | Put source repositories in `services/`, then invoke `sw-controller`. |
| `dependency_status` | `USED`, `SKIPPED`, or `NOT_REQUESTED` for each external capability. |

## External Dependency Metadata

`package.py` is required and must be executed locally from the selected
package. Git and `sw-knowledge-agent` are optional capabilities:

```text
USED — {dependency}; evidence: {command/result}
SKIPPED — {dependency}; reason: {unavailable or not requested}; impact: {limited capability}; fallback: {safe local behavior}
```

When Git is unavailable, local archive installation remains available but
remote Git publishing/download is `BLOCKED`. When `sw-knowledge-agent` is
unavailable, initialization still completes and service discovery is reported
as `SKIPPED`; do not invent a service registry.

## Acceptance Criteria

- Version and dependency metadata are present and match the executed package.
- The selected archive contains a valid manifest and every declared payload
  checksum verifies after extraction.
- Local publish updates `packages/index.json` and resolves `latest` correctly.
- Remote publish uses an explicit Git clone/commit/push sequence and reports
  failures without claiming success.
- Project and user/directory installation routes to the selected platform
  paths without silently changing unrelated files.
- Re-running `init` is idempotent and does not overwrite existing config.
- The Agent asks for the material choices, confirms the write plan, and
  produces the output contract above.
- A fresh project has `services/`, `knowledge/`, `_context/`, a gitignored
  worktree, and an explicit next action for adding source repositories.
- `sw-controller` is invoked only after setup verification passes.

## Verification

1. Run `python package.py --help` and the package lifecycle command relevant to
   the request.
2. Run `python -m pytest tests/test_package_manager.py -q`.
3. Verify the selected target paths and `.harness/installation.json`.
4. Verify `services/` contains the user-provided source repository before
   beginning a development workflow.
