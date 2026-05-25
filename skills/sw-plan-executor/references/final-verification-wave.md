# Final Verification Wave: 终验波次

## 概述

Final Verification Wave 是计划执行的最后关卡。在所有实现任务完成后，启动全部审查 agent 并行审查，确保代码质量。

**这些不是常规任务，是审批关卡。** 每个审查者产生一个 VERDICT：APPROVE 或 REJECT。

## 审查者选择

### 根据配置决定审查者

从 `{project-root}/_bmad/config.yaml` 的 `hw.enabled_reviewers` 读取启用的审查者列表。

默认配置 `security,logic,performance` 对应三个审查者：

| 审查者 | Agent | 审查范围 |
|--------|-------|---------|
| Logic Review | `hw-reviewer-logic` | 正确性、边界情况、错误处理、逻辑 bug |
| Security Review | `hw-reviewer-security` | 漏洞、数据暴露、注入攻击、认证授权 |
| Performance Review | `hw-reviewer-performance` | 瓶颈、N+1 查询、内存泄漏、扩展性 |

### 可选的审查者

根据 `business_domain` 和 `enabled_reviewers` 配置，审查者数量可能不同：

| enabled_reviewers | 审查者列表 |
|-------------------|-----------|
| `security,logic,performance` | 3 个全开 (默认) |
| `security,logic` | 2 个 (安全和逻辑) |
| `logic,performance` | 2 个 (逻辑和性能) |
| `logic` | 1 个 (仅逻辑) |
| `none` | 跳过 Final Verification Wave |

如果配置为 `none` 或所有审查者都被禁用，跳过 Final Verification Wave 直接报告完成。

## 执行步骤

### Step 1: 确认实现完成

在启动 Final Wave 之前:
- 确认所有顶层实现任务的复选框都是 `[x]`
- 确认没有未放弃的 BLOCKED 任务

### Step 2: 收集上下文

为审查者准备上下文信息:

```
审查上下文:
- Plan: {plan-name}
- Tasks completed: {N/N}
- Files modified: {文件列表}
- Key decisions: {引用 decisions.md 中的关键决策}
- Notepad: {project-root}/_bmad/memory/hw-plan-executor/notepads/{plan-name}/
```

### Step 3: 并行启动所有审查

**所有审查者在同一个响应中并行启动。不逐个执行。**

审查者之间没有依赖关系，可以完全并行。

#### Logic Review 委托

委托 `hw-reviewer-logic` 进行逻辑审查：

委托提示应包含:
```
任务: 对计划 {plan-name} 的实现进行逻辑审查
范围: 所有修改的文件
上下文: {修改文件列表、关键决策、notepad 位置}
输出: {project-root}/_bmad/memory/hw-shared/reviews/{plan-name}-logic.md

审查重点:
- 逻辑正确性: 代码是否实现了所需功能
- 边界情况: null/空/极值处理
- 错误处理: 异常是否被正确捕获和处理
- 状态管理: 是否有 race condition 或不一致状态
- 代码路径: 所有分支是否正确

严重程度:
- P0: 导致系统崩溃或数据丢失
- P1: 功能错误或关键路径问题
- P2: 边界情况或非关键路径问题
- P3: 改进建议
```

#### Security Review 委托

委托 `hw-reviewer-security` 进行安全审查：

委托提示应包含:
```
任务: 对计划 {plan-name} 的实现进行安全审查
范围: 所有修改的文件
上下文: {修改文件列表、关键决策、notepad 位置}
输出: {project-root}/_bmad/memory/hw-shared/reviews/{plan-name}-security.md

审查重点:
- 注入攻击: SQL/命令/代码注入
- 认证和授权: 是否正确验证身份和权限
- 数据暴露: 敏感信息是否泄露 (日志、响应、错误信息)
- 输入验证: 用户输入是否被正确验证和清理
- 依赖安全: 第三方依赖是否有已知漏洞

严重程度: P0-P3 (同上)
```

#### Performance Review 委托

委托 `hw-reviewer-performance` 进行性能审查：

委托提示应包含:
```
任务: 对计划 {plan-name} 的实现进行性能审查
范围: 所有修改的文件
上下文: {修改文件列表、关键决策、notepad 位置}
输出: {project-root}/_bmad/memory/hw-shared/reviews/{plan-name}-performance.md

审查重点:
- N+1 查询: 循环中的数据库查询
- 内存使用: 大对象、缓存策略、泄漏风险
- 算法复杂度: 是否有低效的算法或数据结构
- 并发性能: 锁争用、goroutine 泄漏、连接池
- 扩展性: 架构是否支持负载增长

严重程度: P0-P3 (同上)
```

### Step 4: 处理审查结果

审查完成后，读取每个审查报告并处理:

#### 结果分类

