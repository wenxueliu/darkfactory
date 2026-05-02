# 任务拆分 (Task Decomposition)

参考: Compound Engineering task planning (DAG 依赖图 + 拓扑排序 + 临界路径分析) +
      BMAD sprint planning (任务粒度约束 + AC 追溯 + 并行度最大化)

## 核心理念

任务拆分是把 **per-service 设计文档** 翻译成**可并行执行的自包含工作单元**。拆分质量直接决定并行效率——拆太粗，一个 worktree 做太久；拆太细，通信开销吃掉并行收益。目标: **每个任务 1-3 小时的 AI 自主执行 + 无循环依赖 + 最大化并行度**。

**纵向拆分原则:** 每个任务是一个独立的纵向切片——自包含实现代码 + UT + API 测试。不允许把测试横切为独立任务（如 "API 测试任务"、"E2E 测试任务"），UT 和 API 测试必须在同一个 worktree 内随代码一起完成。E2E 测试跨服务编排，作为最后一个 wave 的独立任务。

**拆分是可选的:** 一个微服务可以只对应一个任务。拆分是优化手段，不是强制要求。只有当服务内的功能点可以独立验证时才拆分。

## 拆分流程 (6 步)

> **第 1 步新增了「服务识别」子流程**（原第 1 步只做工作单元提取）。在微服务模式下，必须先确定受影响的服务列表（4 级 fallback），才能提取工作单元。单体模式下跳过服务识别。

### 第 1 步: 确定受影响服务列表 + 提取工作单元 (Identify Services & Extract Work Units)

**输入 (按加载顺序):**

1. **服务注册表:** `_bmad/memory/hw-shared/service-registry.yaml` — 所有已注册服务的权威列表（auto-generated, 由 hw-knowledge-agent 维护）
2. **Stage 1 跨服务设计:** `designs/{id}-design.md` — 其中的「服务影响分析」表列出了本次需求实际涉及的服务（从 service-registry 中筛选，不可臆想）
3. **Stage 2 Per-service 设计:** `designs/{id}-service-{svc}-design.md` × N — 仅加载服务影响分析表中列出的服务，每个服务一份
4. **Stage 3 E2E 测试设计:** `designs/{id}-e2e-design.md` — 用于最后一个 wave 的 E2E 任务
5. **需求规格:** `requirements/{id}.md` — 验收条件来源
6. **ADR:** `knowledge-base/decisions/ADR-*.md` — 架构约束

**受影响服务必须从设计文档获取，禁止臆想:**

```
加载顺序（按优先级 fallback）:

  ┌─ 第 1 优先: service-registry.yaml 存在?
  │     ├─ YES → 读取所有已注册服务（权威事实源）
  │     │        读取 designs/{id}-design.md 的「服务影响分析」表
  │     │        交叉验证: 影响分析表中的服务必须在 registry 中存在
  │     │        验证通过 → 跳转到「加载 per-service 设计文档」
  │     │        验证失败 → 阻塞，升级人工
  │     │
  │     └─ NO  → 进入第 2 优先
  │
  ├─ 第 2 优先: 自动发现 (Auto-Discovery)
  │     扫描 {project-root}/services/ 目录
  │     对每个子目录:
  │       - 检查是否为 git 仓库 (git rev-parse --show-toplevel)
  │       - 获取 git remote URL (git remote get-url origin)
  │       - 检测语言/框架 (build.gradle → java, package.json → node, go.mod → go, ...)
  │       - 检测端口 (从 Dockerfile, application.yml, .env 提取)
  │       - 检测 API 端点 (扫描 *Controller.java, *.tsx routes, *.py routes, ...)
  │       - 检测数据所有权 (扫描 migration/entity/model 文件)
  │       - 记录服务路径: services/{subdir}/
  │     自动发现结果 → 输出临时服务清单:
  │       | 服务名 | 路径 | 仓库地址 | 语言 | 端口 | API 端点 | 拥有数据 |
  │     如果发现了 ≥ 1 个服务 → 展示给用户确认，确认后继续
  │     如果 services/ 目录为空或不存在 → 进入第 3 优先
  │
  ├─ 第 3 优先: 从 Stage 1 设计文档直接提取
  │     读取 designs/{id}-design.md 的「服务影响分析」表
  │     如果表中有服务列表 → 直接使用（跳过 service-registry 验证，因为 registry 不存在）
  │     警告用户: "service-registry.yaml 不存在，已从设计文档直接提取服务列表。建议运行 hw-knowledge-agent service-discovery 生成注册表。"
  │     如果设计文档也没有服务影响分析表 → 进入第 4 优先
  │
  └─ 第 4 优先: 用户交互输入
       向用户提问:
         "无法自动确定受影响的服务列表。请提供本次需求涉及的服务:"
         选项 A: 输入服务名称（逗号分隔）
         选项 B: 只有 1 个服务（单体模式，直接输入服务路径）
         选项 C: 跳过服务验证，手动指定 per-service 设计文档路径
       用户输入后，记录到临时服务清单，继续后续步骤
       同时提示: "建议运行 hw-knowledge-agent service-discovery 生成 service-registry.yaml，避免下次重复询问。"
```

