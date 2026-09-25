# 多仓库工作区约定

本参考文档定义统一的项目工作区模型，不按仓库数量切换流程：

- `services/` 是源码仓库根目录。
- `services/` 下每个直接子目录都是一个独立代码仓库，也是一个服务单元。
- 只有一个代码仓库时，它就是单仓库工作区；这是多仓库模型的自然特例。
- `knowledge/` 独立存放项目知识，不放源码，也不放编排状态。
- `_context/` 只存配置、需求产物、任务状态、审查结果和机器生成的注册表。

## 初始化后的硬前置条件

`sw-setup` 只负责创建工作区骨架，不负责猜测或自动取得业务源码。初始化完成后，用户必须把要修改的代码仓放入：

```text
{project-root}/services/{repository-name}/
```

支持一个或多个独立 Git 仓库。仓库可以由用户复制、克隆或挂载，但每个直接子目录必须能被 Git 识别；未放入 `services/` 的源码不属于本次工作区。

```text
{project-root}/
├── services/                         # 用户放入的源码仓库
│   ├── application/                 # 一个仓库 = 一个服务单元
│   └── another-repository/           # 可选的更多仓库
├── knowledge/                        # 项目知识（可读、可积累）
│   ├── index.md
│   ├── _enterprise/
│   ├── domains/
│   └── services/{service-id}/
├── _context/
│   └── memory/sw-shared/
│       └── service-registry.yaml     # 机器可读的发现结果
└── .worktree/                        # 工作树，按仓库隔离
```

初始化完成后必须执行服务发现。若 `services/` 为空，流程应阻塞并提示用户放入源码仓，不得跳过服务边界。

## 服务发现与知识沉淀

服务注册表由 `sw-knowledge-agent` 从 `services/` 生成，不要求用户在配置中声明仓库类型或重复录入服务元数据：

```text
扫描 services/{repo}/
  → 检测语言、框架、构建/测试命令、API、数据和依赖
  → 写入 _context/memory/sw-shared/service-registry.yaml
  → 写入 knowledge/services/{service-id}/*.md
```

注册表是编排输入，知识文件是人类可读的长期资产。两者不能互相替代：

| 内容 | 唯一路径 | 维护方式 |
|------|----------|----------|
| 源码仓库 | `services/{service-id}/` | 用户放入；各仓库独立 Git 历史 |
| 服务元数据 | `_context/memory/sw-shared/service-registry.yaml` | 服务发现自动生成 |
| 企业级项目知识 | `knowledge/_enterprise/` | `sw-knowledge-agent` 与人工共同维护 |
| 领域级项目知识 | `knowledge/domains/` | 按领域维护 |
| 服务级项目知识 | `knowledge/services/{service-id}/` | 服务发现与人工共同维护 |
| 流程状态 | `_context/memory/sw-shared/` | 各流程 Skill 按契约写入 |

## 统一执行规则

### 需求与设计

所有需求先从服务注册表和需求影响分析中确定受影响的仓库。影响分析至少包含一行：

| 服务单元 | 仓库路径 | 影响类型 | 跨仓库依赖 | 风险 |
|----------|----------|----------|------------|------|
| `{service-id}` | `services/{service-id}` | API / UI / 数据 / 配置 | — 或明确列出 | 低/中/高 |

单仓库时仍然生成这张表，只是只有一行；如果没有跨仓库调用，交互和契约章节标记为 N/A，而不是删除整个设计约束。

Stage 1 产出全局特性设计，Stage 2 按受影响仓库产出服务详细设计，Stage 3 产出跨仓库或端到端验证设计。仓库数量决定是否并行，不决定是否加载某套模板。

### 任务与工作树

- 每个任务必须绑定 `service_id` 和 `service_path`。
- 默认一个仓库至少对应一个纵向任务；仓库内部只有在能独立验证时才继续拆分。
- 每个仓库使用自己的 Git worktree：`.worktree/{service-id}/{task-id}/`。
- 任务间依赖分为 `CODE`、`CONTRACT`、`API_READY`、`EVENT`、`DATA_MIGRATION` 等事实类型；不因仓库数量改变命名。
- 代码仓库之间的契约统一放在 `knowledge/_enterprise/contracts/`，或放在提供方仓库的既有契约路径，并在设计文档中明确归属。

示例：

```yaml
service_groups:
  - service_id: application
    repo_path: services/application
    tasks:
      - task_id: sw-001
        dependencies: []
  - service_id: another-repository
    repo_path: services/another-repository
    tasks:
      - task_id: sw-002
        dependencies:
          - task_id: sw-001
            type: CONTRACT
```

### 门禁与交付

每个仓库独立执行自己的构建、单元测试、API 测试和审查。只有当需求确实跨仓库时，才增加契约测试、集成环境编排或跨仓库 E2E；单仓库不需要伪造跨仓库依赖。

统一的门禁顺序为：

```text
需求定义 → 全局设计 → 仓库级设计 → 任务拆分
→ 各仓库 TDD/审查 → 必要的契约/集成测试 → 交付验收
```

## 禁止事项

- 不在 `_context/config.yaml` 中增加按仓库数量切换的架构模式分支。
- 不把源码放进 `knowledge/` 或 `_context/`。
- 不把项目知识写回 `_context/memory/sw-shared/` 下的旧知识目录。
- 不因为只有一个仓库就跳过服务发现、服务路径、需求影响分析和最小门禁。
- 不因为有多个仓库就假设一定存在跨仓库调用；是否存在依赖必须由代码、设计和契约证据证明。
