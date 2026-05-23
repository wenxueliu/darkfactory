# 知识库 (Knowledge Base)

> **初次接触？** 先看 [README.md](../README.md) 和 [quickstart.md](quickstart.md)。本文是知识库架构的完整说明，覆盖三级分层、两阶段初始化、更新策略和生命周期。

> 黑灯工厂的知识管理架构：如何初始化、如何分层、何时更新、如何维护。

---

## 设计理念

知识库是黑灯工厂的**机构记忆**——每次开发自动沉淀可复用的知识，后续开发自动引用。核心理念：

- **知识是投资** —— 花时间记录，后续节省更多时间
- **准确优先于数量** —— 一条准确的记录胜过十条模糊的
- **可追溯** —— 每条知识都知道何时、为何、如何获得
- **自动优先** —— 能从代码检测的信息不应由人工手写

---

## 三级分层架构

```
_bmad/memory/hw-shared/knowledge-base/
├── index.md                    # 全局知识索引
│
├── _enterprise/                # 第一级：企业级 —— 跨所有服务
│   ├── decisions/              #   架构决策记录 (ADR)
│   ├── patterns/               #   跨服务可复用模式
│   ├── lessons/                #   全局经验教训
│   └── contracts/              #   跨服务 API 契约
│
├── domains/                    # 第二级：业务领域级 —— 按领域组织
│   └── {domain}/               #   例：user-domain/、order-domain/
│       ├── decisions/          #     领域级架构决策
│       ├── patterns/           #     领域内复用模式
│       └── lessons/            #     领域经验教训
│
└── services/                   # 第三级：服务级 —— 每个服务独立
    └── {service-id}/           #   例：user-service/、order-service/
        ├── overview.md         #     服务概览（自动生成）
        ├── api-endpoints.md    #     API 端点列表（自动生成）
        ├── db-schema.md        #     数据库 Schema（自动生成）
        ├── decisions/          #     服务级架构决策
        ├── patterns/           #     服务内复用模式
        └── lessons/            #     服务级经验教训
```

### 各级职责

| 层级 | 存放内容 | 查询时机 |
|------|---------|---------|
| `_enterprise/` | 影响多个服务的全局决策、跨服务契约、通用的可复用模式 | 任何设计开始前必查 |
| `domains/{domain}/` | 特定业务领域的决策和模式（例：用户领域的认证策略） | 涉及该领域的服务设计时查询 |
| `services/{service-id}/` | 单个服务的概要、API、Schema、服务内决策 | 修改该服务时查询 |

### 查询优先级

设计阶段查询知识库时，按以下顺序：

1. `_enterprise/` — 先看有没有全局约束或已有决策
2. `domains/{domain}/` — 再看领域级知识
3. `services/{service-id}/` — 最后看服务级细节

如果全局 ADR 和服务级决策冲突，全局 ADR 优先（需要显式记录为何偏离）。

---

## 初始化时机：两阶段

KB 目录结构的建立分两阶段，各自在不同时机触发：

### 第一阶段：手动创建骨架（项目搭建时，一次性）

在项目工作空间创建 `_bmad/` 配置的同时，创建空的 KB 目录骨架：

```bash
mkdir -p _bmad/memory/hw-shared/knowledge-base/{patterns,decisions,lessons,api-contracts}
mkdir -p _bmad/memory/hw-shared/reviews
mkdir -p _bmad/memory/hw-controller
```

此阶段产物：**空的目录结构**，没有任何知识内容。这一步由人在项目初始化时手动完成。

### 第二阶段：自动生成内容（首次 `/hw-controller 初始化` 时）

当运行 `/hw-controller 初始化：发现所有服务并建立注册表` 时，hw-knowledge-agent 自动执行服务发现：

**检测内容：**

| 检测维度 | 检测方式 | 生成产物 |
|---------|---------|---------|
| 技术栈 | 检测 `build.gradle`/`package.json`/`go.mod`/`pyproject.toml` 等 | `service-registry.yaml` |
| API 端点 | 扫描 Controller/Route/Handler 文件中的路由注解 | `services/{id}/api-endpoints.md` |
| 数据库 Schema | 扫描 Flyway migration / Prisma schema / SQLAlchemy model / GORM struct | `services/{id}/db-schema.md` |
| 基础设施依赖 | 检测 redis/kafka/postgresql 等驱动依赖 | `service-registry.yaml` |
| 跨服务依赖 | 扫描代码中对外部服务 URL 的引用 | `service-registry.yaml` 依赖图 |
| 服务概览 | 综合以上信息 + README 摘要 | `services/{id}/overview.md` |