**单体模式 (architecture: "monolith"):**
- 如果 `service-registry.yaml` 不存在且 `services/` 目录为空 → 跳过服务验证
- 直接从需求规格和设计文档提取工作单元（组件/端点/页面）
- 任务不绑定 `service` 字段，使用 `component` 字段

**为什么不能臆想服务:**
- 服务列表的唯一权威来源是 `service-registry.yaml`（由 hw-knowledge-agent 从代码自动发现）
- 本次需求涉及哪些服务的唯一权威来源是 Stage 1 设计文档的「服务影响分析」表
- 如果跳过这步直接猜测 "可能涉及 user-service 和 order-service"，会遗漏实际受影响的服务或引入不存在的服务
- 新服务必须先通过 hw-knowledge-agent 的 service-discovery 注册到 service-registry.yaml，才能在任务拆分中被引用

**默认模式: 1 服务 = 1 任务**

**任务分配必须基于服务能力，禁止臆想:**

每个任务的 `service` 分配不是填个名字就完事。必须确认该服务有能力执行此任务:

```
能力校验清单（每个任务分配时必须通过，全部通过才写入 tasks.yaml）:

  1. 语言/框架匹配:
     - 任务的实现语言 = 服务的 language 字段（如 java-springboot）
     - 不能把 TypeScript React 前端任务分配给 Java Spring Boot 后端服务
     - 来源: service-registry.yaml → language，Stage 1 代码调查 → 语言/框架验证

  2. 服务路径存在:
     - service_path 指向的目录必须存在（如 services/user-service/）
     - 该目录必须是 git 仓库（git rev-parse --show-toplevel 通过）
     - 来源: service-registry.yaml → local_path

  3. 服务能力覆盖:
     - 任务涉及的 API 端点 → 在服务的 provides_apis 范围内（或设计文档明确新增）
     - 任务涉及的数据操作 → 在服务的 owns_data 范围内（或设计文档明确新增）
     - 任务涉及的外部调用 → 在服务的 consumes_apis 范围内（或设计文档明确新增）
     - 来源: Stage 1 代码调查 → 服务能力摘要

  4. 不匹配处理:
     - 如果任务需要的 API/数据不在服务的能力范围内 → 检查设计文档是否规划了新增
     - 如果设计文档也没有 → 阻塞，升级人工（可能是服务边界划分问题）
     - 如果任务需要的能力分散在多个服务 → 重新审视拆分，可能需要按服务边界重新切
```

**如果服务内部功能点互相独立且可并行验证，才进一步拆分:**

| 拆分维度 | 拆分为 | 粒度 |
|---------|--------|------|
| 默认: 整个服务 | 1 个任务（实现 + UT + API 测试） | 1-3h |
| 可选: 按端点组拆分 | 每 1-3 个相关端点 → 1 个任务 | 1-2h |
| 可选: 按独立组件拆分 | 每个独立组件 → 1 个任务 | 1-2h |
| 可选: 按用户故事拆分 | 每个用户故事 → 1 个任务 | 1-2h |
| E2E 测试 | 1 个独立任务（跨服务编排，最后一个 wave） | 1-2h |

**每个任务必须自包含（纵向切片）:**

