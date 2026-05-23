# 多平台技能开发 (Multi-Platform Skill Design)

> **需要背景？** 先看 [README.md](../README.md) 了解项目概览。本文是高级指南，适用于需要编写或迁移跨平台技能的贡献者。

---

黑灯工厂的技能需要同时在 **Claude Code**、**Codex (OpenAI)** 和 **OpenCode** 三个平台上运行。本文档定义了确保跨平台兼容性的设计约束和最佳实践。

---

## 平台对比

| 平台 | 技能位置 | 配置文件 | 指令文件 | 调用方式 |
|------|---------|---------|---------|---------|
| **Claude Code** | `skills/<name>/SKILL.md` | `.claude/settings.json` | `CLAUDE.md` | `/<skill-name>` |
| **Codex (OpenAI)** | `.agents/skills/<name>/SKILL.md` | `~/.codex/config.toml` | `AGENTS.md` | `/skills` or `$skill-name` |
| **OpenCode** | `.opencode/skills/<name>/SKILL.md` | `opencode.json` | `opencode.json` instructions | via plugin agent |

### 技能发现机制

- **Claude Code:** 自动发现 `skills/` 或 `.claude/skills/` 下的技能。技能是包含 `SKILL.md` + 可选 `references/`、`scripts/`、`assets/` 的目录。
- **Codex:** 自动发现 `.agents/skills/`（仓库级）或 `~/.agents/skills/`（用户级）下的技能。启动时只加载 name/description，调用时注入完整内容。
- **OpenCode:** 从 `.opencode/skills/`（项目级）或 `~/.config/opencode/skills/`（全局级）加载技能。

---

## 平台无关的技能设计

技能编写一次，在三个平台上运行。每个设计决策必须跨平台工作。

### Frontmatter 约束

YAML frontmatter 是三个平台通用的元数据格式：

- **`name`**（必需）：≤ 100 字符（Codex 限制）。kebab-case，仅 ASCII。必须匹配技能目录名。
- **`description`**（必需）：≤ 500 字符（Codex 限制）。包含中英文触发词以实现跨平台发现。这是 Codex 启动时加载的唯一内容。
- **禁止平台特有的 frontmatter 字段：** `allowed-tools`（Claude Code）、`argument-hint`（Codex）等在其他平台会出错。

```yaml
---
name: hw-tdd-agent
description: TDD执行Agent. Use when executing TDD cycles, writing unit tests. [trigger: TDD, 单元测试, 测试先行, RED-GREEN-REFACTOR]
---
```

### 文件引用：仅相对路径

SKILL.md 中所有文件引用必须使用相对路径（相对于技能目录）：

```
# 正确 — 相对于技能目录
Run scripts/run-tests.sh
Load references/tdd-ut-cycle.md

# 错误 — 平台特有变量
${CLAUDE_PLUGIN_ROOT}/skills/hw-tdd-agent/references/tdd-ut-cycle.md

# 错误 — 绝对路径
/home/user/.claude/skills/hw-tdd-agent/references/tdd-ut-cycle.md

# 错误 — 跨技能引用（目标平台可能不存在）
../hw-controller/references/global-state.md
```

原因：Claude Code 在版本化路径缓存插件；Codex 沙箱化技能；OpenCode 从多源合并配置。相对路径是唯一可移植的模式。

### 状态引用：基于 Token，非基于路径

技能通过逻辑 token 引用共享状态，而非文件系统路径：

```
# 正确 — 各平台解析为自己的记忆根目录
Load task from {project-root}/_bmad/memory/hw-shared/tasks.yaml

# 错误 — 假定特定工作目录
Load task from /home/user/project/_bmad/memory/hw-shared/tasks.yaml
```

`{project-root}` token 由每个技能的"On Activation"步骤解析（Claude Code: 工作目录；Codex: 仓库根目录；OpenCode: 项目配置路径）。

### 工具调用：平台中立的描述模式