此阶段产物：**每个服务的自动生成知识文件 + 服务注册表**。

> 服务信息从代码中自动学习，而非人工配置。`service-registry.yaml` 是生成的产物，不是手写的输入。

### 两阶段对比

| | 第一阶段 | 第二阶段 |
|------|---------|---------|
| 触发 | 项目搭建时手动执行 | `/hw-controller 初始化` |
| 执行者 | 人 | hw-knowledge-agent（自动） |
| 产物 | 空目录骨架 | 服务级 KB 文件 + service-registry.yaml |
| 频率 | 一次性 | 首次初始化 + 后续持续更新 |
| 前提条件 | 无 | services/ 下各服务已 clone、依赖已安装、基线测试通过 |

---

## 自动生成 vs 人工维护

| 内容 | 来源 | 维护方式 |
|------|------|---------|
| `services/{id}/overview.md` | 自动检测 + README 提取 | 自动更新。职责描述如无法提取则标记 `NEEDS_MANUAL` |
| `services/{id}/api-endpoints.md` | 自动扫描 Controller/Route | 任务完成后增量更新 |
| `services/{id}/db-schema.md` | 自动扫描 Migration/Model | 任务完成后增量更新 |
| `service-registry.yaml` | 自动扫描所有服务 | 全量或增量更新 |
| `_enterprise/contracts/` | 设计阶段自动生成 + 人工审核 | hw-controller 写入，人审核确认 |
| `_enterprise/decisions/` (ADR) | 设计阶段 hw-controller 自动写入 | 自动写入，重大决策需人工确认 |
| `_enterprise/patterns/` | hw-knowledge-agent 自动沉淀 | 自动提取，可人工补充 |
| `_enterprise/lessons/` | 开发完成后自动沉淀 | 自动写入，包含成功和失败经验 |
| `domains/{domain}/` | 涉及多服务的领域知识 | 自动分类 + 人工调整领域归属 |
| `services/{id}/decisions/` | 服务级设计决策 | 自动写入，服务负责人可补充 |

**基本原则：能从代码检测的，不手写。需要判断和决策的，Agent 自动生成初稿，人审核确认。**

---

## 更新策略

KB 不是一次生成就完事的——它随项目持续演进。三种更新触发方式：

### 1. 增量更新（任务级）

每个 worktree 任务完成后，自动触发增量更新：

- 如果任务修改了 Controller/Route 文件 → 重新扫描该服务的 API 端点
- 如果任务修改了 Migration/Model 文件 → 重新扫描该服务的数据库 Schema
- 如果任务修改了配置文件 → 重新检测基础设施依赖和跨服务依赖

**触发时机：** worktree-controller 报告 `DONE` → hw-controller 验证通过 → hw-knowledge-agent 增量更新

### 2. 全量更新（需求级）

每个需求的所有任务完成后，全量重新发现一次：

- 重新扫描所有服务的技术栈、API、Schema、依赖
- 重建 `service-registry.yaml`
- 重建所有 `services/{id}/*.md`
- 与上一版本对比，标记新增、修改、删除

**触发时机：** 需求进入 `merge → test` 阶段时

### 3. 手动触发

```
/hw-controller 重新发现服务           # 全量重新发现
/hw-controller 重新发现 {service-id}  # 仅重新发现指定服务
```

**使用场景：** 人工在服务仓库中做了较大改动、首次全量发现后新增了服务、发现检测结果有误需要重跑。

### 更新覆盖规则

| 字段 | 全量更新 | 增量更新 | 手动编辑 |
|------|---------|---------|---------|
| 自动检测字段（API、Schema、端口等） | 覆盖 | 覆盖 | **会被覆盖** |
| `NEEDS_MANUAL` 标记字段（职责描述等） | 保留 | 保留 | **手动填充后标记移除** |
| 知识沉淀（patterns、lessons、ADR） | 追加，不覆盖 | 追加，不覆盖 | **不会被覆盖** |

> 如果你在 `overview.md` 中手写了职责描述，请将 `NEEDS_MANUAL` 标记移除——后续自动更新会保留它。如果保留标记，下次全量更新可能重置为 `NEEDS_MANUAL`。

---

## KB 生命周期

知识条目具有生命周期状态，防止 KB 无限膨胀和过时：

### 条目状态

| 状态 | 含义 | 行为 |
|------|------|------|
| `active` | 当前有效，最新 | 正常使用 |
| `deprecated` | 已被新方案替代 | 查询时显示但标记"已过时"，指向替代条目 |
| `superseded` | 被指定条目取代 | 通过 `supersedes` 字段指向新条目 |
| `expired` | 超过有效期 | 仅存档显示，查询时过滤 |