```
Logic Review:   P0: 0, P1: 1, P2: 2, P3: 3 → VERDICT: REJECT (有 P1)
Security Review: P0: 0, P1: 0, P2: 0, P3: 1 → VERDICT: APPROVE (无 P0/P1/P2)
Performance Review: P0: 0, P1: 0, P2: 0, P3: 0 → VERDICT: APPROVE
```

#### VERDICT 判定规则

| 条件 | VERDICT |
|------|---------|
| P0 > 0 | REJECT -- 致命问题，必须修复 |
| P1 > 0 | REJECT -- 严重问题，必须修复 |
| P2 > 0 | REJECT -- 一般问题，必须修复 |
| 仅 P3 > 0 | APPROVE -- P3 建议，记录但不阻塞 |
| 无任何问题 | APPROVE |

#### 修复 REJECT 的审查

如果任何审查者的 VERDICT 是 REJECT:

1. **收集所有审查者的问题，按优先级和关联性分组**
2. **委托修复 P0/P1/P2 问题**（使用 task_id 重用 session）
3. **修复后重新运行该审查者**（仅运行报告了问题的审查者，不是全部）
4. **循环直到所有审查者 VERDICT 都是 APPROVE**

示例修复委托:
```
任务: 修复 Logic Review 发现的 P1 问题
问题: [引用具体问题描述和位置]
修复: [具体修复指示]
这些修复不能破坏之前通过的审查结果。只修改必要的代码。
```

#### P3 问题的处理

P3 (建议) 不阻塞 APPROVE:
- 记录到 `issues.md` 和审查报告中
- 不委托修复
- 在计划完成后的人工审查阶段由人工决定是否采纳

### Step 5: 审批关卡

```
ALL REVIEWERS APPROVE?
    │
    ├── YES → 报告计划完成
    │
    └── NO (至少一个 REJECT)
        │
        ├── 收集 REJECT 问题
        ├── 委托修复
        ├── 重新运行 REJECT 的审查者
        └── 循环直至全部 APPROVE
```

**最多 3 轮修复循环。** 如果 3 轮修复后仍有审查者 REJECT：
- 记录剩余问题到 problems.md
- 报告完成状态: COMPLETED_WITH_CONCERNS
- 详细说明哪些审查通过、哪些仍有问题、每个剩余问题的严重程度

## 完成报告

### 全部 APPROVE

```
============================================
ORCHESTRATION COMPLETE - FINAL WAVE PASSED
============================================

Plan: {plan-name}
Location: {project-root}/_bmad/memory/hw-shared/plans/{plan-name}.md

TASKS COMPLETED: N/N

FINAL VERIFICATION WAVE:
  Logic Review:      APPROVE (P0:0 P1:0 P2:0 P3:{n})
  Security Review:   APPROVE (P0:0 P1:0 P2:0 P3:{n})
  Performance Review: APPROVE (P0:0 P1:0 P2:0 P3:{n})

FILES MODIFIED:
  {文件列表}

NOTEPAD:
  {project-root}/_bmad/memory/hw-plan-executor/notepads/{plan-name}/

REVIEW REPORTS:
  {project-root}/_bmad/memory/hw-shared/reviews/{plan-name}-logic.md
  {project-root}/_bmad/memory/hw-shared/reviews/{plan-name}-security.md
  {project-root}/_bmad/memory/hw-shared/reviews/{plan-name}-performance.md
============================================
```

### 部分 REJECT (3 轮后仍有问题)

```
============================================
ORCHESTRATION COMPLETE - WITH CONCERNS
============================================

Plan: {plan-name}
TASKS COMPLETED: N/N

FINAL VERIFICATION WAVE (after 3 fix rounds):
  Logic Review:      APPROVE
  Security Review:   APPROVE
  Performance Review: REJECT
    Remaining: P1 x1 ({问题描述}), P2 x2 ({问题描述})

See problems.md for details on unresolved issues.
Recommendation: {建议人工审查 Performance Review 的剩余问题}
============================================
```

## 审查报告位置

所有审查报告写入共享审查目录:

```
{project-root}/_bmad/memory/hw-shared/reviews/
├── {plan-name}-logic.md
├── {plan-name}-security.md
└── {plan-name}-performance.md
```

## Final Verification Wave 的边界

### 审查范围

- 审查覆盖本次计划修改/创建的所有文件
- 审查者可能发现不在修改文件中的问题 → 记录为 P3 建议
- 审查者不应建议超出计划范围的重大架构变更

### 审查者的独立性

- 审查者之间不通信
- 审查者不修改代码
- 审查者只产出审查报告

### 与任务验证的区别

| 维度 | 任务验证 (Phase A-D) | Final Verification Wave |
|------|---------------------|------------------------|
| 执行者 | hw-plan-executor (你) | hw-reviewer-* agents |
| 粒度 | 单任务 | 全计划 |
| 关注点 | 任务是否正确实现 | 跨任务的质量和一致性 |
| 时机 | 每个委托完成后 | 所有实现任务完成后 |
