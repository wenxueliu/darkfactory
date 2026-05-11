# Dependency Analysis: 依赖分析与波次构建

## 核心原则

**PARALLEL BY DEFAULT (默认并行)**：只有命名依赖才能阻止任务并行执行。

## 依赖类型

### 命名依赖 (Named Dependency) -- 阻止并行

任务 B 显式声明依赖任务 A，满足以下任一条件：

1. **输入依赖 (Input Dependency)**：任务 B 读取或消费任务 A 的产出（文件、值、schema、接口）
   - 示例: "实现用户登录 API -- depends on: 实现用户注册 API (需要注册后才能测试登录)"

2. **文件冲突 (File Conflict)**：任务 A 和任务 B 会修改同一个文件
   - 示例: 两个任务都需要修改 `src/auth/service.go` 的不同部分

3. **接口契约依赖 (Contract Dependency)**：任务 B 调用任务 A 产出的接口
   - 示例: "实现前端登录页面 -- 需要后端登录 API 已就绪"

**关键：命名依赖必须明确写在任务描述中，或能从任务目标明确推断出来。不推定、不猜测依赖。**

### 非依赖 (Non-Dependency) -- 允许并行

以下情况不应阻止并行：

| 情况 | 原因 |
|------|------|
| 任务在同一目录 | 不同文件无冲突 |
| 任务涉及同一服务的不同模块 | 模块间独立 |
| 任务有逻辑先后但无数据传递 | 可以并行 |
| 任务属于同一类别 (如 "所有前端任务") | 类别不是依赖 |

## 波次构建算法

### 算法步骤

```
输入: 任务列表 tasks，每个任务包含 id, description, depends_on[]
输出: 波次列表 waves[]

1. 构建已完成任务集合 completed = {task | task.status == 'x'}
2. 构建依赖图 G: task -> depends_on[]
3. 循环直至所有 incompleted 任务分配完毕:
   a. 找出当前波次候选: 所有 depends_on[] ⊆ completed 的未完成任务
   b. 如果候选为空且还有未分配任务 → 存在循环依赖或丢失依赖，报错
   c. 将候选加入当前波次
   d. 将候选标记为 completed（用于计算下一波次）
4. 返回 waves[]
```

### 算法特性

- **贪心最大化并行**：每波次包含所有依赖已满足的任务
- **无循环依赖**：如果检测到循环依赖，报告 "circular dependency detected" 并暂停
- **天然支持动态依赖**：如果某任务失败后放弃，依赖它的任务永远不会进入候选集

## 波次构建示例

### 示例 1: 混合依赖

```
任务列表:
  task-1: 实现用户注册 API
  task-2: 实现用户登录 API (depends on: task-1)
  task-3: 添加密码验证 (depends on: task-1)
  task-4: 实现前端注册页面
  task-5: 实现前端登录页面 (depends on: task-2)

波次分析:
  Wave 1 (parallel): task-1 (注册API), task-4 (前端注册页面)
    - task-1 和 task-4 无共享依赖，可并行
  Wave 2 (parallel): task-2 (登录API), task-3 (密码验证)
    - 两者都只依赖 task-1，互相无依赖
  Wave 3 (sequential): task-5 (前端登录页面)
    - 依赖 task-2

执行时间: T(task-1 || task-4) + T(task-2 || task-3) + T(task-5)
比纯串行节省: ~40-50%
```

### 示例 2: 完全可并行

```
任务列表:
  task-1: 添加日志中间件
  task-2: 添加 CORS 支持
  task-3: 添加 rate limiting
  task-4: 添加 health check 端点

波次分析:
  Wave 1 (parallel): task-1, task-2, task-3, task-4
    - 四个任务独立，无任何依赖

执行时间: T(max(task-1, task-2, task-3, task-4))
比纯串行节省: ~75%
```

### 示例 3: 完全串行

```
任务列表:
  task-1: 创建数据库 schema
  task-2: 实现 DAO 层 (depends on: task-1)
  task-3: 实现 Service 层 (depends on: task-2)
  task-4: 实现 Controller 层 (depends on: task-3)

波次分析:
  Wave 1: task-1
  Wave 2: task-2
  Wave 3: task-3
  Wave 4: task-4

执行时间: 等于纯串行
无法加速，但这是正确的。
```

## 执行时动态重分析

### 何时重分析

每次波次完成后，重新分析依赖：
1. 前一波次的产出可能消除了某些依赖
2. 失败并放弃的任务，其下游任务自动变为不可执行
3. 原本推断为串行的任务可能变得可并行

### 重分析步骤

```
After Wave N completes:
1. 更新已完成/已放弃任务集合
2. 对所有未完成任务重新执行波次构建算法
3. 新的 Wave N+1 可能比初始预期的更大（新解锁任务变多）
```

### 示例：动态解锁

```
初始分析:
  Wave 1: task-1, task-3
  Wave 2: task-2 (depends on: task-1)

实际执行:
  Wave 1: task-1 完成, task-3 完成
  Wave 2 重分析: task-2 可执行 + task-4 (原本依赖 task-3, 但 task-3 已完成)
  新 Wave 2: task-2, task-4 (并行!)
```

## 特殊依赖处理

### 跨波次依赖 (Cross-Wave Dependency)

如果任务 B 依赖的任务 A 不在当前计划中：
- 检查 A 是否在其他计划中 → 记录跨计划依赖
- 检查 A 是否是外部服务 → 不在本计划控制范围内
- 如果找不到 A → 标记 B 为 BLOCKED，记录到 problems.md

### 循环依赖检测

如果在构建波次时发现某些任务永远无法进入候选集（它们的依赖永远无法满足），检测循环：
```
对于无法满足的 X:
  追溯 X 的依赖链: X -> Y -> Z -> X → Circle detected
```

循环依赖必须人工解决。标记所有涉及任务为 BLOCKED，记录到 problems.md。

### 自依赖

任务不能依赖自身。如果检测到，忽略该声明。

## 波次派遣规则

### 波次内全部并行

```
// CORRECT: Wave 2 有 3 个任务，全部并行派遣
Delegate task-2 to hw-tdd-agent
Delegate task-3 to hw-tdd-agent
Delegate task-4 to hw-tdd-agent
// All three fire in ONE response

// WRONG: 逐个派遣，人为串行化
Delegate task-2 → wait → Delegate task-3 → wait → Delegate task-4
```

### 波次间自动衔接

波次 N 全部完成后，立即开始波次 N+1。不等待、不询问。

波次 N 中有任务失败（已放弃）→ 从波次 N+1 中移除依赖该失败任务的任务 → 将其标记为 BLOCKED → 继续波次 N+1 中剩下的任务。
