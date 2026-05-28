# 黑灯工厂 快速开始

> **初次接触？** 先看 [README.md](../README.md) 了解项目概览和安装。本文是四个接入场景的完整教程。

> 从零到第一次交付，跟着这段对话走。

---

## 先聊聊你的情况

黑灯工厂是一套**人机协同的软件生成系统**——你负责决策，AI Agent 负责执行。但在开始之前，我需要了解你站在哪里。

**请对号入座：**

| 你的情况 | 跳转到 |
|----------|--------|
| 我有一个已有项目，想给它加上黑灯工厂 | [场景 A：已有项目接入](#场景-a已有项目接入) |
| 我要从零开始一个新项目 | [场景 B：新项目启动](#场景-b新项目启动) |
| 我有多个微服务，想统一编排 | [场景 C：微服务多仓接入](#场景-c微服务多仓接入) |
| 我只是想先看看它长什么样 | [场景 D：5 分钟体验](#场景-d5-分钟体验) |

---

## 场景 A：已有项目接入

### 第一步：了解你的项目

在开始之前，先回答三个问题：

1. **你的项目是什么语言？** Python / Java / Go / TypeScript / ...（`*` 表示自动检测）
2. **你的项目是单体还是微服务？** 单体意味着一个 git 仓库对应一个可部署的服务
3. **你对质量门禁的严格度要求？**
   - 金融/合规场景 → 全开（security + logic + performance），人工介入频繁
   - 内部工具 → 仅 logic，减少打断
   - 一般业务 → 默认（security + logic + performance），3 次迭代后人工介入

### 第二步：创建配置

在你的项目根目录下创建 `_context/` 目录，新增两个文件：

```bash
mkdir -p _context/memory/sw-shared
mkdir -p _context/memory/sw-controller
```

**`_context/config.yaml`**（根据上面的回答调整）：

```yaml
sw:
  architecture: "monolith"              # 单体服务
  business_domain: "general"            # general | fintech | ecommerce | internal-tools
  min_iteration_before_human: 3         # AI 自主迭代几次后升级到人工
  enabled_reviewers: "logic"            # 起步保守，后续加 security,performance
  knowledge_base_auto_update: true
  merge_strategy: "merge"
```

**`_context/config.user.yaml`**：

```yaml
communication_language: Chinese
user_name: 你的名字
```

> 完整的配置项说明见 `CLAUDE.md` 中的 Configuration 章节。

### 第三步：安装技能

使用 `install.py` 一键安装技能到你的项目目录：

```bash
# 在你的项目目录下执行
python /path/to/harness/services/multiagents/install.py

# 只安装 4 个核心技能
python /path/to/harness/services/multiagents/install.py --minimal

# 安装到指定路径
python /path/to/harness/services/multiagents/install.py --target /path/to/your/project
```

4 个核心技能：

| 技能 | 作用 |
|------|------|
| `sw-controller` | 总控：需求分析 → 设计 → 任务拆分 → 编排执行 |
| `sw-tdd-agent` | TDD 执行：RED → GREEN → REFACTOR |
| `sw-reviewer-logic` | 逻辑审查：发现正确性问题和边界情况 |
| `sw-worktree-controller` | 任务执行：在隔离 worktree 中完成单个任务 |

安装完成后，你的项目下会出现 `skills/` 目录（Claude Code）或 `.agents/skills/` 目录（Codex）。

**多平台：** `--claude`（默认）安装到 `skills/`，`--codex` 安装到 `.agents/skills/`，可同时指定：

```bash
python /path/to/harness/services/multiagents/install.py --claude --codex
```

### 第四步：更新 .gitignore

```bash
echo ".worktree/" >> .gitignore
echo "_context-output/" >> .gitignore
```

### 第五步：试运行

在 Claude Code 中输入：

```
/sw-controller 我想给项目加一个健康检查端点
```

你会看到 sw-controller 启动，依次完成：
1. 需求澄清（问你几个问题）
2. 设计输出（生成设计文档）
3. 任务拆分（生成 tasks.yaml）
4. 执行任务（启动 worktree-controller → tdd-agent → reviewer）
5. 质量门禁通过后合并

> 如果只是体验流程，可以用 `/sw-controller 体验模式：我想加一个 /health 端点` 快速走一遍。

---

## 场景 B：新项目启动

### 第一步：初始化项目骨架

```bash
mkdir my-project && cd my-project
git init

# 创建基础目录
mkdir -p src tests
mkdir -p _context/memory/sw-shared
mkdir -p _context/memory/sw-controller
mkdir -p skills
```

### 第二步：配置项目

**`_context/config.yaml`**：

```yaml
sw:
  architecture: "monolith"
  business_domain: "general"
  min_iteration_before_human: 3
  enabled_reviewers: "security,logic,performance"
  knowledge_base_auto_update: true
  merge_strategy: "merge"
```

**`_context/config.user.yaml`**：

```yaml
communication_language: Chinese
user_name: 你的名字
```

### 第三步：安装技能

```bash
# 从黑灯工厂仓库安装全部技能
python /path/to/harness/services/multiagents/install.py --target .
```

### 第四步：让 sw-controller 带你走

```
/sw-controller 我要启动一个新项目，技术栈是 {Python FastAPI / Go Gin / Java Spring Boot / ...}，
核心功能是 {一句话描述}
```

sw-controller 会引导你完成：
1. **需求规格** — 帮你把一句话需求展开为完整的需求文档
2. **设计文档** — 生成架构设计、API 设计、测试设计
3. **任务拆分** — 将设计拆分为可并行执行的 TDD 任务
4. **开发执行** — 按 TDD 铁律（先写测试，再写代码）逐步实现
5. **审查通过** — 逻辑、安全、性能三层审查
6. **交付就绪** — 代码合并、集成测试、发布清单

### 第五步：沉淀知识

第一次开发完成后，检查 `_context/memory/sw-shared/knowledge-base/`：
- `patterns/` — 本次发现的可复用模式
- `decisions/ADR-0001-*.md` — 架构决策记录
- `lessons/` — 经验教训

这些沉淀会在后续开发中被自动引用。

---

## 场景 C：微服务多仓接入

### 前置条件确认

你有多个独立的微服务仓库。比如：`user-service`、`order-service`、`web-frontend`。

### 第一步：创建工作目录

```bash
mkdir sw-workspace && cd sw-workspace
git init  # 这个仓只放 _context + skills，不放服务代码
```

### 第二步：克隆所有服务

```bash
mkdir -p services
git clone git@github.com:org/user-service.git services/user-service
git clone git@github.com:org/order-service.git services/order-service
git clone git@github.com:org/web-frontend.git services/web-frontend
```

> 关键点：每个 `services/{id}/` 保持独立的 `.git/`、独立的 remote、独立的 CI/CD。co-location 只是让它们在同一工作目录下协作，不改变各自的 git 独立性。

### 第三步：创建配置和知识库骨架

创建 `_context/` 目录结构——这是**手动一次性**操作，建立空的记忆目录骨架：

```bash
mkdir -p _context/memory/sw-shared/knowledge-base/{patterns,decisions,lessons,api-contracts}
mkdir -p _context/memory/sw-shared/reviews
mkdir -p _context/memory/sw-controller
```

**`_context/config.yaml`**：

```yaml
sw:
  architecture: "microservices"

  microservices:
    max_parallel_services: 4
    integration_test_mode: "docker-compose"
    contract_first: true

  business_domain: "general"
  min_iteration_before_human: 3
  enabled_reviewers: "security,logic,performance"
  merge_strategy: "merge"
```

**`_context/config.user.yaml`**：

```yaml
communication_language: Chinese
user_name: 你的名字
```

当前阶段 KB 目录还是**空的**——只有骨架，没有任何服务知识内容。

### 第四步：安装技能

```bash
python /path/to/harness/services/multiagents/install.py --target .
```

### 第五步：服务发现——自动生成 KB 内容

```
/sw-controller 初始化：发现所有服务并建立注册表
```

这是 KB 初始化的**第二阶段（自动）**。流程：`sw-controller` → `sw-setup` → `sw-knowledge-agent` 的服务发现能力：

**自动扫描和检测：**
- 扫描 `services/` 下所有 git 仓库
- 检测每个服务的技术栈（语言/框架/构建工具/端口）
- 提取 API 端点、数据库 schema、基础设施依赖
- 分析跨服务依赖关系

**自动生成的文件：**

| 产物 | 路径 |
|------|------|
| 服务注册表 | `_context/memory/sw-shared/service-registry.yaml` |
| 服务概览 | `_context/memory/sw-shared/knowledge-base/services/{id}/overview.md` |
| API 端点文档 | `_context/memory/sw-shared/knowledge-base/services/{id}/api-endpoints.md` |
| 数据库 Schema | `_context/memory/sw-shared/knowledge-base/services/{id}/db-schema.md` |

你不需要手写任何服务元数据——服务信息从代码中自动检测，而非人工配置。

> KB 的三级分层结构、自动/手动内容划分、后续更新策略详见 [`docs/knowledge-base.md`](knowledge-base.md)。

### 第六步：开始一个跨服务需求

```
/sw-controller 用户下单时需要校验信用分，涉及 user-service（新增信用分接口）、
order-service（调用信用分校验）、web-frontend（下单页展示信用额度）
```

微服务模式下的关键差异：

| 阶段 | 与单体的区别 |
|------|------------|
| 需求 | 追加「服务影响分析」表，标注每个服务的变更类型 |
| 设计 | 3 个 Agent 依次执行：特性设计（跨服务）→ 服务设计（每服务并行）→ E2E 设计 |
| 拆分 | 按服务分组，跨服务依赖标记为 CONTRACT 类型（可并行 + mock） |
| 执行 | 不同服务的 worktree 独立创建在 `.worktree/{service-id}/` 下 |
| 质量 | 新增契约测试层（API 测试通过后、E2E 前） |
| 交付 | 多服务协调发布序列，按依赖关系分 wave 上线 |

---

## 场景 D：5 分钟体验

不配置任何项目，直接在黑灯工厂仓库内体验：

```
/sw-controller 体验模式：在 reference/ 目录下找一个最简单的例子跑一遍
```

sw-controller 会跳过配置检查，用默认参数跑一个最短路径：
1. 生成一个示例需求
2. 走过需求 → 设计 → 拆分 → 执行 → 合并的完整流程
3. 你会看到各 Agent 如何协作、质量门禁如何运作、worktree 如何管理

预计 5-10 分钟走完。

---

## 第一次使用后

恭喜！你已经用过一次黑灯工厂了。接下来几个方向可以选择：

**我想更深入理解某个 Agent：**
- `skills/sw-controller/SKILL.md` — 总控的完整能力表
- `skills/sw-tdd-agent/SKILL.md` — TDD 执行的详细流程
- `skills/sw-reviewer-logic/SKILL.md` — 逻辑审查的检查维度

**我想了解知识库的架构和维护：**
- [`docs/knowledge-base.md`](knowledge-base.md) — KB 的三级分层、初始化时机、更新策略、生命周期

**我想调整配置以适应我的团队：**
- `CLAUDE.md` 中的 Configuration 章节 — 所有可配置项及默认值
- `_context/config.yaml` — 调整 review 严格度、业务领域、人力介入频率

**我想扩展新的业务领域模板：**
- `skills/sw-controller/references/template-router.md` — 如何新增一个业务领域模板
- `skills/sw-controller/references/requirements-spec-template.md` — 通用模板结构

**我遇到了问题：**
- 检查 `_context/memory/sw-shared/human-interventions.md` — 是否有阻塞升级
- 检查 `_context/memory/sw-controller/global-state.yaml` — 当前阶段和进度
- 直接对 sw-controller 描述你的问题，它会自主诊断

---

## 速查表

### 常用指令

| 指令 | 作用 |
|------|------|
| `/sw-controller {需求描述}` | 启动一个需求 |
| `/sw-controller 状态` | 查看当前开发进度 |
| `/sw-controller 继续` | 从上次中断处继续 |
| `/sw-controller 升级` | 遇到阻塞，升级到人工决策 |

### 目录速查

| 目录 | 内容 | 谁维护 |
|------|------|--------|
| `_context/config.yaml` | 项目配置 | 你（人工） |
| `_context/memory/sw-shared/` | 需求、设计、任务、审查 | sw-controller（自动） |
| `_context/memory/sw-shared/knowledge-base/_enterprise/` | 全局 ADR、契约、跨服务模式 | sw-controller + 人工审核 |
| `_context/memory/sw-shared/knowledge-base/domains/` | 业务领域级知识 | sw-controller（自动分类） |
| `_context/memory/sw-shared/knowledge-base/services/` | 每个服务的 API、Schema、概览 | sw-knowledge-agent（自动生成） |
| `_context/memory/sw-controller/` | 编排状态、worktree 注册表 | sw-controller（自动） |
| `.worktree/` | 隔离开发环境 | 自动创建/销毁 |
| `skills/` | Agent 技能定义（Claude Code） | 随黑灯工厂更新 |
| `agents/` | Agent 独立 prompt 模板（Codex/OpenCode） | 随黑灯工厂更新 |
| `contracts/` | 跨服务 API 契约 | sw-controller + 人工审核 |
| `service-registry.yaml` | 服务注册表（技术栈/依赖图） | sw-knowledge-agent（自动生成） |

---

## 下一步

| 我想… | 看这里 |
|-------|--------|
| 了解核心设计理念 | [concepts.md →](concepts.md) |
| 浏览全部 Agent 目录 | [agents.md →](agents.md) |
| 深入了解知识库架构 | [knowledge-base.md →](knowledge-base.md) |
| 查看系统架构 | [architecture.md →](architecture.md) |
| 查看配置项详情 | [configuration.md →](configuration.md) |
| 了解总控 Agent 的能力 | `skills/sw-controller/SKILL.md` |
| 了解 TDD Agent 的执行流程 | `skills/sw-tdd-agent/SKILL.md` |
| 在 Codex 上使用黑灯工厂 | [INSTALL-codex.md →](INSTALL-codex.md) |
| 在 OpenCode 上使用黑灯工厂 | [INSTALL-opencode.md →](INSTALL-opencode.md) |
