# 探索与研究 (Exploration & Research)

参考: Sisyphus orchestrator DNA — oh-my-openagent Phase 2A 并行探索模式

## 核心理念

在执行非 trivial 的实现之前，必须通过并行探索充分理解现状。**默认并行，绝不串行等待。** 内部搜索 (codebase-explorer) 和外部搜索 (external-researcher) 总是同时启动，互不阻塞。

探索的目的是消除假设——你以为是这样的代码，实际上可能是那样的；你以为外部文档说的对的，实际版本可能已经不匹配。**不探索就开始实现 = 基于假设写代码。**

## 何时探索

以下情况必须触发探索：

| 触发条件 | 原因 |
|---------|------|
| 非 trivial 的代码库问题（不是 "X 文件在哪里" 这种单次 grep 能解决的） | 需要理解跨文件/跨模块的关系 |
| 不熟悉的模块/服务 | 不了解现有模式和约定 |
| 跨层改动（如从 API → Service → Repository 全链路） | 需要了解各层的实际实现状态 |
| 涉及到外部 API/库/框架的最新版本或文档 | 版本可能不匹配，需要验证 |
| Open-ended 任务的评估阶段 | 需要全面了解现状才能提案 |
| 修复 bug（诊断阶段） | 需要理解 bug 的影响范围 |

以下情况可以跳过探索：

| 跳过条件 | 原因 |
|---------|------|
| Trivial 任务（单文件、已知位置、<10 行改动） | 开销大于收益 |
| 上一 turn 刚探索过同一模块 | 信息仍然新鲜 |
| 项目为 Greenfield | 无现有代码可探索；只需外部研究 |

## 探索分工

### hw-codebase-explorer (内部搜索)

**职责:** 在当前代码库中搜索、分析、追踪代码关系

**典型问题:**
- "UserService 中认证相关的所有调用链"
- "找到所有使用 deprecated `getUser()` 方法的地方"
- "Order 模块的完整依赖关系和测试覆盖情况"
- "最近 3 个月修改过的文件中有哪些使用了旧的 error handling 模式"

**输入格式:**
```
TASK: 在代码库中搜索 {具体问题}
SCOPE: {搜索范围 — 目录/文件/模式}
DEPTH: {shallow — grep 级别 | medium — 调用链追踪 | deep — 跨模块影响分析}
```

### hw-external-researcher (外部搜索)

**职责:** 搜索外部文档、最新 API 规范、最佳实践、同类解决方案

**典型问题:**
- "Spring Boot 3.2 中 WebClient 的最佳实践"
- "gRPC 错误处理的最新推荐模式"
- "React 19 中 Server Components 与现有 Redux 的集成方式"

**输入格式:**
```
TASK: 搜索外部信息 {具体问题}
SOURCES: {官方文档 | GitHub issues | Stack Overflow | 技术博客}
VERSION: {目标版本号 — 确保搜索结果是针对正确版本的}
```

## 并行执行模式

### 默认: 双线并行

```
收到非 trivial 任务
  ├─ [并行启动] hw-codebase-explorer: 搜索代码库中的相关实现
  └─ [并行启动] hw-external-researcher: 搜索外部最佳实践/文档
      │
      ├─ 等待两个结果返回
      ├─ 内部结果 + 外部结果 → 综合
      └─ 基于综合结果决定实现策略
```

### 复杂场景: 多 Agent 并行 (2-5 个)

对于跨多个模块的复杂任务，可以同时启动多个探索 Agent：

```
收到跨 3 个微服务的改动需求
  ├─ [并行] hw-codebase-explorer #1: 搜索 user-service 认证逻辑
  ├─ [并行] hw-codebase-explorer #2: 搜索 order-service 订单状态机
  ├─ [并行] hw-codebase-explorer #3: 搜索 gateway 路由配置
  └─ [并行] hw-external-researcher: 搜索微服务间认证 token 传递最佳实践
      │
      └─ 收集所有结果 → 综合 → 实现决策
```

### 关键规则

1. **始终 background 运行** — 探索 Agent 在后台执行，不阻塞主流程
2. **绝不重复委托** — 不给两个 Agent 分配相同的搜索任务
3. **搜索任务必须互斥** — 每个 Agent 的搜索 scope 不重叠
4. **2-5 个 Agent 是合理范围** — 少于 2 个可能不够全面，多于 5 个可能产生冗余信息

## 后台执行与结果收集

### 启动模式

```
1. 同时启动所有探索 Agent (2-5 个)
2. 每个 Agent 分配到后台运行
3. 主流程有两种选择:
   A. 如果有非重叠的工作 → 继续执行不依赖搜索结果的部分
   B. 如果没有非重叠的工作 → 结束当前 response，等待搜索结果
```

### 结果收集模式

```
当所有探索 Agent 返回后:
  1. 阅读每个 Agent 的结果
  2. 交叉验证: 内部搜索和外部搜索的结论是否一致？
  3. 识别差距: 还有哪些信息缺失？
  4. 综合: 将分散的发现整合为一个完整的理解
  5. 根据综合结果决定下一步行动
```

### 搜索停止条件

以下条件满足时停止搜索，开始综合：

| 条件 | 说明 |
|------|------|
| 找到了明确的答案 | 不需要继续搜索 |
| 所有并行 Agent 已返回 | 收集结果进行综合 |
| 已经搜了 3 轮仍未找到 | 可能是问题本身有误，检查前提假设 |
| 搜索结果相互矛盾 | 标记矛盾点，综合时重点标注不确定性 |
| 信息已足够做出决策 | 即使不完美，足够推进即可——不要过度搜索 |

## 反重复规则 (Anti-Duplication)

```
❌ 错误做法:
  Agent A: "搜索 user-service 中所有认证相关的代码"
  Agent B: "搜索 user-service 中所有认证相关的代码"  ← 重复！

❌ 错误做法:
  Agent A: "搜索 user-service"
  Agent B: "搜索 user-service 中的 AuthController"  ← 范围重叠！

✅ 正确做法:
  Agent A: "搜索 user-service 中认证中间件的实现"
  Agent B: "搜索 user-service 中 token 刷新的实现"
  Agent C: "搜索 order-service 中权限检查的实现"
  ← 每个 Agent 搜索不同的、互斥的范围
```

## 探索质量检查清单

在开始实现之前，确认以下问题已有答案：

- [ ] 相关代码的实际结构是否与我的假设一致？
- [ ] 最近是否有相关模块的重构/改动？（git log）
- [ ] 是否有现成的模式/工具类可以复用？（内部搜索）
- [ ] 最新版本的外部依赖是否有 breaking changes？（外部搜索）
- [ ] 是否存在与我的改动冲突的并行工作？（检查其他 worktree）
- [ ] 测试覆盖情况如何？有哪些 characterization tests 可以参考？

## 与后续阶段的衔接

```
Phase 2A (Exploration) 完成:
  → 综合结果清晰 → Phase 2B (Implementation Planning) 或直接实现
  → 综合结果有矛盾 → 标记不确定性，保守实现（加更多 assertion/validation）
  → 关键信息仍然缺失 → 询问用户或等待更多上下文
  → 探索结果推翻了原始假设 → 回到 Phase 0 (Intent Gate) 重新评估
```