```
Task-{id}: {名称}
├── 实现代码
├── UT 设计 + UT 实现（来自该服务设计文档 Section 10.3 中对应部分的用例）
└── API 测试设计 + API 测试实现（来自该服务设计文档 Section 10.4 中对应端点的用例）
```

**服务内跨切关注点（共享 DB schema、公共工具、配置）的处理:**
- 归入该服务的第一个任务（wave 最前的那个）
- 如果跨切关注点工作量 > 1h，可单独拆为一个任务，其他任务依赖它

**拆分约束:**
- 每个任务必须能在**一个 git worktree** 中独立完成
- 任务粒度: 最少 30 分钟，最多 3 小时（AI 自主执行时间）
- 如果某个服务 > 3h → 按上述维度拆分子任务
- 如果某组任务 < 30min → 合并
- 不拆分也是合法的 —— 1 服务 = 1 任务是默认选项

**拆分决策检查清单:**

对候选拆分做以下检查，全部通过才拆分:

- [ ] 拆分后的每个任务可以独立验证（有自己的 AC，不依赖其他任务的测试结果来证明正确性）
- [ ] 拆分后的任务之间无循环代码依赖（如果是 API 依赖，通过 stub/mock 可消除则不算阻塞）
- [ ] 拆分后的任务有足够的工作量（≥ 30min），不会因为拆分产生过多的 worktree 创建/销毁开销
- [ ] 拆分不会破坏 TDD 纪律（每个任务内的 UT → API 执行顺序不被打乱）

### 第 2 步: 构建依赖图 (Dependency Graph)

**依赖类型:**

| 类型 | 含义 | 示例 | 阻塞? |
|------|------|------|--------|
| **代码依赖 (CODE)** | 任务 B 的代码 import/调用任务 A 的代码 | UserService 任务 B → UserService 任务 A 的共享模块 | 是 |
| **API 依赖 (API)** | 任务 B 调用的 API 端点由任务 A 实现 | 任务 B（前端消费） → 任务 A（API 端点） | 是 |
| **数据依赖 (DATA)** | 任务 B 需要任务 A 创建的数据库表/迁移 | 业务逻辑 → DB Migration | 是 |
| **服务间契约依赖 (CONTRACT)** | 任务 B 所在服务依赖任务 A 所在服务提供的 API 契约 | OrderService → UserService.findById() | 是（可并行设计，执行时通过 stub/mock 解除阻塞） |
| **顺序依赖 (SEQ)** | 任务 B 在逻辑上必须在 A 之后（非技术原因） | 重构 → 新功能（先重构再开发） | 是 |

**依赖图构建规则:**
1. 对每对任务 (A, B)，检查: B 的输入是否依赖 A 的输出？
2. 画出有向无环图 (DAG): `A → B` 表示 B 依赖 A
3. 标记依赖类型
4. 跨服务的 CONTRACT 依赖: 两个服务的任务可以并行开发，各自用对方的 API 契约 stub/mock。CONTRACT 类型不阻塞并行调度，但需要契约测试在 merge 前验证

**循环依赖检测:**
```
如果发现 A → B → C → A:
  1. 这三项任务不能拆分 —— 合并为一个大任务 (标注 CIRCULAR_MERGED)
  2. 或者在设计中重新审视 —— 循环依赖通常意味着设计问题
  3. 禁止用 "先做 A 的 stub，再做 B，再回来补 A" 来绕过 —— 这会破坏 TDD 纪律
```

### 第 3 步: 分配测试用例 (Assign Test Cases)

每个任务绑定来自 per-service 设计文档 Section 10 的测试用例。由于采用纵向拆分，每个任务自带对应切片内的 UT 和 API 测试:

| 任务 | 绑定的 UT 用例 | 绑定的 API 用例 | 验证顺序 |
|------|--------------|---------------|---------|
| Task-{id}: {名称} | UT-{ids} | API-{ids} | UT → API（任务内闭环） |

**分配规则:**
- 实现任务自包含: UT 用例 + API 用例在**同一个任务内部**完成
- TDD 铁律: 任务内先写 UT（RED → GREEN → REFACTOR），再写 API 测试（RED → GREEN → REFACTOR），两层都通过才算任务完成
- E2E 用例分配给独立的 E2E 任务（最后一个 wave），依赖所有服务任务完成
- UT 用例从 per-service 设计文档 Section 10.3 提取，API 用例从 Section 10.4 提取，E2E 用例从 Stage 3 的 `designs/{id}-e2e-design.md` 提取

