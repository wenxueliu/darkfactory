# 任务拆分 (Task Decomposition)

参考: Compound Engineering task planning (DAG 依赖图 + 拓扑排序 + 临界路径分析) +
      BMAD sprint planning (任务粒度约束 + AC 追溯 + 并行度最大化)

## 核心理念

任务拆分是把设计文档翻译成**可并行执行的工作单元**。拆分质量直接决定并行效率——拆太粗，一个 worktree 做太久；拆太细，通信开销吃掉并行收益。目标: **每个任务 1-3 小时的 AI 自主执行 + 无循环依赖 + 最大化并行度**。

## 拆分流程 (5 步)

### 第 1 步: 从设计文档提取工作单元 (Extract Work Units)

**输入:**
- 设计文档: `designs/{id}-design.md`
- 需求规格: `requirements/{id}.md`
- ADR: `knowledge-base/decisions/ADR-*.md`

**提取规则:**

| 设计文档章节 | 提取为 | 粒度 |
|------------|--------|------|
| Section 5: 架构设计 — 组件职责表 | 每个组件 → 1 个实现任务 | 新建组件: 1-3h, 修改组件: 0.5-2h |
| Section 6: API/接口设计 — 端点表 | 每 1-3 个相关端点 → 1 个任务 | 1-2h |
| Section 3: 页面设计 — 页面清单 | 每个页面 → 1 个任务 (含前端组件) | 1-3h |
| Section 10.3: UT 设计 | 分配到各组件任务中 (不单独拆) | — |
| Section 10.4: API 测试 JSON | 1 个独立任务 (Postman Collection) | 0.5-1h |
| Section 10.5: E2E 测试 | 1 个独立任务 (端到端自动化) | 1-2h |
| Section 7: 状态管理 — 状态机 | 1 个任务 (如果状态机跨多个组件) | 1-2h |
| Section 9: 安全设计 | 渗透到各任务中 (不单独拆，除非独立安全基础设施) | — |

**拆分约束:**
- 每个任务必须能在**一个 git worktree** 中独立完成
- 任务粒度: 最少 30 分钟，最多 3 小时（AI 自主执行时间）
- 如果某个组件 > 3h → 拆分子组件（如: "UserService CRUD" + "UserService 权限校验"）
- 如果某组任务 < 30min → 合并（如: 3 个简单 GET 端点 → 1 个任务）

### 第 2 步: 构建依赖图 (Dependency Graph)

**依赖类型:**

| 类型 | 含义 | 示例 | 阻塞? |
|------|------|------|--------|
| **代码依赖 (CODE)** | 任务 B 的代码 import/调用任务 A 的代码 | UserService → OrderService 依赖 UserService.findById() | 是 |
| **接口依赖 (API)** | 任务 B 调用任务 A 提供的 API 端点 | 前端页面 → 后端 API | 是 |
| **数据依赖 (DATA)** | 任务 B 需要任务 A 创建的数据库表/迁移 | 业务逻辑 → DB Migration | 是 |
| **测试依赖 (TEST)** | 任务 B 的测试需要任务 A 的测试数据/环境 | E2E → API 实现完成 | 是 (可并行设计，但不可并行执行) |
| **顺序依赖 (SEQ)** | 任务 B 在逻辑上必须在 A 之后（非技术原因） | 重构 → 新功能（先重构再开发） | 是 |

**依赖图构建规则:**
1. 对每对任务 (A, B)，检查: B 的输入是否依赖 A 的输出？
2. 画出有向无环图 (DAG): `A → B` 表示 B 依赖 A
3. 标记依赖类型

**循环依赖检测:**
```
如果发现 A → B → C → A:
  1. 这三项任务不能拆分 —— 合并为一个大任务 (标注 CIRCULAR_MERGED)
  2. 或者在设计中重新审视 —— 循环依赖通常意味着设计问题
  3. 禁止用 "先做 A 的 stub，再做 B，再回来补 A" 来绕过 —— 这会破坏 TDD 纪律
```

### 第 3 步: 分配测试用例 (Assign Test Cases)

