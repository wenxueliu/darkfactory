# 黑灯工厂 (Harness Multi-Agent System)

[English](#english) | [中文](#中文)

---

## English

### What is 黑灯工厂?

黑灯工厂 (Black-light Factory) is a **human-AI collaborative software generation system** — orchestrate multiple specialized AI Agents in a pipeline from requirements to delivery. It implements the **Harness Engineering** philosophy: humans own strategic decisions, AI Agents handle execution and review.

**13 skills** covering the full E2E pipeline, following acceptance-driven development with a strict TDD iron law (no failing test, no production code).

### Supported Platforms

| Platform | Status | Guide |
|----------|--------|-------|
| **Claude Code** (Anthropic) | Primary | [Installation](#claude-code) |
| **Codex** (OpenAI) | Supported | [Installation](#codex-openai) |
| **OpenCode** | Supported | [Installation](#opencode) |

### Installation

#### Claude Code

**Prerequisites:** [Claude Code](https://claude.ai/code) installed.

**Step 1: Create project structure**

```bash
mkdir -p _bmad/memory/hw-shared
mkdir -p _bmad/memory/hw-controller
```

**Step 2: Configure**

Create `_bmad/config.yaml`:

```yaml
hw:
  architecture: "monolith"              # or "microservices"
  business_domain: "general"            # general | fintech | ecommerce | internal-tools
  min_iteration_before_human: 3
  enabled_reviewers: "security,logic,performance"
  knowledge_base_auto_update: true
  merge_strategy: "merge"
```

Create `_bmad/config.user.yaml`:

```yaml
communication_language: Chinese
user_name: Your Name
```

**Step 3: Copy skills**

Copy the `skills/` directory from this repo into your project root. Minimum required skills: `hw-controller`, `hw-tdd-agent`, `hw-reviewer-logic`, `hw-worktree-controller`.

**Step 4: Update `.gitignore`**

```bash
echo ".worktree/" >> .gitignore
echo "_bmad-output/" >> .gitignore
```

**Step 5: Start developing**

```
/hw-controller I want to add a health check endpoint to the project
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

Skills are auto-discovered on restart. Invoke by name: `hw-controller`, `hw-tdd-agent`, etc.

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
| I have an existing project | See [Scenario A](docs/quickstart.md#scenario-a-existing-project) |
| I'm starting a new project from scratch | See [Scenario B](docs/quickstart.md#scenario-b-new-project) |
| I have multiple microservices | See [Scenario C](docs/quickstart.md#scenario-c-microservices-multi-repo) |
| I just want a 5-minute tour | Run `/hw-controller demo mode` |

Detailed walkthrough: [docs/quickstart.md](docs/quickstart.md)

### Agent Architecture (v1)

```
hw-controller (Orchestrator: requirements → design → decomposition → execution → delivery)
  ├── hw-setup (Environment initialization)
  ├── hw-feature-designer (Cross-service feature design)
  ├── hw-service-designer (Single-service design)
  ├── hw-e2e-designer (E2E test design)
  ├── hw-value-judgment (Requirements value assessment)
  ├── hw-knowledge-agent (Knowledge base management)
  └── hw-worktree-controller (Single-task coordinator) × N
        ├── hw-tdd-agent (RED → GREEN → REFACTOR)
        ├── hw-reviewer-logic (Correctness + edge cases)
        ├── hw-reviewer-security (Vulnerabilities + data exposure)
        └── hw-reviewer-performance (Bottlenecks + scalability)
```

### Directory Layout

```
multiagents/
├── skills/                  # Agent skill definitions (13 skills)
│   ├── hw-controller/       # Top-level orchestrator
│   ├── hw-tdd-agent/        # TDD cycle execution
│   ├── hw-worktree-controller/ # Single-task coordinator
│   ├── hw-reviewer-logic/   # Logic and correctness review
│   ├── hw-reviewer-security/ # Security vulnerability review
│   ├── hw-reviewer-performance/ # Performance review
│   └── ...                  # 7 more specialized skills
├── _bmad/                   # BMAD framework (config + memory)
│   ├── config.yaml          # Project configuration
│   ├── config.user.yaml     # User-specific settings
│   └── memory/              # Agent shared state
├── docs/                    # Documentation
├── hooks/                   # Session-start bootstrap
└── scripts/                 # Knowledge base management tools
```

### Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `business_domain` | `general` | Domain template: `general`, `fintech`, `ecommerce`, `internal-tools` |
| `enabled_reviewers` | `security,logic,performance` | Active review types |
| `min_iteration_before_human` | `3` | AI iterations before human escalation |
| `architecture` | `microservices` | `monolith` or `microservices` |
| `communication_language` | `Chinese` | Human-Agent interaction language |

### Next Steps

- Read [CLAUDE.md](CLAUDE.md) for the full project guide
- Read [docs/quickstart.md](docs/quickstart.md) for detailed walkthroughs
- Explore skill definitions: `skills/hw-controller/SKILL.md`, `skills/hw-tdd-agent/SKILL.md`
- Learn the Harness Framework: [../harness_framework/](../harness_framework/)

---

## 中文

### 什么是黑灯工厂？

黑灯工厂是一套**人机协同的软件生成系统**——协调多个专业化 AI Agent 组成流水线，将人类决策与 AI 执行能力结合，实现从需求到交付的端到端自动化。遵循**验收驱动开发**和 TDD 铁律（无失败测试不写代码）。

**13 个技能**覆盖完整 E2E 流水线：需求 → 设计 → 拆分 → 执行 → 合并 → 测试 → 交付。

### 支持的平台

| 平台 | 状态 | 安装指引 |
|------|------|---------|
| **Claude Code** (Anthropic) | 主要平台 | [安装](#claude-code-1) |
| **Codex** (OpenAI) | 已支持 | [安装](#codex-openai-1) |
| **OpenCode** | 已支持 | [安装](#opencode-1) |

### 安装

#### Claude Code

**前置条件：** 已安装 [Claude Code](https://claude.ai/code)。

**第一步：创建项目结构**

```bash
mkdir -p _bmad/memory/hw-shared
mkdir -p _bmad/memory/hw-controller
```

**第二步：配置**

创建 `_bmad/config.yaml`：

```yaml
hw:
  architecture: "monolith"              # 单体服务，或 "microservices" 微服务
  business_domain: "general"            # general | fintech | ecommerce | internal-tools
  min_iteration_before_human: 3         # AI 自主迭代次数，之后升级到人工
  enabled_reviewers: "security,logic,performance"
  knowledge_base_auto_update: true
  merge_strategy: "merge"
```

创建 `_bmad/config.user.yaml`：

```yaml
communication_language: Chinese
user_name: 你的名字
```

**第三步：复制技能目录**

将本仓库的 `skills/` 目录复制到你的项目根目录下。最少需要 4 个技能：`hw-controller`、`hw-tdd-agent`、`hw-reviewer-logic`、`hw-worktree-controller`。

推荐也复制：`hw-reviewer-security`、`hw-reviewer-performance`、`hw-setup`。

**第四步：更新 `.gitignore`**

```bash
echo ".worktree/" >> .gitignore
echo "_bmad-output/" >> .gitignore
```

**第五步：开始开发**

```
/hw-controller 我想给项目加一个健康检查端点
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

重启 Codex，技能自动发现。通过名称调用：`hw-controller`、`hw-tdd-agent` 等。

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
| 多个微服务，想统一编排 | 见 [场景 C](docs/quickstart.md#场景-c微服务多仓接入) |
| 只想先体验一下 | 运行 `/hw-controller 体验模式` |

详细教程：[docs/quickstart.md](docs/quickstart.md)

### Agent 架构（v1）

```
hw-controller（总控：需求 → 设计 → 拆分 → 执行 → 交付）
  ├── hw-setup（环境初始化）
  ├── hw-feature-designer（跨服务特性设计）
  ├── hw-service-designer（单服务设计）
  ├── hw-e2e-designer（端到端测试设计）
  ├── hw-value-judgment（需求价值评估）
  ├── hw-knowledge-agent（知识库管理）
  └── hw-worktree-controller（单任务协调）× N
        ├── hw-tdd-agent（RED → GREEN → REFACTOR）
        ├── hw-reviewer-logic（正确性 + 边界审查）
        ├── hw-reviewer-security（漏洞 + 数据暴露审查）
        └── hw-reviewer-performance（瓶颈 + 扩展性审查）
```

### 目录结构

```
multiagents/
├── skills/                  # Agent 技能定义（13 个技能）
│   ├── hw-controller/       # 总控
│   ├── hw-tdd-agent/        # TDD 执行
│   ├── hw-worktree-controller/ # 单任务协调
│   ├── hw-reviewer-logic/   # 逻辑审查
│   ├── hw-reviewer-security/ # 安全审查
│   ├── hw-reviewer-performance/ # 性能审查
│   └── ...                  # 其余 7 个专项技能
├── _bmad/                   # BMAD 框架（配置 + 记忆）
│   ├── config.yaml          # 项目配置
│   ├── config.user.yaml     # 用户配置
│   └── memory/              # Agent 共享状态
├── docs/                    # 文档
├── hooks/                   # 会话启动引导
└── scripts/                 # 知识库管理工具
```

### 配置参考

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `business_domain` | `general` | 业务领域模板：`general`、`fintech`、`ecommerce`、`internal-tools` |
| `enabled_reviewers` | `security,logic,performance` | 启用的审查类型 |
| `min_iteration_before_human` | `3` | AI 自主迭代几次后升级到人工 |
| `architecture` | `microservices` | `monolith` 或 `microservices` |
| `communication_language` | `Chinese` | 人机交互语言 |

### 下一步

- 阅读 [CLAUDE.md](CLAUDE.md) 了解完整项目指南
- 阅读 [docs/quickstart.md](docs/quickstart.md) 查看详细教程
- 探索技能定义：`skills/hw-controller/SKILL.md`、`skills/hw-tdd-agent/SKILL.md`
- 了解 Harness Framework：[../harness_framework/](../harness_framework/)

---

**开始你的第一次人机协同开发：** 打开 Claude Code，输入 `/hw-controller {你的需求}`