### 置信度衰减

知识置信度随时间自动衰减（不同来源衰减速度不同）：

| 来源类型 | 衰减速度 | 说明 |
|---------|---------|------|
| `observed` | 每 60 天 -1 置信度 | 从代码/日志中观察到的事实，衰减最慢 |
| `inferred` | 每 30 天 -1 置信度 | 从模式中推断的知识，衰减较快 |
| `cross-model` | 每 30 天 -1 置信度 | 跨模型验证的知识，衰减较快 |
| `user-stated` | 不衰减 | 人类陈述的知识，视为稳定 |

### 过期阈值

| 阈值 | 条件 | 行为 |
|------|------|------|
| Stale（陈旧） | 超过 90 天 + effective confidence ≤ 5 | 触发审查提醒，标记但保留 |
| Expired（过期） | 超过 365 天 | 自动标记为 `expired`，查询时过滤 |

> 配置项：`_bmad/config.yaml` → `hw.kb.freshness.*`

---

## 维护命令

```bash
# KB 健康检查（增长、陈旧、缺口）
python scripts/kb-health.py

# 陈旧条目检测
python scripts/kb-index.py --check-staleness

# 置信度衰减计算
python scripts/kb-freshness.py

# 批量压缩 KB 条目（减少 token 消耗）
python scripts/kb-distill.py batch

# 重建全局索引
python scripts/kb-index.py --rebuild

# 预览服务发现（不写入文件）
python scripts/kb-service-discovery.py --probe --verbose

# 完整服务发现
python scripts/kb-service-discovery.py --verbose
```

建议在每个需求完成后运行一次 `kb-health.py`，在每周例行检查中运行 `kb-index.py --check-staleness`。

---

## 与开发流程的关系

```
ideation → design → decomposition → execution → merge → test → delivery
              ↑            ↑             ↑          ↑       ↑
              │            │             │          │       │
          查 KB      写 ADR/契约   增量更新KB   追加lessons  全量更新KB
```

| 阶段 | KB 操作 |
|------|---------|
| **ideation** | 查询 KB：有没有类似需求的经验和决策？ |
| **design** | 查询 KB（_enterprise → domains → services）→ 写入 ADR 和契约 |
| **decomposition** | 无直接操作（依赖 task-decomposition 读取 tasks.yaml） |
| **execution** | 每个任务完成后增量更新 API/Schema 信息 |
| **merge** | 追加 lessons learned（成功和失败经验） |
| **test** | 更新 API 契约（如有变更） |
| **delivery** | 全量更新 KB，检查陈旧条目，运行 `kb-health.py` |

---

## 常见问题

### Q: KB 在工作空间根目录还是服务仓库里？

在工作空间根目录的 `_bmad/memory/hw-shared/knowledge-base/`。每个 `services/{id}/` 保持独立的 git 仓库，知识全部沉淀在工作空间层。

### Q: 新增一个服务后需要重新初始化吗？

不需要全量重新初始化。运行 `/hw-controller 重新发现 {new-service-id}` 即可增量添加，新服务的 KB 文件会自动生成。

### Q: 手动编辑的 KB 内容会被自动更新覆盖吗？

- 自动检测字段（API 端点、Schema、端口等）会被覆盖——这些应该从代码派生
- `NEEDS_MANUAL` 标记的字段不会被覆盖——填充后请移除标记
- 知识沉淀（patterns、lessons、ADR、contracts）只追加不覆盖

### Q: 多个服务有相似的 pattern 应该放哪里？

如果 pattern 只在一个服务内使用 → `services/{id}/patterns/`。如果被 2+ 个服务使用 → 提取到 `_enterprise/patterns/`。

### Q: 什么时候应该清理 KB？

每周运行 `kb-index.py --check-staleness` 检查陈旧条目，每个 delivery 阶段运行 `kb-health.py`。过期的条目自动标记并在查询时过滤——不需要手动删除，但需要定期审查。

---

## 下一步

| 我想… | 看这里 |
|-------|--------|
| 从零开始第一次使用 | [quickstart.md →](quickstart.md) |
| 了解核心设计理念 | [concepts.md →](concepts.md) |
| 查看全部 Agent 角色 | [agents.md →](agents.md) |
| 查看系统架构和记忆架构 | [architecture.md →](architecture.md) |
| 了解配置项和 KB 生命周期 | [configuration.md →](configuration.md) |
| 查看 KB 管理脚本 | `scripts/` 目录下 `kb-*.py` 文件 |