### 第 4 步: 确定并行执行批次 (Parallelization Batching)

对 DAG 做拓扑排序，确定哪些任务可以并行:

```
Wave 1: 无依赖的任务 → 可全部并行（各服务的第一个任务通常在此）
Wave 2: 仅依赖 Wave 1 的任务 → 可全部并行
Wave 3: 依赖 Wave 1-2 的任务 → 可全部并行
...
Final Wave: E2E 测试任务（依赖所有实现任务）
```

**并行度约束:**
- 同一 Wave 中的任务数 ≤ `max_parallel_worktrees`（从 config 读取，默认 4）
- 如果超出 → 按关键路径长度排序，优先调度关键路径上的任务
- CONTRACT 依赖不阻塞并行调度 —— 两个服务的任务可以放在同一 Wave，通过 stub/mock 解除耦合
- E2E 测试任务永远是最后一个 Wave

### 第 5 步: 写入 tasks.yaml

**tasks.yaml 完整 Schema:**

```yaml
# _bmad/memory/hw-shared/tasks.yaml
requirement_id: "{REQ-YYYYMMDD-NNN}"
created_at: "{timestamp}"
total_estimated_hours: {n}
split_strategy: "one-task-per-service" | "by-endpoint" | "by-component" | "by-user-story"

tasks:
  - task_id: "hw-{NNN}"
    name: "{描述性名称}"
    description: "{1-2 句话描述做什么}"
    service: "{对应微服务名}"
    service_path: "{服务代码路径，来自 service-registry.yaml local_path，如 services/user-service}"
    repo_url: "{服务 git 仓库地址，来自 service-registry.yaml repo}"
    language: "{服务语言/框架，来自 service-registry.yaml language，如 java-springboot}"
    component: "{对应设计文档中的组件名（如适用）}"
    design_doc: "designs/{id}-service-{svc}-design.md"
    worktree_path: "{worktree_base}/hw-task-{NNN}"
    wave: {1|2|3|...}
    estimated_hours: {n}
    is_e2e_task: false

    capability_verified: true   # 任务分配已根据服务实际能力校验（禁止臆想分配）
    capability_checks:           # 校验记录
      - check: "服务语言匹配任务类型"
        passed: true
        detail: "{language} 可执行此类任务"
      - check: "服务路径存在"
        passed: true
        detail: "{service_path} 已验证存在"
      - check: "服务能力覆盖任务范围"
        passed: true
        detail: "该任务涉及的 API/数据在服务 provides_apis/owns_data 范围内"

    dependencies:
      - task_id: "hw-{NNN}"
        type: "CODE|API|DATA|CONTRACT|SEQ"
        reason: "{为什么依赖}"
        blocking: true|false   # CONTRACT 类型通常为 false（可通过 stub 并行）

    acceptance_criteria:
      - ac_id: "AC-{N}"
        source: "requirements/{id}.md"
        description: "{具体、可测量的完成标准}"

    test_bindings:
      ut_cases: ["UT-{ids}"]       # 来自 per-service 设计文档 Section 10.3
      api_cases: ["API-{ids}"]     # 来自 per-service 设计文档 Section 10.4
      # 注意: UT 和 API 测试在此任务内部完成，不是独立任务

    review_requirements:
      - reviewer: "security|logic|performance"
        reason: "{为什么需要此审查者}"

    status: "pending"
    assigned_worktree_controller: null

  - task_id: "hw-E2E-{NNN}"
    name: "E2E 集成测试"
    description: "跨服务端到端测试，验证完整用户旅程"
    service: null
    design_doc: "designs/{id}-e2e-design.md"
    worktree_path: "{worktree_base}/hw-task-E2E-{NNN}"
    wave: {final}
    estimated_hours: {n}
    is_e2e_task: true

    dependencies:
      - task_id: "hw-{ids}"
        type: "TEST"
        reason: "E2E 测试需要所有服务实现完成"
        blocking: true

    acceptance_criteria:
      - ac_id: "AC-{N}"
        source: "designs/{id}-e2e-design.md"
        description: "E2E 测试场景全部通过"

    test_bindings:
      e2e_cases: ["E2E-{ids}"]    # 来自 Stage 3 E2E 设计文档

    status: "pending"
    assigned_worktree_controller: null

waves:
  - wave: 1
    tasks: ["hw-{ids}"]
    max_parallel: {n}
  - wave: 2
    tasks: ["hw-{ids}"]
    depends_on: [1]
  - wave: {final}
    tasks: ["hw-E2E-{NNN}"]
    depends_on: [{all_previous}]
```

