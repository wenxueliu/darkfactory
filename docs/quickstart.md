# 黑灯工厂 快速开始

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

在你的项目根目录下创建 `_bmad/` 目录，新增两个文件：

```bash
mkdir -p _bmad/memory/hw-shared
mkdir -p _bmad/memory/hw-controller
```

**`_bmad/config.yaml`**（根据上面的回答调整）：

```yaml
hw:
  architecture: "monolith"              # 单体服务
  business_domain: "general"            # general | fintech | ecommerce | internal-tools
  min_iteration_before_human: 3         # AI 自主迭代几次后升级到人工
  enabled_reviewers: "logic"            # 起步保守，后续加 security,performance
  knowledge_base_auto_update: true
  merge_strategy: "merge"
```

**`_bmad/config.user.yaml`**：

```yaml
communication_language: Chinese
user_name: 你的名字
```

> 完整的配置项说明见 `CLAUDE.md` 中的 Configuration 章节。

### 第三步：复制技能目录

将黑灯工厂的 `skills/` 目录复制到你的项目根目录下。**最少需要 4 个技能：**

| 技能 | 作用 |
|------|------|
| `hw-controller` | 总控：需求分析 → 设计 → 任务拆分 → 编排执行 |
| `hw-tdd-agent` | TDD 执行：RED → GREEN → REFACTOR |
| `hw-reviewer-logic` | 逻辑审查：发现正确性问题和边界情况 |
| `hw-worktree-controller` | 任务执行：在隔离 worktree 中完成单个任务 |

可选但推荐：

| 技能 | 作用 |
|------|------|
| `hw-reviewer-security` | 安全审查 |
| `hw-reviewer-performance` | 性能审查 |
| `hw-setup` | 环境初始化 |

### 第四步：更新 .gitignore

```bash
echo ".worktree/" >> .gitignore
echo "_bmad-output/" >> .gitignore
```

### 第五步：试运行

在 Claude Code 中输入：

```
/hw-controller 我想给项目加一个健康检查端点
```

你会看到 hw-controller 启动，依次完成：
1. 需求澄清（问你几个问题）
2. 设计输出（生成设计文档）
3. 任务拆分（生成 tasks.yaml）
4. 执行任务（启动 worktree-controller → tdd-agent → reviewer）
5. 质量门禁通过后合并

> 如果只是体验流程，可以用 `/hw-controller 体验模式：我想加一个 /health 端点` 快速走一遍。

---

## 场景 B：新项目启动

### 第一步：初始化项目骨架

```bash
mkdir my-project && cd my-project
git init

# 创建基础目录
mkdir -p src tests
mkdir -p _bmad/memory/hw-shared
mkdir -p _bmad/memory/hw-controller
mkdir -p skills
```

### 第二步：配置项目

**`_bmad/config.yaml`**：

```yaml
hw:
  architecture: "monolith"
  business_domain: "general"
  min_iteration_before_human: 3
  enabled_reviewers: "security,logic,performance"
  knowledge_base_auto_update: true
  merge_strategy: "merge"
```

**`_bmad/config.user.yaml`**：

```yaml
communication_language: Chinese
user_name: 你的名字
```

### 第三步：复制技能

将黑灯工厂 `skills/` 下的所有 `hw-*` 技能目录复制到你的 `skills/` 下。

### 第四步：让 hw-controller 带你走

```
/hw-controller 我要启动一个新项目，技术栈是 {Python FastAPI / Go Gin / Java Spring Boot / ...}，
核心功能是 {一句话描述}
```

hw-controller 会引导你完成：
1. **需求规格** — 帮你把一句话需求展开为完整的需求文档
2. **设计文档** — 生成架构设计、API 设计、测试设计
3. **任务拆分** — 将设计拆分为可并行执行的 TDD 任务
4. **开发执行** — 按 TDD 铁律（先写测试，再写代码）逐步实现
5. **审查通过** — 逻辑、安全、性能三层审查
6. **交付就绪** — 代码合并、集成测试、发布清单

### 第五步：沉淀知识

