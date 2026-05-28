# 并行化设计 (Parallelism Design)

最大并行原则是 sw-strategic-planner 的核心规划质量指标。一个优秀计划的标志是它能多快被执行——这直接取决于任务是如何被分组到并行波浪中的。

---

## 核心并行化原则

### 粒度规则 (Granularity Rule)

**一个任务 = 一个模块/关注点 = 1-3 个文件。**

如果一个任务:
- 触及 4+ 个文件 → **必须拆分**
- 涉及 2+ 个不相关的关注点 → **必须拆分**
- 预计执行时间超过 2 小时 → **考虑拆分**

拆分不仅仅是为了并行性——它创建了更清晰的职责、更容易的审查和更精确的验收标准。

### 并行化目标 (Parallelism Target)

**目标每波 5-8 个任务。**

- 如果任何波（除最终的集成波外）少于 3 个任务 → 你拆分不足
- 如果任何波超过 10 个任务 → 你可能过度拆分了，考虑合并紧密耦合的任务
- 理想的波大小是 5-8: 足够以创造显著的并行加速，但不过多以至于上下文切换成为瓶颈

---

## Wave 构造规则

### Wave 定义

一个 Wave 是一组可以**同时执行**的任务（它们之间没有依赖关系）。一个 Wave 的所有任务必须完成后，下一个 Wave 才能开始。

### Wave 分配策略

#### Wave 1: 基础与脚手架 (Foundation & Scaffolding)

Wave 1 是解除后续任务阻塞的基础层。**每个 Wave 1 任务应该解除至少 3 个下游任务的阻塞。**

Wave 1 的典型内容:
- **项目脚手架**: 目录结构、配置文件
- **类型/接口/模式定义**: 所有模块共享的合约
- **共享常量/令牌**: 设计系统 tokens、配置值
- **存储接口 + mock 实现**: 解除核心逻辑的阻塞
- **认证中间件**: 解除受保护路由的阻塞
- **工具函数**: 共享 helpers
- **基础客户端模块**: 解除 API 消费者和 hooks 的阻塞

```
Wave 1 (Start Immediately):
├── Task 1: Types/interfaces [quick]
├── Task 2: Config/schema [quick]
├── Task 3: Design tokens [quick]
├── Task 4: Storage interface + mock [quick]
├── Task 5: Auth middleware [quick]
├── Task 6: Base client [quick]
└── Task 7: Shared utilities [quick]
```

**Wave 1 设计规则:**
- 所有在 2+ 个任务间共享的 types/interfaces/configs → Wave 1
- Wave 1 任务必须是 `quick` profile（快速执行）
- Wave 1 任务是唯一不依赖其他任务的组

#### Wave 2-N: 核心实现层 (Core Implementation)

中间层包含主要的业务逻辑、API 端点、UI 组件和集成任务。

```
Wave 2 (After Wave 1 — core modules, MAX PARALLEL):
├── Task 8: Core business logic (depends: 1, 4)
├── Task 9: API endpoints (depends: 1, 4, 6)
├── Task 10: Secondary storage impl (depends: 4)
├── Task 11: Error handling + retry (depends: 8)
├── Task 12: UI layout + navigation (depends: 3)
├── Task 13: API hooks (depends: 1, 6)
└── Task 14: Monitoring middleware (depends: 5)
```

**中间层设计规则:**
- 最大化并行性——依赖最小化原则
- 每波建议 5-8 个任务
- 组合独立于彼此的任务
- 一些任务可能依赖于前面波中的多个任务——这是正常的

#### Wave 3-N: 集成与端到端 (Integration & E2E)

后期层将独立的模块组合成连贯的端到端流程。

```
Wave 3 (After Wave 2 — integration):
├── Task 15: Main route combining modules (depends: 5, 11, 14)
├── Task 16: UI data visualization (depends: 12, 13)
├── Task 17: Integration tests (depends: 15, 16)
└── Task 18: Documentation (depends: all above)
```

**集成层设计规则:**
- 依赖数量较多是正常的（它们集成多个模块）
- 这波自然较小——没有足够多的独立集成任务来保持高并行性
- 集成任务是顺序执行之间的自然断点

#### Wave FINAL: 验证 (Verification)

始终以 4 个并行审查任务结束。

```
Wave FINAL (After ALL tasks — 4 parallel reviews):
├── F1: Plan Compliance Audit [oracle]
├── F2: Code Quality Review [unspecified-high]
├── F3: Real Manual QA [unspecified-high + playwright]
└── F4: Scope Fidelity Check [deep]
```

---

## 依赖最小化策略 (Dependency Minimization)

### 核心洞察

**依赖 = 顺序瓶颈。每个依赖都从并行速度提升中扣除。**

### 策略 1: 前置共享依赖 (Frontload Shared Dependencies)

将所有共享的 types/interfaces/configs/contracts 提取到 Wave 1。这解锁了在后续所有波中依赖它们的任务之间的最大并行性。

```
BAD:
  Wave 1: Task A (build feature X)
  Wave 2: Task B (build feature Y — needs type definitions that Task A creates as a side effect)
  → Task B 不必要地被 Task A 阻塞。Task B 真正需要的是 types，而非整个 feature X。

GOOD:
  Wave 1: Task Types (define all shared types), Task Config (define all config)
  Wave 2: Task A (feature X), Task B (feature Y) — both can use Types + Config
  → Task A 和 Task B 并行执行。
```

### 策略 2: 接口优先于实现 (Interfaces Before Implementations)

