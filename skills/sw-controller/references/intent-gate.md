# 意图门禁 (Intent Gate)

参考: Sisyphus orchestrator DNA — oh-my-openagent 的意图分类与路由协议

## 核心理念

每次激活时，在执行任何操作之前必须通过意图门禁。意图门禁的核心原则是：**不猜测、不假设、不跨 turn 携带模式**。每次收到新的输入，都当作全新的请求来评估。

意图门禁解决 3 个根本问题：
1. **表面形式 != 真实意图** —— "帮我看看这个" 可能是研究需求，也可能是修复 bug
2. **turn 间模式污染** —— 上一 turn 在 "实现模式"，不代表这一 turn 仍然要写代码
3. **模糊推进行动** —— 需求信息不足时直接开始执行，等于用错误的前提写代码

## 5 步执行流程

### 第 1 步: Verbalize Intent (意图口头化)

将表面形式映射为真实意图。用自己的话陈述对请求的理解。

```
用户说: "用户注册接口好像有点问题"
→ 意图口头化: "用户报告注册接口存在异常行为，想让我诊断并修复"

用户说: "能不能加个登录功能"
→ 意图口头化: "要求在现有系统中新增登录功能，涉及前后端实现"
```

**目的:** 在开始之前让用户确认你的理解是否正确。如果理解偏差，用户此时纠正成本为零。

**禁止:** 口头化后不等待确认就直接开始执行（针对 Ambiguous 或 Open-ended 类型）。

### 第 2 步: Classify Request Type (请求类型分类)

| 类型 | 描述 | 示例 | 路由决策 |
|------|------|------|---------|
| **Trivial** (简单) | 单文件、已知位置、<10 行改动 | "在 UserController 加个日志" | 直接执行，不委托 |
| **Explicit** (明确实现) | 明确的实现动词 + 具体范围——但需求未经澄清验证 | "实现 OrderService 的 createOrder 方法" | ideation (requirement-clarification 验证) → 规划 → 委托 |
| **Exploratory** (探索) | 理解某物如何工作 | "解释一下认证流程" | 并行搜索 → 综合 → 回答 |
| **Open-ended** (开放) | 无具体范围的重构/改进 | "优化代码质量" | 评估代码库 → 提案 → 等待确认 |
| **Ambiguous** (模糊) | 多个合理解读，或缺少关键信息 | "改一下那个接口" | 问 1 个精确问题，不猜测 |

**分类决策树:**

```
收到请求
├─ 是否只需要单文件 + 已知位置 + <10 行？
│   └─ YES → Trivial → 直接执行
├─ 是否有明确的实现动词 (implement/add/create) + 具体范围 (module/endpoint/component)？
│   └─ YES → Explicit → 需求澄清验证 → 规划 → 委托
├─ 是否以 "解释/如何工作/是什么" 开头？
│   └─ YES → Exploratory → 探索 → 回答
├─ 是否以 "重构/改进/优化/清理" 开头但无具体范围？
│   └─ YES → Open-ended → 评估 → 提案 → 等待
├─ 是否缺少关键信息或有 2+ 种合理解读？
│   └─ YES → Ambiguous → 问问题
└─ 默认: 假定为 Ambiguous → 问清楚再行动
```

### 第 3 步: Turn-Local Intent Reset (Turn 级意图重置)

**NEVER auto-carry "implementation mode" from prior turns.**

每个 turn 独立评估意图。上一个 turn 在执行代码实现，不代表这个 turn 仍然在实现模式。

```
反模式:
  Turn 1: 用户说 "实现 createOrder" → Agent 进入实现模式
  Turn 2: 用户说 "看看那个 model" → Agent 仍然在实现模式，去修改 model
  正确: Turn 2 用户可能在探索/理解，应重新分类为 Exploratory

正模式:
  Turn 2: 用户说 "看看那个 model"
  → 意图重置: 这可能是一个探索性请求 → 分类为 Exploratory
  → 回答: 展示 model 的结构和字段，不主动修改
```

**关键信号** — 出现以下触发词时，强制重新分类：
- "看看"、"查一下"、"了解" → 探索
- "你觉得"、"建议" → 评估
- "好像"、"似乎"、"有点" → 可能是 bug 报告
- "那个"、"这个" → 可能指向模糊（缺少具体名称）

### 第 4 步: Check for Ambiguity (模糊性检查)

以下任一情况成立，请求为模糊：
- 2+ 种合理解读（不同解读导致完全不同的行动路径）
- 缺少关键信息（如: 哪个文件？哪个服务？什么错误信息？）
- 设计看起来有问题（例如，要求在不该耦合的地方耦合）

**处理流程:**

```
模糊检测成立:
  1. 提出 1 个精确问题（不是 3 个，不是模糊的开放式问题）
  2. 问题格式: 指出不明确之处 + 给出 2-3 个选项让用户选择
  3. 等待用户回答
  4. 禁止: 猜测一个方向然后开始执行
```

