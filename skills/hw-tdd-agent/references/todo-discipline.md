# TODO 纪律 (TODO Discipline)

## 核心理念

TODO list 不是建议，是强制约束。多步骤无 TODO = 不完整的工作。

## 何时必须使用 TODO list

满足以下任一条件时，**必须**先创建 TODO list 再开始工作：

1. **2 个及以上独立步骤** — 任何包含多个独立操作的任务
2. **跨文件变更** — 需要修改 2 个及以上文件
3. **有依赖顺序** — 步骤之间有先后依赖关系（A 必须在 B 之前）
4. **耗时任务** — 预估完成时间超过 5 分钟
5. **用户明确要求多个任务** — 用户以列表形式给出了多个要做的事

**例外:** 单一文件、单一步骤、可在一个工具调用内完成的操作 —— 不需要 TODO list。

## TODO 原子分解规则

### 好的分解 (Atomic)

每个 TODO 项应该是一个**可独立验证的单元**：

```
GOOD — 原子化，每项可独立验证：
1. 创建 User 模型的单元测试 (ut-red)
2. 实现 User 模型 (ut-green)
3. 重构 User 模型代码 (ut-refactor)
4. 创建 POST /users API 测试 (api-red)
5. 实现 POST /users 端点 (api-green)
6. 重构 API 代码 (api-refactor)
7. 运行全量测试验证
```

### 坏的分解 (Non-atomic)

```
BAD — 太粗粒度，内部包含多个不可分割的步骤：
1. 实现用户管理功能  ← 这是一个项目，不是一个步骤
2. 写测试            ← 什么测试？多少测试？哪一层？

BAD — 太细粒度，每个都是无意义的微步骤：
1. 打开文件
2. 看第3行
3. 在第4行插入import
4. 保存文件
```

### 分解检查清单

每个 TODO 项应满足：
- [ ] 描述了一个明确的、可观察的结果
- [ ] 可以在单次连续操作中完成（不中断、不切换上下文）
- [ ] 完成后有明确的验证方式（测试通过/构建成功/文件存在）
- [ ] 不与其他 TODO 项重叠
- [ ] 使用了动词开头的命令式描述

## 标记纪律 (Marking Discipline)

### 铁律

```
EXACTLY ONE task in_progress at any time.
```

**违反即错误:**
- 同时有 2 个 in_progress → 错误
- 0 个 in_progress 但在执行 → 错误
- 标记 completed 但实际未完成 → 严重错误

### 工作流程

```
1. 创建 TODO list → 所有项初始为 pending
2. 选择第一项 → 标记为 in_progress
3. 开始执行该项
4. 该项完成 → 立即标记为 completed
5. 选择下一项 → 标记为 in_progress
6. 重复直到所有项 completed
```

### "立即"的意思

**标记 completed 的时刻 = 该项工作真正完成的时刻。**

不是：
- "等我把这批一起标记"  ← 禁止批量标记
- "我做完再回来标记"    ← 做完就是现在
- "等验证通过再标记"    ← 标记的是步骤完成，验证是单独的步骤

正确做法：
- 写完测试 → 立即标记 ut-red 为 completed
- 实现完代码 → 立即标记 ut-green 为 completed
- 重构完成 → 立即标记 ut-refactor 为 completed

## 反模式 (Anti-Patterns)

### 反模式 1: 批量完成 (Batch Completion)

```
# BAD
做完步骤1、2、3后，一次性标记3个为completed

# GOOD
做完步骤1 → 标记步骤1为completed
做完步骤2 → 标记步骤2为completed
做完步骤3 → 标记步骤3为completed
```

### 反模式 2: 忘记更新状态 (Stale Status)

```
# BAD
agent: "现在开始实现 User 模型"  ← TODO 仍显示上一个步骤 in_progress
[5分钟后]
agent: "User 模型实现完成"       ← TODO 仍显示上一个步骤 in_progress
[hack]$ 用户打断："当前进度是什么？agent你还活着吗？"
```

```
# GOOD
agent: [标记 ut-green 为 in_progress] "现在开始实现 User 模型"
[5分钟后]
agent: [标记 ut-green 为 completed] "User 模型实现完成 (GREEN)"
```

### 反模式 3: 多步骤工作无 TODO (Missing TODO)

```
# BAD
用户: "实现用户注册功能，包括 UT 和 API 测试"
agent: [直接开始写代码，没有创建 TODO list]

# GOOD
用户: "实现用户注册功能，包括 UT 和 API 测试"
agent: [创建包含6-8个步骤的 TODO list]
agent: [开始执行第一个步骤]
```

### 反模式 4: 过早完成 (Premature Completion)

```
# BAD
TODO 全部标记 completed → 报告 DONE
但实际上 VERIFY 阶段测试失败了 ← 没有对应 TODO 项跟踪验证

# GOOD
最后一个 TODO 项: "运行全量测试验证"
该项标记 completed 意味着所有测试已通过
```

### 反模式 5: TODO 作为事后补记 (Retroactive TODO)

```
# BAD
已经完成了3个步骤 → 现在创建 TODO list → 标记已完成项为 completed
// TODO list 变成了已完成工作的日志，失去规划和管理作用

# GOOD
总是先创建 TODO list，再开始执行
如果发现遗漏的步骤，添加新的 pending 项
```

## TODO 强制检查点

以下时刻必须检查 TODO 状态：

| 时刻 | 检查 |
|------|------|
| 开始新任务时 | 是否需要创建 TODO list？ |
| 每完成一个步骤后 | 立即标记 completed；下一个步骤是什么？ |
| 被打断再恢复时 | TODO 状态是否反映实际进度？ |
| 报告工作完成前 | 所有项是否为 completed？ |
| 遇到阻塞时 | 阻塞的项标记为 pending，是否需要新项跟踪阻塞解除？ |

## 最终检查

报告 DONE 之前，TODO list 必须满足：
- [ ] 所有项的 status 为 `completed`
- [ ] 没有 pending 项被遗忘
- [ ] in_progress 计数 = 0（最后一项已标记完成）
- [ ] TODO list 准确反映了实际完成的工作（不是事后编造的）
