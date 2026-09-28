# 黑灯工厂 (Harness Multi-Agent System)

[English](#english) | [中文](#中文)

---

## English

### What is 黑灯工厂?

黑灯工厂 (Black-light Factory) is a **human-AI collaborative software generation system** — orchestrate multiple specialized AI Agents in a pipeline from requirements to delivery. It implements the **Harness Engineering** philosophy: humans own strategic decisions, AI Agents handle execution and review.

**44 skills** covering the full E2E pipeline (v2), including package lifecycle and requirement-change propagation, following acceptance-driven development with a strict TDD iron law (no failing test, no production code).

### Supported Platforms

| Platform | Status | Guide |
|----------|--------|-------|
| **Claude Code** (Anthropic) | Primary | [Installation](#claude-code) |
| **Codex** (OpenAI) | Supported | [Installation](#codex-openai) |
| **OpenCode** | Supported | [Installation](#opencode) |

### Installation

#### One-click package lifecycle

Harness can be distributed as a verified package. Build once, publish to a
local directory or remote Git repository, then let an Agent download, install,
and initialize a project:

```bash
python package.py build --version 2.0.0 --output dist
python package.py publish --package dist/harness-multiagents-2.0.0.tar.gz --repository /srv/harness-packages
python package.py init --target /path/to/project --platform all
```

For the conversational flow, tell the Agent where to install, which package
repository/version to use, and which platforms/reviewers to enable. It routes
to `sw-setup`, verifies the manifest/checksums, preserves existing config, and
creates the `services/`, `knowledge/`, `_context/`, and `.worktree/` skeleton.
See [the package lifecycle guide](docs/package-lifecycle.md).

#### Start through an Agent

If the Harness skills are already available in your Agent, open a session in
the target project and send this message:

```text
Please use sw-setup to initialize this project. Ask me for the target directory, package source and version, enabled platforms, business domain, reviewers, and whether to install only core skills. Show me the write plan before applying it. After initialization, verify the installation record and tell me how to place source repositories under services/.
```

`sw-controller` can route the request to `sw-setup`. The Agent verifies the
package manifest and checksums, preserves existing configuration, and runs the
same `package.py init` flow documented above. If the Agent has not been
installed yet, run the interactive bootstrap once from this repository:

```bash
python scripts/interactive-init.py
```

The script asks the same setup questions in a terminal and is useful for the
first bootstrap or for environments without an interactive Agent session.

#### Requirement changes during a workflow

Use the change propagator when a requirement changes after design has started:

```bash
python change.py plan \
  --project-root . \
  --requirement-id REQ-001 \
  --kind partial \
  --current-phase service_design \
  --change "Add authorization checks"
```

`small` edits only the current step, `partial` regenerates the current and
downstream phases from the earliest affected phase, and `large` creates a new
requirement from ideation. Apply a reviewed packet with
`change.py apply --approve`; see [the change propagation guide](skills/sw-change-propagator/references/change-propagation.md).

#### Claude Code

**Prerequisites:** [Claude Code](https://claude.ai/code) installed.

**Step 1: Create project structure**

```bash
mkdir -p knowledge
mkdir -p knowledge/sw-controller
mkdir -p services knowledge
```

**Step 2: Configure**

Create `_context/config.yaml`:

```yaml
sw:
  business_domain: "general"            # general | fintech | ecommerce | internal-tools
  min_iteration_before_human: 3
  enabled_reviewers: "security,logic,performance"
  knowledge_base_auto_update: true
  merge_strategy: "merge"
```

Create `_context/config.user.yaml`:

```yaml
communication_language: Chinese
user_name: Your Name
```

After initialization, put every source repository to be modified under `services/{repository-name}/`. One repository and multiple repositories use the same flow. Project knowledge and workflow state are written to `knowledge/`; `_context/` is reserved for configuration.

**Step 3: Copy skills**

Copy the `skills/` directory from this repo into your project root. Minimum required skills: `sw-controller`, `sw-tdd-agent`, `sw-reviewer-logic`, `sw-worktree-controller`.

**Step 4: Update `.gitignore`**

```bash
echo ".worktree/" >> .gitignore
echo "_context-output/" >> .gitignore
```

**Step 5: Start developing**

```
/sw-controller I want to add a health check endpoint to the project
```

#### Codex (OpenAI)

See [docs/INSTALL-codex.md](docs/INSTALL-codex.md) for the full guide.

**Quick install:**

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/harness/services/multiagents/skills ~/.agents/skills/harness
```

Enable multi-agent support in `~/.codex/config.toml`:

```toml
[features]
multi_agent = true
```

Skills are auto-discovered on restart. Invoke by name: `sw-controller`, `sw-tdd-agent`, etc.

#### OpenCode

See [docs/INSTALL-opencode.md](docs/INSTALL-opencode.md) for the full guide.

**Quick install** — add to `opencode.json`:

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

Restart OpenCode. All skills auto-register.

### Quick Start

Four scenarios — pick your starting point:

| Scenario | Start Here |
|----------|-----------|
| I have an existing project | See [Scenario A](docs/quickstart-en.md#scenario-a-add-to-existing-project) |
| I'm starting a new project from scratch | See [Scenario B](docs/quickstart-en.md#scenario-b-new-project) |
| I have one or more source repositories | See [Scenario C](docs/quickstart-en.md#scenario-c-multi-repository-workspace) |
| I just want a 5-minute tour | Run `/sw-controller demo mode` |

Detailed walkthrough: [docs/quickstart-en.md](docs/quickstart-en.md)

### Agent Architecture (v2)

```
sw-controller (Orchestrator: Intent Gate + Phase Transition + Delegation)
  │
  ├── [需求层 Ideation]
  │     sw-requirements-clarifier / sw-value-judgment
  │
  ├── [规划层 Planning]
  │     sw-strategic-planner
  │       ├── sw-pre-planning-consultant
  │       ├── sw-plan-reviewer
  │       ├── sw-codebase-explorer
  │       └── sw-external-researcher
  │
  ├── [设计层 Design]
  │     sw-brainstorming
  │     sw-feature-designer → sw-service-designer × N → sw-e2e-designer
  │
  ├── [拆分层 Decomposition]
  │     sw-task-decomposer
  │
  ├── [执行层 Execution]
  │     sw-plan-executor
  │       └── sw-worktree-controller × N
  │             └── sw-tdd-agent
  │                   ├── sw-reviewer-logic / security / performance / context
  │     sw-receiving-review
  │
  ├── [测试层 Test]
  │     sw-integration-tester
  │
  ├── [交付层 Delivery]
  │     sw-delivery-manager
  │
  ├── [咨询层 Consultation]
  │     sw-strategic-advisor / sw-codebase-explorer / sw-external-researcher / sw-media-interpreter
  │
  └── [基础设施层 Infrastructure]
        sw-setup / sw-knowledge-agent / sw-systematic-debugging
        sw-verification-before-completion / sw-finishing-branch / sw-document-project
        sw-writing-skills / using-harness
```

### Directory Layout

```
multiagents/
├── skills/                  # Agent skill definitions (44 skills)
│   ├── sw-controller/       # Top-level orchestrator
│   ├── sw-tdd-agent/        # TDD cycle execution
│   ├── sw-worktree-controller/ # Single-task coordinator
│   ├── sw-reviewer-logic/   # Logic and correctness review
│   ├── sw-reviewer-security/ # Security vulnerability review
│   ├── sw-reviewer-performance/ # Performance review
│   ├── sw-strategic-planner/ # Strategic planner (NEW)
│   ├── sw-plan-executor/    # Plan execution orchestrator (NEW)
│   ├── sw-change-propagator/ # Requirement change propagation (NEW)
│   ├── sw-brainstorming/    # Pre-design exploration (NEW)
│   └── ...                  # 24 more specialized skills
├── agents/                  # Standalone agent prompt templates
├── services/                # User-provided source repositories
├── knowledge/               # Project knowledge + workflow state
├── _context/                # BMAD framework configuration
│   ├── config.yaml          # Project configuration
│   └── config.user.yaml     # User-specific settings
├── docs/                    # Documentation
├── hooks/                   # Session-start bootstrap
├── package.py               # Build/publish/download/install/init CLI
├── scripts/                 # Interactive bootstrap and utility scripts
│   └── interactive-init.py  # Terminal Q&A initialization
├── .claude-plugin/          # Claude Code plugin manifest
├── .codex-plugin/           # Codex plugin manifest
└── .opencode/               # OpenCode plugin + config
```

### Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `business_domain` | `general` | Domain template: `general`, `fintech`, `ecommerce`, `internal-tools` |
| `enabled_reviewers` | `security,logic,performance` | Active review types |
| `min_iteration_before_human` | `3` | AI iterations before human escalation |
| `communication_language` | `Chinese` | Human-Agent interaction language |

### Next Steps

- Read [CLAUDE.md](CLAUDE.md) for agent instructions and behavior rules
- Read [docs/quickstart-en.md](docs/quickstart-en.md) for detailed walkthroughs
- Learn core concepts: [docs/concepts.md](docs/concepts.md)
- Browse the agent catalog: [docs/agents.md](docs/agents.md)
- Understand the architecture: [docs/architecture.md](docs/architecture.md)
- Configure your project: [docs/configuration.md](docs/configuration.md)
- Customize lint check and deploy: [docs/customization.md](docs/customization.md)
- Explore skill definitions: `skills/sw-controller/SKILL.md`, `skills/sw-tdd-agent/SKILL.md`
- Learn the Harness Framework: [../harness_framework/](../harness_framework/)

---

## 中文

### 什么是黑灯工厂？

黑灯工厂是一套**人机协同的软件生成系统**——协调多个专业化 AI Agent 组成流水线，将人类决策与 AI 执行能力结合，实现从需求到交付的端到端自动化。遵循**验收驱动开发**和 TDD 铁律（无失败测试不写代码）。

**44 个技能**覆盖完整 E2E 流水线（v2），并包含发行打包与需求变更传播：需求 → 设计 → 拆分 → 执行 → 合并 → 测试 → 交付。

### 支持的平台

| 平台 | 状态 | 安装指引 |
|------|------|---------|
| **Claude Code** (Anthropic) | 主要平台 | [安装](#claude-code-1) |
| **Codex** (OpenAI) | 已支持 | [安装](#codex-openai-1) |
| **OpenCode** | 已支持 | [安装](#opencode-1) |

### 安装

#### 一键打包与初始化

```bash
python package.py build --version 2.0.0 --output dist
python package.py init --target /path/to/project --platform all
```

也可以通过本地目录或远程 Git 仓库发布、下载和安装。Agent 会先询问目标目录、
来源版本、平台和配置，再执行初始化。详见 [打包生命周期文档](docs/package-lifecycle.md)。

#### 通过 Agent 快速开始（推荐）

如果当前 Agent 已经安装了 Harness 技能，请在目标项目目录打开会话并发送：

```text
请使用 sw-setup 初始化当前项目。先询问我目标目录、安装包来源和版本、启用的平台、业务域、审核器以及是否只安装核心 skills；确认写入计划后执行初始化。初始化完成后检查安装清单，并告诉我下一步如何把源码仓放入 services/。
```

也可以让总控 Agent 路由：

```text
/sw-controller 请先完成 Harness 环境初始化，再开始处理我的需求。
```

Agent 会确认参数，校验清单和校验和，保留已有配置，并调用与
`package.py init` 相同的初始化流程。如果 Agent 尚未安装，先在本仓库执行
问答式引导脚本：

```bash
python scripts/interactive-init.py
```

脚本会逐项询问目标目录、包来源、平台和项目配置，确认后创建工作区并安装技能。

#### Claude Code

**前置条件：** 已安装 [Claude Code](https://claude.ai/code)。

**第一步：创建项目结构**

```bash
mkdir -p knowledge
mkdir -p knowledge/sw-controller
mkdir -p services knowledge
```

**第二步：配置**

创建 `_context/config.yaml`：

```yaml
sw:
  business_domain: "general"            # general | fintech | ecommerce | internal-tools
  min_iteration_before_human: 3         # AI 自主迭代次数，之后升级到人工
  enabled_reviewers: "security,logic,performance"
  knowledge_base_auto_update: true
  merge_strategy: "merge"
```

创建 `_context/config.user.yaml`：

```yaml
communication_language: Chinese
user_name: 你的名字
```

**第三步：复制技能目录**

将本仓库的 `skills/` 目录复制到你的项目根目录下。最少需要 4 个技能：`sw-controller`、`sw-tdd-agent`、`sw-reviewer-logic`、`sw-worktree-controller`。

推荐也复制：`sw-reviewer-security`、`sw-reviewer-performance`、`sw-setup`。

**第四步：更新 `.gitignore`**

```bash
echo ".worktree/" >> .gitignore
echo "_context-output/" >> .gitignore
```

**第五步：开始开发**

```
/sw-controller 我想给项目加一个健康检查端点
```

#### Codex (OpenAI)

完整指南：[docs/INSTALL-codex.md](docs/INSTALL-codex.md)

**快速安装：**

```bash
mkdir -p ~/.agents/skills
ln -s /path/to/harness/services/multiagents/skills ~/.agents/skills/harness
```

在 `~/.codex/config.toml` 中启用多 Agent 支持：

```toml
[features]
multi_agent = true
```

重启 Codex，技能自动发现。通过名称调用：`sw-controller`、`sw-tdd-agent` 等。

#### OpenCode

完整指南：[docs/INSTALL-opencode.md](docs/INSTALL-opencode.md)

**快速安装**——在 `opencode.json` 中添加：

```json
{
  "plugin": ["harness@git+https://github.com/wenxueliu/harness.git"]
}
```

或指向本地克隆：

```json
{
  "plugin": ["./services/multiagents/.opencode/plugins"]
}
```

重启 OpenCode，所有技能自动注册。

### 快速开始

四个场景，对号入座：

| 你的情况 | 入口 |
|----------|------|
| 已有项目，想接入黑灯工厂 | 见 [场景 A](docs/quickstart.md#场景-a已有项目接入) |
| 从零开始新项目 | 见 [场景 B](docs/quickstart.md#场景-b新项目启动) |
| 一个或多个代码仓，想统一编排 | 见 [场景 C](docs/quickstart.md#场景-c多仓库工作区接入) |
| 只想先体验一下 | 运行 `/sw-controller 体验模式` |

详细教程：[docs/quickstart.md](docs/quickstart.md)

### Agent 架构（v2）

```
sw-controller（总控：Intent Gate + Phase Transition + 委派纪律 — 只协调，不执行）
  │
  ├── [需求层 Ideation]
  │     sw-requirements-clarifier / sw-value-judgment
  │
  ├── [规划层 Planning]
  │     sw-strategic-planner
  │       ├── sw-pre-planning-consultant
  │       ├── sw-plan-reviewer
  │       ├── sw-codebase-explorer
  │       └── sw-external-researcher
  │
  ├── [设计层 Design]
  │     sw-brainstorming
  │     sw-feature-designer → sw-service-designer × N → sw-e2e-designer
  │
  ├── [拆分层 Decomposition]
  │     sw-task-decomposer
  │
  ├── [执行层 Execution]
  │     sw-plan-executor
  │       └── sw-worktree-controller × N
  │             └── sw-tdd-agent
  │                   ├── sw-reviewer-logic / security / performance / context
  │     sw-receiving-review
  │
  ├── [测试层 Test]
  │     sw-integration-tester
  │
  ├── [交付层 Delivery]
  │     sw-delivery-manager
  │
  ├── [咨询层 Consultation]
  │     sw-strategic-advisor / sw-codebase-explorer / sw-external-researcher / sw-media-interpreter
  │
  └── [基础设施层 Infrastructure]
        sw-setup / sw-knowledge-agent / sw-systematic-debugging
        sw-verification-before-completion / sw-finishing-branch / sw-document-project
        sw-writing-skills / using-harness
```

### 目录结构

```
multiagents/
├── skills/                  # Agent 技能定义（44 个技能）
│   ├── sw-controller/       # 总控
│   ├── sw-tdd-agent/        # TDD 执行
│   ├── sw-worktree-controller/ # 单任务协调
│   ├── sw-reviewer-logic/   # 逻辑审查
│   ├── sw-reviewer-security/ # 安全审查
│   ├── sw-reviewer-performance/ # 性能审查
│   ├── sw-strategic-planner/ # 战略规划（NEW）
│   ├── sw-plan-executor/    # 计划执行编排（NEW）
│   ├── sw-brainstorming/    # 头脑风暴（NEW）
│   └── ...                  # 其余 18 个专项技能
├── agents/                  # 独立 Agent prompt 模板
├── services/                # 用户放入的源码仓库
├── knowledge/               # 项目知识 + 工作流状态
├── _context/                # BMAD 框架配置
│   ├── config.yaml          # 项目配置
│   └── config.user.yaml     # 用户配置
├── docs/                    # 文档
├── hooks/                   # 会话启动引导
├── scripts/                 # 问答式初始化和辅助脚本
│   └── interactive-init.py  # 终端问答初始化
├── .claude-plugin/          # Claude Code 插件清单
├── .codex-plugin/           # Codex 插件清单
└── .opencode/               # OpenCode 插件 + 配置
```

### 配置参考

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `business_domain` | `general` | 业务领域模板：`general`、`fintech`、`ecommerce`、`internal-tools` |
| `enabled_reviewers` | `security,logic,performance` | 启用的审查类型 |
| `min_iteration_before_human` | `3` | AI 自主迭代几次后升级到人工 |
| `communication_language` | `Chinese` | 人机交互语言 |

### 下一步

- 阅读 [CLAUDE.md](CLAUDE.md) 了解 Agent 行为规则和指令
- 阅读 [docs/quickstart.md](docs/quickstart.md) 查看详细教程
- 了解核心概念：[docs/concepts.md](docs/concepts.md)
- 浏览全部 Agent 目录：[docs/agents.md](docs/agents.md)
- 了解系统架构：[docs/architecture.md](docs/architecture.md)
- 查看配置项：[docs/configuration.md](docs/configuration.md)
- 自定义规范检查和部署：[docs/customization.md](docs/customization.md)
- 探索技能定义：`skills/sw-controller/SKILL.md`、`skills/sw-tdd-agent/SKILL.md`
- 了解 Harness Framework：[../harness_framework/](../harness_framework/))

---

**开始你的第一次人机协同开发：** 打开 Claude Code，输入 `/sw-controller {你的需求}`
初始化完成后，请将需要修改的一个或多个独立 Git 代码仓放入 `services/{仓库名}/`；项目知识与工作流状态写入独立的 `knowledge/`，`_context/` 仅保存配置。