**同时初始化 worktree-registry.yaml:**

```yaml
# _bmad/memory/hw-controller/worktree-registry.yaml
requirement_id: "{REQ-YYYYMMDD-NNN}"
created_at: "{timestamp}"

worktrees:
  hw-task-{NNN}:
    branch: "hw-task-{NNN}"
    task_id: "hw-{NNN}"
    status: "pending"
    wave: {1|2|3}
    created_at: null
    started_at: null
    completed_at: null
    review_status:
      security: null
      logic: null
      performance: null
    test_status:
      ut: null
      api: null
      e2e: null
```

### 第 6 步: 导出 dependencies.json（harness_framework 消费格式）

将 tasks.yaml 的 wave 结构转换为 harness_framework 兼容的 `dependencies.json`，用于写入 Consul KV 由 Aggregator 调度执行。

**转换规则:**

| tasks.yaml | dependencies.json |
|-----------|-------------------|
| 每个 Wave | 1 个 `parallel` 节点 + 1 个 `aggregate` 节点 (fan-out → fan-in) |
| Wave 内的每个任务 | `parallel` 节点的 child, `type: task` |
| Wave N 的 parallel | `depends_on: [wave-{N-1}-merge]` |
| Wave 1 的 parallel | `depends_on: []` |
| E2E 任务 (Final Wave) | `type: task`, `depends_on: [wave-{last}-merge]` |
| CONTRACT 依赖 | `"blocking": false` |
| test_bindings / review_requirements | 放入 `metadata` 字段透传 |
| 服务名 (service 字段) | `service_name` |

**特殊处理:**
- 如果整个需求只有 1 个 Wave (所有任务互不依赖)，不需要 parallel/aggregate 包装，任务直接平铺在 `tasks` 数组中
- CONTRACT 依赖（跨服务 API 契约）标记 `blocking: false`，允许两个服务并行开发（各自用 stub）
- CODE/DATA/SEQ 依赖 → `blocking: true`（默认），必须等待上游 DONE

**dependencies.json 完整 Schema:**

```json
{
  "req_id": "REQ-YYYYMMDD-NNN",
  "title": "需求标题",
  "guardrails": {
    "abort_check_interval_seconds": 30
  },
  "tasks": [
    {
      "name": "wave-1",
      "type": "parallel",
      "depends_on": [],
      "children": ["hw-001", "hw-002"]
    },
    {
      "name": "hw-001",
      "type": "task",
      "service_name": "user-service",
      "service_path": "services/user-service",
      "repo_url": "git@github.com:org/user-service.git",
      "language": "java-springboot",
      "capability": "dev",
      "description": "实现用户注册API",
      "depends_on": [],
      "blocking": true,
      "metadata": {
        "task_id": "hw-001",
        "component": "UserController",
        "design_doc": "designs/REQ-001-service-user-service-design.md",
        "estimated_hours": 2,
        "capability_verified": true,
        "capability_checks": [
          {"check": "语言匹配", "passed": true, "detail": "java-springboot"},
          {"check": "路径存在", "passed": true, "detail": "services/user-service"},
          {"check": "能力覆盖", "passed": true, "detail": "API/数据在 provides_apis/owns_data 范围内"}
        ],
        "test_bindings": {
          "ut_cases": ["UT-1", "UT-2"],
          "api_cases": ["API-1"]
        },
        "review_requirements": [
          {"reviewer": "security", "reason": "涉及用户认证"},
          {"reviewer": "logic", "reason": "注册逻辑需验证"},
          {"reviewer": "performance", "reason": "预期高并发"}
        ]
      }
    },
    {
      "name": "hw-002",
      "type": "task",
      "service_name": "order-service",
      "service_path": "services/order-service",
      "repo_url": "git@github.com:org/order-service.git",
      "language": "java-springboot",
      "capability": "dev",
      "description": "实现订单创建API",
      "depends_on": ["hw-001"],
      "blocking": false,
      "metadata": {
        "task_id": "hw-002",
        "component": "OrderController",
        "design_doc": "designs/REQ-001-service-order-service-design.md",
        "estimated_hours": 2,
        "capability_verified": true,
        "capability_checks": [
          {"check": "语言匹配", "passed": true, "detail": "java-springboot"},
          {"check": "路径存在", "passed": true, "detail": "services/order-service"},
          {"check": "能力覆盖", "passed": true, "detail": "API/数据在 provides_apis/owns_data 范围内"}
        ],
        "test_bindings": {
          "ut_cases": ["UT-3", "UT-4"],
          "api_cases": ["API-2"]
        },
        "review_requirements": [
          {"reviewer": "logic", "reason": "订单状态机需验证"}
        ]
      }
    },
    {
      "name": "wave-1-merge",
      "type": "aggregate",
      "depends_on": ["wave-1"]
    },
    {
      "name": "hw-E2E-001",
      "type": "task",
      "service_name": "_test",
      "capability": "test",
      "description": "E2E集成测试",
      "depends_on": ["wave-1-merge"],
      "metadata": {
        "task_id": "hw-E2E-001",
        "design_doc": "designs/REQ-001-e2e-design.md",
        "estimated_hours": 1.5,
        "test_bindings": {
          "e2e_cases": ["E2E-1", "E2E-2"]
        }
      }
    }
  ]
}
```