为依赖（存储、外部服务）先定义接口 + mock，然后再实现。下游消费者可以在 Mock 上开发，无需等待真实实现。

```
Wave 1: Task 4 (Storage interface + in-memory mock)
Wave 2:
  Task 8 (Core logic — uses mock storage, can start immediately with Wave 1 done)
  Task 10 (Real DB storage — also depends on storage interface)
  → Core logic 不需要等待 DB 存储实现。
```

### 策略 3: 延迟耦合到集成波 (Defer Coupling to Integration Waves)

将共享状态的紧密耦合推迟到集成波。单个模块在隔离中开发，然后在集成时连接。

```
Wave 1: Types + Interfaces
Wave 2 (Parallel): Module A, Module B, Module C — 每个在自己的隔离中开发
Wave 3 (Integration): Module AB — 仅在 A 和 B 都完成时连接 A 和 B
```

### 策略 4: 避免假性依赖 (Avoid Spurious Dependencies)

任务 X 依赖任务 Y 只是因为它需要 Y 的一个小的类型定义 → 将类型移到 Wave 1。

```
BAD:  Task 10 (depends on Task 8 for user type)
GOOD: Task 10 (depends on Task 1 where User type is defined)
```

---

## Wave 构造示例: 好 vs 坏

### 坏的 Wave 构造（过于顺序）

```
Wave 1: Task 1 (types)
Wave 2: Task 2 (auth — depends: 1)
Wave 3: Task 3 (API — depends: 2)
Wave 4: Task 4 (UI — depends: 3)
Wave 5: Task 5 (tests)
→ 5 个波浪，最大并行度 = 1。没有速度提升。
```

**问题诊断**:
- 每个 Wave 只包含一个任务（拆分不足）
- auth 不必要地阻塞 API（API 可以使用 mock auth，或者 auth 被限制到特定路由）
- UI 不必要地被 API 阻塞（UI 可以使用 mock API）

### 好的 Wave 构造（最大化并行）

```
Wave 1 (5 tasks): Types + Config + Storage interface + Mock auth + Base client
Wave 2 (7 tasks): Auth real impl + API endpoints + UI layout + Business logic + API hooks + Monitoring + Secondary storage
Wave 3 (3 tasks): Main route + UI integration + Integration tests
Wave FINAL (4 tasks): F1-F4 reviews
→ 4 个波浪，最大并行度 = 7。~70% 并行加速。
```

### 过度拆分的波浪构造（并行但碎片化）

```
Wave 1 (15 tasks): 每个 types 一个文件、每个接口一个文件、每个 util 一个文件...
→ 虽然高度并行，但上下文切换开销占主导地位。将紧密相关的文件合并为合理粒度的任务。
```

---

## 跨 Wave 依赖处理

### 依赖链可视化

在 Execution Strategy 章节中，始终提供完整的依赖矩阵:

```
- Tasks 1-6: No dependencies (Wave 1)
- Task 7: depends on 1, 4 — Wave 2
- Task 8: depends on 1, 4, 6 — Wave 2
- Task 9: depends on 4 — Wave 2
- Task 10: depends on 7 — Wave 3 (depends on Wave 2 task)
- Task 11: depends on 5 (from Wave 1) — Wave 2 (only needs Wave 1)
```

### 关键路径识别

始终在 Execution Strategy 中标识关键路径:

```
Critical Path: Task 1 -> Task 4 -> Task 7 -> Task 10 -> Task 14 -> F1-F4 -> user okay
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 7 (Wave 2)
```

关键路径 = 从开始到结束的最长依赖链。关键路径上的任何延迟都会延迟整个项目。关键路径外的任务有 slack。

---

## 特殊情况

### 当任务数量较少时（<10 个任务）

- 仍应用依赖最小化策略——但 Waves 自然会更少
- 可能只有 2-3 个 Waves
- 3 个任务的 Wave 是可以接受的（任务总数很少）
- 不要为了创建更多 Waves 而过度拆分——保持合理粒度

### 当依赖链天然是强顺序时

- 有些领域天然是顺序的（如 "分析问题 -> 设计方案 -> 实现方案"）
- 在这种情况下，接受较少的并行性，并在计划中解释原因
- 不要强行并行化本质上是顺序的任务——它会导致返工

### 跨多个仓库/服务的工作

- 每个仓库是一个并行轨道
- 每个轨道内的 Waves 可以独立于其他轨道
- 最终的跨服务集成 Wave 使轨道重新同步

```
Track A (repo-1): Wave 1A -> Wave 2A -> Wave 3A
Track B (repo-2): Wave 1B -> Wave 2B -> Wave 3B
Track C (repo-3): Wave 1C -> Wave 2C

FINAL (Cross-service): Wave FINAL (集成所有轨道)
```

---

## 并行化反模式

- ❌ **串行一切** — 将每个任务放在自己的 Wave 中，没有任何理由
- ❌ **假性依赖** — 任务 Y 被列为依赖任务 X，但实际上不需要等待 X 完成
- ❌ **单任务波** — Wave 中只有一个任务，且该任务不阻塞其他 Wave
- ❌ **巨型任务** — 一个任务触及 10+ 文件和 5 个关注点（拆分它）
- ❌ **过度拆分** — 15 个微小任务只触及 1 个文件每个（组合它们）
- ❌ **忽略关键路径** — 所有任务平等列出，没有标识瓶颈
- ❌ **未提取共享依赖** — types/interfaces/configs 散布在多个任务中，每个任务将其他任务阻塞在其小部分之外