**示例:**

```
用户: "改一下那个认证"
↓
意图口头化: "你提到要修改认证相关代码，但我不确定具体是指什么"
精确问题: "你希望我: A) 修改 Token 过期时间配置, B) 调整认证中间件的逻辑, C) 还是有其他具体的改动？"
```

### 第 5 步: Context-Completion Gate (上下文完备门禁)

**仅适用于实现类请求。** 只有以下 4 个条件全部满足时才能开始实现：

1. **明确的实现动词存在** — implement, add, create, build, 实现, 新增, 创建
2. **范围是具体的** — 具体的 module/endpoint/component，不是 "改一下系统"
3. **需求已通过澄清验证** — 表面明确不等于需求已澄清。澄清本身就是检查——必须通过 sw-requirements-clarifier 的 Substantiality Threshold
4. **没有阻塞性专家结果待返回** — 没有在等待 codebase-explorer 的搜索结果，没有在等待 external-researcher 的文档

**Explicit 不等于 "已澄清":** 即使请求有明确的实现动词和具体范围，也必须先通过需求澄清。需求澄清不是"澄清模糊需求"的工具，而是"验证表面明确度是否可信"的检查。

**门禁失败时的处理:**

| 缺失条件 | 处理 |
|---------|------|
| 缺少实现动词 | 询问: "你是想让我探索/理解，还是实际实现？" |
| 范围不具体 | 询问: "你希望改动哪个模块/服务的哪个具体部分？" |
| 需求未经过澄清 | 委托 sw-requirements-clarifier 执行 4 步澄清对话，直到 Substantiality Threshold 满足 |
| 专家结果待返回 | 等待 or 告知用户 "正在搜索 X，等结果返回后再开始实现" |

## 意图路由映射表 (完整)

| 表面形式 | 真实意图 | 路由 |
|---------|---------|------|
| "explain X", "how does Y work", "解释", "怎么工作" | Research/understanding | codebase-explorer + external-researcher (并行) → synthesize → answer |
| "implement X", "add Y", "create Z", "实现", "新增", "创建" | Implementation (explicit — requires clarification verification) | ideation (requirement-clarification) → plan → delegate or execute |
| "look into X", "check Y", "investigate", "看看", "查一下" | Investigation | codebase-explorer → report findings |
| "what do you think about X?", "你觉得", "建议" | Evaluation | evaluate → propose → wait for confirmation |
| "X is broken", "I'm seeing error Y", "有问题", "报错" | Fix needed | diagnose → fix minimally → verify |
| "refactor", "improve", "clean up", "重构", "优化", "清理" | Open-ended change | assess codebase → propose approach → wait for approval |
| "can you help with X", "帮我" | Ambiguous (缺具体动词) | 追问澄清 |
| "把那个改了", "改一下这个" | Ambiguous (代词指代不明) | 追问澄清 |
| "和上次一样处理", "跟上次类似" | Ambiguous (跨 turn 引用) | 追问澄清上次的具体内容 |

## 反模式 (Anti-Patterns)

### 反模式 1: 猜测意图

```
用户: "用户注册有点慢"
❌ Agent: 直接开始优化数据库查询、加缓存、改连接池...
✅ Agent: "你说注册慢，是指: A) 页面响应慢, B) 注册接口响应慢, C) 注册后的邮件发送慢？"
```

### 反模式 2: 跨 Turn 携带模式

```
Turn 1: 用户说 "实现 createOrder" → Agent 正确进入实现模式
Turn 2: 用户说 "我看了一下 response 格式"
❌ Agent: 继续实现模式 → "好的，我来改 response 格式"
✅ Agent: 重置意图 → "你是在探索 response 格式的现状，还是想修改它？"
```

### 反模式 3: 无明确请求时开始实现

```
用户: "我在想认证模块要不要加双因子"
❌ Agent: "好的，我来实现双因子认证..."
✅ Agent: "这是一个评估性讨论。需要我先调研现有认证架构，然后给出双因子认证的集成方案建议吗？"
```

### 反模式 4: 同时问多个问题

```
用户: "看起来有问题"
❌ Agent: "什么问题？哪个服务？什么环境？错误信息是什么？有日志吗？"
✅ Agent: "能描述一下具体看到了什么错误信息吗？"
```

## 与后续阶段的衔接

意图门禁通过后，根据分类进入对应阶段：

```
Trivial    → 直接执行，不经过后续阶段
Explicit   → ideation (requirement-clarification) → Phase 1 (Codebase Assessment) → Phase 2A (Exploration) → 实现
Exploratory → Phase 2A (Exploration) → 综合回答
Open-ended → Phase 1 (Codebase Assessment) → 提案 → 等待确认
Ambiguous  → 追问澄清 → 重新进入意图门禁
Fix needed → 诊断 → Phase 2C (Failure Recovery) → 修复 → 验证
```
