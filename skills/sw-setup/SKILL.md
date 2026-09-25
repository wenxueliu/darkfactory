---
name: sw-setup
description: "黑灯工厂模块安装配置. Use when installing or updating the 黑灯工厂 module, configuring worktree directories, or initializing shared memory structure. [trigger: 安装黑灯工厂, 配置hw, 初始化]"
---

# 黑灯工厂 模块安装 (sw-setup)

## Overview

This skill installs and configures the **黑灯工厂 (SW)** module. It sets up shared memory structure, configures worktree directories, and registers the module capabilities.

**Your Mission:** Get 黑灯工厂 ready to run.

## On Activation

### Module Identity

- **Module name:** 黑灯工厂
- **Module code:** sw
- **Version:** 1.0.0

### Configuration Collected

| Variable | Prompt | Default |
|----------|--------|---------|
| `worktree_base` | Worktree目录位置 | `{project-root}/.worktree` |
| `min_iteration_before_human` | 人工介入前最小迭代次数 | 3 |
| `enabled_reviewers` | 启用的审核类型(逗号分隔) | `security,logic,performance` |
| `knowledge_base_auto_update` | 开发完成后自动更新知识库 | `true` |
| `merge_strategy` | Worktree合并策略 | `merge` |

## Setup Tasks

### 1. Create Directory Structure

```bash
# Create worktree directory
mkdir -p {worktree_base}

# Verify it's in gitignore
git check-ignore {worktree_base} || echo "{worktree_base} not in gitignore!"
```

### 2. Initialize Shared Memory

```bash
# Create the workspace structure. The user must put source repositories under services/ after initialization.
mkdir -p {project-root}/services
mkdir -p {project-root}/knowledge
mkdir -p {project-root}/knowledge/_enterprise/{patterns,decisions,lessons,contracts}
mkdir -p {project-root}/knowledge/domains
mkdir -p {project-root}/knowledge/services
{project-root}/_context/memory/
├── sw-shared/
│   ├── requirements-tracker.yaml
│   ├── tasks.yaml
│   ├── design-decisions.md
│   ├── human-interventions.md
│   └── reviews/
└── sw-controller/
    ├── global-state.yaml
    └── worktree-registry.yaml
```

初始化完成后的硬前置条件：

1. 用户将需要修改的一个或多个独立 Git 代码仓放入 `{project-root}/services/{repository-name}/`。
2. 项目知识统一写入 `{project-root}/knowledge/`（全局知识位于 `knowledge/_enterprise/`）；`_context/` 只保存配置、流程产物和机器状态。
3. 运行服务发现，生成 `_context/memory/sw-shared/service-registry.yaml` 和 `knowledge/services/{service-id}/`。
4. `services/` 为空时阻塞后续开发，并提示用户先放入源码仓。

### 3. Register Capabilities

Register all 黑灯工厂 skills in the module help system.

## Configuration Files

Config is written to:
- `{project-root}/_context/config.yaml` — module section (sw)
- `{project-root}/_context/config.user.yaml` — user settings

## Capabilities

| Capability | Route |
| ---------- | ----- |
| InitializeMemory | Load `references/init-memory.md` |
| ConfigureWorktree | Load `references/config-worktree.md` |
| RegisterModule | Load `references/register-module.md` |
| ServiceBootstrap | Load `references/service-bootstrap.md` |

## Verification

After setup:
1. Verify worktree directory exists and is gitignored
2. Verify shared memory structure created
3. Verify config written correctly
4. Report setup status