每个任务必须绑定来自设计文档 Section 10 的测试用例:

| 任务 | 绑定的 UT 用例 | 绑定的 API 用例 | 绑定的 E2E 用例 | 验证顺序 |
|------|--------------|---------------|----------------|---------|
| Task-{id}: {名称} | UT-{ids} | API-{ids} (如涉及) | E2E-{ids} (如涉及) | UT → API → E2E |

**分配规则:**
- 实现任务 (组件/API/页面) 绑定 UT 用例 + API 用例
- API 测试任务绑定 Postman Collection 中的所有 API 用例
- E2E 测试任务绑定所有 E2E 用例（依赖所有实现任务完成）
- UT 用例必须在实现任务**内部**完成（TDD: 先写测试，再写代码），不能依赖外部任务

### 第 4 步: 确定并行执行批次 (Parallelization Batching)

对 DAG 做拓扑排序，确定哪些任务可以并行:

```
批次 1 (Wave 1): 无依赖的任务 → 可全部并行
批次 2 (Wave 2): 仅依赖批次 1 的任务 → 可全部并行
批次 3 (Wave 3): 依赖批次 1-2 的任务 → 可全部并行
...
```

**并行度约束:**
- 同一批次中的任务数 ≤ `max_parallel_worktrees`（默认 4，从 config 读取）
- 如果超出 → 按关键路径长度排序，优先调度关键路径上的任务
- E2E 测试任务永远是最后一个批次

### 第 5 步: 写入 tasks.yaml

**tasks.yaml 完整 Schema:**

```yaml
# _bmad/memory/hw-shared/tasks.yaml
requirement_id: "{REQ-YYYYMMDD-NNN}"
design_id: "{DESIGN-YYYYMMDD-NNN}"
created_at: "{timestamp}"
total_estimated_hours: {n}

tasks:
  - task_id: "hw-{NNN}"
    name: "{描述性名称}"
    description: "{1-2 句话描述做什么}"
    component: "{对应设计文档 5.3 的组件名}"
    worktree_path: "{worktree_base}/hw-task-{NNN}"
    wave: {1|2|3|...}
    estimated_hours: {n}

    dependencies:
      - task_id: "hw-{NNN}"
        type: "CODE|API|DATA|TEST|SEQ"
        reason: "{为什么依赖}"

    acceptance_criteria:
      - ac_id: "AC-{N}"
        source: "{requirements/{id}.md}"
        description: "{具体、可测量的完成标准}"

    test_bindings:
      ut_cases: ["UT-{ids}"]
      api_cases: ["API-{ids}"]
      e2e_cases: ["E2E-{ids}"]

    review_requirements:
      - reviewer: "security|logic|performance"
        reason: "{为什么需要此审查者}"

    status: "pending"
    assigned_worktree_controller: null

waves:
  - wave: 1
    tasks: ["hw-{ids}"]
    max_parallel: {n}
  - wave: 2
    tasks: ["hw-{ids}"]
    depends_on: [1]
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

## 过渡门禁

任务拆分完成，可以进入执行阶段的条件:

- [ ] tasks.yaml 包含所有任务，每个任务有明确的 AC
- [ ] 依赖图无循环（所有 CIRCULAR_MERGED 已标注并合理化）
- [ ] 每个任务绑定了具体的 UT/API/E2E 用例
- [ ] 每个任务估算时间在 0.5-3h 范围内
- [ ] 并行批次规划完成，每批任务数 ≤ max_parallel_worktrees
- [ ] worktree-registry.yaml 已初始化
- [ ] 人类确认: "拆分合理，进入执行"

**失败处理:**
- 循环依赖无法通过合并解决 → 升级到人工，可能需要回到设计阶段
- 某批次任务数超过并行度上限 → 人工确认是否增加并行度或接受串行化
- 任务粒度不达标 → 回到第 1 步重新拆分

**完成确认语:** "设计已拆分为 {N} 个任务，{M} 个并行批次。依赖图无循环。每个任务已绑定测试用例。准备好进入执行阶段吗？"