第一次开发完成后，检查 `_bmad/memory/hw-shared/knowledge-base/`：
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
mkdir hw-workspace && cd hw-workspace
git init  # 这个仓只放 _bmad + skills，不放服务代码
```

### 第二步：克隆所有服务

```bash
mkdir -p services
git clone git@github.com:org/user-service.git services/user-service
git clone git@github.com:org/order-service.git services/order-service
git clone git@github.com:org/web-frontend.git services/web-frontend
```

> 关键点：每个 `services/{id}/` 保持独立的 `.git/`、独立的 remote、独立的 CI/CD。co-location 只是让它们在同一工作目录下协作，不改变各自的 git 独立性。

### 第三步：配置微服务模式

**`_bmad/config.yaml`**：

```yaml
hw:
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

### 第四步：服务发现（自动）

```
/hw-controller 初始化：发现所有服务并建立注册表
```

hw-controller 调用 hw-knowledge-agent 自动扫描 `services/` 下的每个仓库，生成 `_bmad/memory/hw-shared/service-registry.yaml`。这个过程会检测每个服务的语言、框架、API 端点、数据库 schema。

你不需要手写任何服务元数据。

### 第五步：开始一个跨服务需求

```
/hw-controller 用户下单时需要校验信用分，涉及 user-service（新增信用分接口）、
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
/hw-controller 体验模式：在 reference/ 目录下找一个最简单的例子跑一遍
```

hw-controller 会跳过配置检查，用默认参数跑一个最短路径：
1. 生成一个示例需求
2. 走过需求 → 设计 → 拆分 → 执行 → 合并的完整流程
3. 你会看到各 Agent 如何协作、质量门禁如何运作、worktree 如何管理

预计 5-10 分钟走完。

---

## 第一次使用后

恭喜！你已经用过一次黑灯工厂了。接下来几个方向可以选择：

**我想更深入理解某个 Agent：**
- `skills/hw-controller/SKILL.md` — 总控的完整能力表
- `skills/hw-tdd-agent/SKILL.md` — TDD 执行的详细流程
- `skills/hw-reviewer-logic/SKILL.md` — 逻辑审查的检查维度

**我想调整配置以适应我的团队：**
- `CLAUDE.md` 中的 Configuration 章节 — 所有可配置项及默认值
- `_bmad/config.yaml` — 调整 review 严格度、业务领域、人力介入频率

**我想扩展新的业务领域模板：**
- `skills/hw-controller/references/template-router.md` — 如何新增一个业务领域模板
- `skills/hw-controller/references/requirements-spec-template.md` — 通用模板结构

**我遇到了问题：**
- 检查 `_bmad/memory/hw-shared/human-interventions.md` — 是否有阻塞升级
- 检查 `_bmad/memory/hw-controller/global-state.yaml` — 当前阶段和进度
- 直接对 hw-controller 描述你的问题，它会自主诊断

---

## 速查表

### 常用指令

| 指令 | 作用 |
|------|------|
| `/hw-controller {需求描述}` | 启动一个需求 |
| `/hw-controller 状态` | 查看当前开发进度 |
| `/hw-controller 继续` | 从上次中断处继续 |
| `/hw-controller 升级` | 遇到阻塞，升级到人工决策 |

### 目录速查

| 目录 | 内容 | 谁维护 |
|------|------|--------|
| `_bmad/config.yaml` | 项目配置 | 你（人工） |
| `_bmad/memory/hw-shared/` | 需求、设计、任务、审查 | hw-controller（自动） |
| `_bmad/memory/hw-controller/` | 编排状态、worktree 注册表 | hw-controller（自动） |
| `.worktree/` | 隔离开发环境 | 自动创建/销毁 |
| `skills/` | Agent 技能定义 | 随黑灯工厂更新 |
| `contracts/` | 跨服务 API 契约 | hw-controller + 人工审核 |
| `_bmad/memory/hw-shared/knowledge-base/` | 积累的架构知识 | hw-controller（自动沉淀） |

---

**下一步？** 选好你的场景，打开 Claude Code，输入 `/hw-controller` 开始你的第一次人机协同开发。
