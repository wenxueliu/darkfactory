# 失败升级协议 (Failure Escalation)

## 核心原则

Agent 应自主解决大部分问题。升级是**最后手段**，不是首选方案。

升级之前的默认假设是：**我能自己解决这个问题。**

## 3 次连续失败规则 (Three-Consecutive-Failures Rule)

同一个障碍如果连续 3 次尝试仍未克服，**必须**升级。

### 什么是"同一个障碍"

- 同一个测试连续 3 次尝试后仍然失败
- 同一个 VERIFY 错误（diagnostics / build / test）连续 3 次出现
- 同一个信息缺口在探索层次 Level 1-4 穷尽后仍未填补

### 什么是"不同尝试"

每次重试必须与之前**实质性不同**：

```
# 同一尝试的不同变体 → 不算
Attempt 1: 用 sleep(1) 等待异步完成 → FAIL
Attempt 2: 用 sleep(2) 等待异步完成 → FAIL  ← 不算，同一个方法
Attempt 3: 用 sleep(5) 等待异步完成 → FAIL  ← 不算，同一个方法

# 实质性不同的尝试 → 算
Attempt 1: 用 sleep() 等待异步完成 → FAIL
Attempt 2: 用 polling + timeout 等待 → FAIL  ← 算，不同方法
Attempt 3: 用 event-driven callback  → SUCCESS ←✓
```

### 3 次规则的状态跟踪

```
Iteration 1: 尝试方法A → 失败
  ↓
  分析失败原因，制定方法B
  ↓
Iteration 2: 尝试方法B → 失败
  ↓
  分析失败原因，制定方法C
  ↓
Iteration 3: 尝试方法C → 失败
  ↓
  升级到 strategic-advisor（附带 3 次尝试记录）
```

## 升级前必须尝试的方案

在说"我做不了"之前，按以下顺序穷尽所有选项：

### 1. 尝试不同的方法 (Try a Different Approach)

- 如果直接调用 API 失败 → 尝试通过 client library
- 如果 mock 导致问题 → 尝试 integration test
- 如果同步方案不工作 → 尝试异步方案
- 如果 eager loading 有性能问题 → 尝试 lazy loading
- 如果 eager initialization 有时序问题 → 尝试 lazy initialization

### 2. 分解问题 (Decompose the Problem)

- 大功能拆成小功能 → 逐个实现
- 复杂逻辑拆成简单步骤 → 逐个验证
- 多依赖一起处理 → 逐个消除依赖
- 如果整个测试写不出来 → 先写一个最小的、最trivial的测试

**示例:**
```
问题: "我无法实现完整的用户权限系统"
分解:
  1. 先实现单一角色检查（忽略 hierarchy）
  2. 再实现角色继承
  3. 再实现权限颗粒度
  → 至少可以先完成第1步，不是完全阻塞
```

### 3. 挑战假设 (Challenge Your Assumptions)

自问：
- 我假设需要做 X——真的需要吗？有没有更简单的方式？
- 我假设现有代码不支持 Y——我确实确认过吗？还是推测的？
- 我假设这个库/框架不能做 Z——看过文档吗？还是凭经验判断的？
- 我假设这个问题必须现在解决——能不能在 GREEN 阶段绕过，在 REFACTOR 阶段再处理？

### 4. 研究他人方案 (Research How Others Solved It)

- 搜索代码库中类似问题的已有实现
- 启动外部研究 agent 查找最佳实践
- 查阅参考项目的类似模块
- 查看 `_context/memory/sw-shared/knowledge-base/patterns/` 中的已有模式

## 升级触发条件汇总

满足以下**任一**条件时，执行升级：

| 条件 | 信号 |
|------|------|
| 连续失败 | 同一障碍 3 次实质性不同尝试均失败 |
| 信息缺失 | 探索层次 Level 1-4 全部穷尽，仍缺少关键信息 |
| 架构决策 | 变更涉及跨模块 API contract 修改，超出 tdd-agent 决策范围 |
| 需求模糊 | 任务定义不清晰，多次推断导致返工，且 Level 1-4 无法澄清 |
| 依赖阻塞 | 工作依赖其他 agent/服务/团队的输出，目前不可用 |
| 环境问题 | 测试框架、构建工具、或开发环境损坏，修复超出 tdd-agent 能力 |
| 安全/数据风险 | 操作可能造成数据丢失、安全漏洞或不可逆破坏 |

## 升级消息格式

升级到上层 agent（strategic-advisor 或 worktree-controller）时，必须包含以下信息：