**简化示例（单 Wave，无 parallel 包装）:**

```json
{
  "req_id": "REQ-001",
  "title": "用户注册功能",
  "tasks": [
    {
      "name": "hw-001",
      "type": "task",
      "service_name": "user-service",
      "service_path": "services/user-service",
      "repo_url": "git@github.com:org/user-service.git",
      "language": "java-springboot",
      "capability": "dev",
      "depends_on": [],
      "metadata": {
        "capability_verified": true,
        "test_bindings": {"ut_cases": ["UT-1"], "api_cases": ["API-1"]}
      }
    }
  ]
}
```

**写入位置:** `{project-root}/_bmad-output/{requirement_id}/dependencies.json`

## 过渡门禁

任务拆分完成，可以进入执行阶段的条件:

- [ ] 受影响服务列表来源已记录（service-registry / auto-discovery / 设计文档 / 用户输入），未臆想
- [ ] 每个任务的 `service_path` + `repo_url` + `language` 已从服务注册表填充（非空）
- [ ] 每个任务的能力校验已通过（`capability_verified: true`）: 语言匹配 + 路径存在 + 能力覆盖
- [ ] 如果使用了 fallback（第 2/3/4 优先），已提示用户运行 `hw-knowledge-agent service-discovery` 生成 service-registry.yaml
- [ ] tasks.yaml 包含所有受影响服务的任务 + 1 个 E2E 任务
- [ ] 每个任务有明确的 AC（来自需求规格）
- [ ] 每个非 E2E 任务自包含 UT 用例 + API 用例（来自 per-service 设计文档 Section 10）
- [ ] 依赖图无循环（所有 CIRCULAR_MERGED 已标注并合理化）
- [ ] 每个任务估算时间在 0.5-3h 范围内
- [ ] 并行 Wave 规划完成，每 Wave 任务数 ≤ max_parallel_worktrees
- [ ] E2E 任务在最后一个 Wave，依赖所有实现任务
- [ ] worktree-registry.yaml 已初始化
- [ ] `split_strategy` 已标注（默认 `one-task-per-service`）
- [ ] 人类确认: "拆分合理，进入执行"

**失败处理:**
- 循环依赖无法通过合并解决 → 升级到人工，可能需要回到设计阶段
- 某 Wave 任务数超过并行度上限 → 人工确认是否增加并行度或接受串行化
- 任务粒度不达标 → 回到第 1 步重新拆分

**完成确认语:** "{N} 个服务拆分为 {M} 个任务（策略: {split_strategy}），{W} 个并行 Wave + 1 个 E2E Wave。依赖图无循环。每个任务自包含 UT + API 测试。准备好进入执行阶段吗？"