不同平台有不同工具名。技能必须描述意图，而非工具名：

```
# 正确 — 描述做什么
Delegate the review to the security reviewer agent

# 错误 — Claude Code 特有工具名
Use the Agent tool with subagent_type=hw-reviewer-security
```

需要 Agent 间委托时，用逻辑名称（`hw-reviewer-security`）描述目标 Agent。各平台运行时解析为本地委托机制。

### Bash 块：自包含

每个 bash 代码块在独立 shell 中运行。变量不在块间持久化：

- 用自然语言表达逻辑和状态，而非 shell 变量
- 保持 bash 块自包含
- 将条件表达为英文，而非嵌套的 `if/elif/else`
- 禁止平台特有的 CLI 标志

### 字符编码

- **标识符**（文件名、Agent 名、命令名）：仅 ASCII。转换器和正则表达式依赖此规则。
- **Markdown 表格：** 管道分隔（`| col | col |`），禁止制表符画线字符。
- **正文：** Unicode 可用。代码块和终端示例中优先使用 ASCII 箭头（`->`、`<-`）。

### 并行执行：描述意图

```
# 正确
Run the three code reviews in parallel:
- Security review
- Logic review
- Performance review

# 错误 — 平台特有
Use Task tool with run_in_background for each review
```

---

## 平台特性矩阵

| Feature | Claude Code | Codex | OpenCode | 可移植方案 |
|---------|-------------|-------|----------|-----------|
| Skill 目录 | `skills/<name>/` | `.agents/skills/<name>/` | `.opencode/skills/<name>/` | 从 SKILL.md 使用相对路径 |
| Agent 委托 | `Agent` tool | `$skill-name` | agent config | 描述意图，非工具名 |
| 后台任务 | `run_in_background` | N/A | N/A | 描述并行性，非机制 |
| 权限 | `.claude/settings.json` | `config.toml` | `opencode.json` | 文档化所需权限；各平台独立配置 |
| Hooks | `hooks/hooks.json` | N/A | plugin events | 避免技能中依赖 hook 逻辑 |
| MCP 服务器 | `.mcp.json` | `[mcp_servers]` in TOML | `mcp` in JSON | 每平台分别配置 MCP；技能仅按名称引用 MCP 工具 |
| 指令文件 | `CLAUDE.md` | `AGENTS.md` | instructions in JSON | 维护 `AGENTS.md` 为规范文件；`CLAUDE.md` 委托给它 |
| Frontmatter 扩展 | `allowed-tools` | `argument-hint` | N/A | 保持 frontmatter 仅含 `name` + `description` |

---

## 技能设计模式

每个技能（`skills/hw-*/SKILL.md`）遵循一致模板：

1. **YAML frontmatter** — name, description with trigger keywords
2. **Overview** — agent purpose and mission statement
3. **Identity** — agent persona and mindset
4. **Communication Style** — how the agent communicates
5. **Principles** — non-negotiable behavioral rules
6. **On Activation** — initialization steps when the skill is invoked
7. **Capabilities table** — routes to reference files for detailed instructions
8. **Memory/State files** — which shared files the agent reads/writes
9. **Output** — where results are written

创建或修改技能时：
- `references/` 目录包含运行时加载的详细能力指令
- 保持 SKILL.md 作为高层 Agent 定义；将过程细节放在 `references/` 中
- 语言模式放在 `references/`（如 `references/patterns-python.md`）
- 业务领域配置放在 `_bmad/config.yaml` 中

---

## 下一步

| 我想… | 看这里 |
|-------|--------|
| 查看完整 Agent 目录 | [agents.md →](agents.md) |
| 查看配置项详情 | [configuration.md →](configuration.md) |
| 在 Codex 上安装 | [INSTALL-codex.md →](INSTALL-codex.md) |
| 在 OpenCode 上安装 | [INSTALL-opencode.md →](INSTALL-opencode.md) |