```markdown
## 升级: {问题简述}

### 当前任务
- Task: {task name from tasks.yaml}
- Phase: {explore/plan/decide/execute/verify}
- 已完成: {what's done so far}

### 阻塞问题
{具体描述：什么阻塞、为什么阻塞}

### 已尝试的方案
1. **方法A:** {简述} → 结果: {失败原因}
2. **方法B:** {简述} → 结果: {失败原因}
3. **方法C:** {简述} → 结果: {失败原因}

### 已探索的信息来源
- [x] Direct tools (grep/read/glob): {关键发现}
- [x] Codebase exploration: {关键发现}
- [x] External research: {关键发现}
- [x] Context inference: {推断结论}
- [ ] User inquiry: 尚未询问

### 当前状态
- 代码状态: {working / partially working / broken}
- 测试状态: {X/Y PASS, Z failures}
- 文件状态: {已修改但未提交 / 未修改}

### 我的建议
我倾向于方案{D}，原因是{理由}。

### 需要什么
{具体需要上层 agent 提供什么：决策、信息、权限、协调}
```

## 升级消息示例

```markdown
## 升级: API Layer 的 auth middleware 测试无法通过

### 当前任务
- Task: implement-user-auth
- Phase: EXECUTE (Layer 2 API, GREEN phase)
- 已完成: Layer 1 UT 全部通过 (15/15 PASS)，API RED 阶段完成

### 阻塞问题
POST /api/auth/login 的 API 测试依赖 auth middleware，该 middleware 需要
读取 Consul KV 中的 JWT secret。当前开发环境 Consul 不可用，测试因连接
超时而失败。

### 已尝试的方案
1. **Mock Consul client:** 但 auth middleware 在框架层实例化 Consul client，
   无法通过依赖注入替换。 → 结果: 需要修改框架层，超出当前任务范围。
2. **使用环境变量绕过 Consul:** 框架代码不检查环境变量 fallback。 → 结果:
   同样需要修改框架层。
3. **直接测试 endpoint handler（跳过 middleware）:** handler 在 deep module
   中，不对外暴露。 → 结果: 需要修改模块导出，影响多个下游模块。

### 已探索的信息来源
- [x] Direct tools: 已读取 auth middleware 源码、Consul client 源码
- [x] Codebase exploration: 已追踪依赖链：handler → middleware → consul_client
- [x] External research: N/A（内部架构问题）
- [x] Context inference: 框架层设计时未考虑测试可替换性
- [ ] User inquiry: 尚未询问

### 当前状态
- 代码状态: Layer 1 代码完成但未提交。Layer 2 测试文件已创建。
- 测试状态: UT 15/15 PASS。API 0/5 PASS（环境问题）。
- 文件状态: 未修改（仅在 worktree）

### 我的建议
建议方案：在 auth middleware 中添加可选的 `JWT_SECRET` 环境变量 fallback。
这是最小的框架层改动（约 5 行），向后兼容，不影响生产行为。
如果同意，我可以在 10 分钟内完成框架层修改并继续 API 测试。

### 需要什么
批准修改框架层的 auth middleware 以支持环境变量 fallback。
```

## 禁止的升级方式

```markdown
# BAD — 信息不足，没有展示自主尝试
"我卡住了，auth 测试跑不了。怎么办？"

# BAD — 过早升级，没有尝试自行解决
"auth middleware 需要 Consul，Consul 不可用，所以我无法继续。"
// 当 agent 说这个的时候，它应该已经尝试过 mock、环境变量、绕过等方式

# BAD — 把决策推给用户
"我应该修改 auth middleware 来绕过 Consul，还是 mock 整个框架层？"
// agent 应该给出建议，不是让用户二选一
```

## 升级后的行为

1. 发送升级消息后，**停止当前工作**，等待上层 agent 回复
2. 保持 worktree 状态不变（不提交、不重置、不切换分支）
3. 收到回复后，根据指示继续执行
4. 如果 30 分钟内无回复，恢复自主工作模式，选择风险最小的路径继续

## 不应升级的情况

以下情况**不允许**升级，应自行处理：

- 测试框架的具体用法不清楚 → 搜索代码库中的已有测试作为示例
- 不确定命名约定 → 从现有代码推断
- 不确定文件应该放在哪个目录 → 从项目结构推断
- 不确定错误消息应该怎么写 → 搜索项目中已有的错误消息风格
- 不确定应该用哪个测试断言 → 查看已有测试使用的断言模式
- 一次测试失败 → 分析失败原因，修复代码，重新运行（不算 3 次中的 1 次）
