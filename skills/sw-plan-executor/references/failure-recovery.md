# Failure Recovery: 失败恢复策略

## 核心原则

**使用 task_id 恢复，永不重新开始。** 子 agent 的 session 包含所有上下文——已读取的文件、尝试过的方案、遇到的错误。重新开始会抹掉这些，浪费 70%+ 的 token。

## 失败分类

### 类型 1: 构建/编译失败

**症状:** `go build` / `npm run build` / `cargo build` 返回非零 exit code

**恢复策略:**
1. 读取编译错误输出
2. 识别根本原因（类型错误、缺少导入、语法错误等）
3. 使用同一个 session (task_id) 委托修复:
   ```
   "Build failed: {具体错误信息}。修复这个编译错误。"
   ```
4. 如果由简单的 typo 导致（如拼写错误），可以尝试 2 次
5. 如果是根本性的类型或架构问题，立即报告

### 类型 2: 测试失败

**症状:** 测试不通过或 test runner 报错

**恢复策略:**

**测试断言失败 (期望 vs 实际不匹配):**
1. 检查是代码逻辑问题还是测试本身的问题
2. 如果是代码问题 → 修复代码
3. 如果测试的期望错了 → 修复测试
4. 重试最多 3 次

**测试编译/导入失败:**
1. 通常是依赖或导入问题
2. 检查导入路径和依赖是否可用

**测试超时:**
1. 检查是否有死循环或阻塞操作
2. 增加超时时间或修复阻塞

**恢复委托示例:**
```
"Verification Phase A failed: 3 tests failing in src/api/auth/register_test.go:
  - TestRegister_WeakPassword: expected 400 but got 500 (test line 45)
  - TestRegister_EmptyBody: expected 400 but got 500 (test line 67)
  - TestRegister_Success: server panic at handler.go:32 nil pointer dereference

Root cause: handler.go:32 accesses request body without checking for nil.

Fix: Add nil check for request body before JSON decoding. Fix the handler, all three tests should pass."
```

### 类型 3: LSP 诊断错误

**症状:** lsp_diagnostics 报告 errors

**恢复策略:**
1. 读取诊断输出，识别错误位置和类型
2. 区分真正的错误 vs 项目已有的噪声警告
3. 仅修复本次修改引入的新错误

### 类型 4: Phase B 审查发现质量问题

**症状:** 代码逻辑正确 (Phase A 通过) 但质量不达标

**恢复策略:**
1. 指出具体的问题位置和性质
2. 如果问题轻微（命名、格式）→ 委托修复 (相同 session)
3. 如果问题严重（缺少错误处理、逻辑漏洞）→ 委托修复 + 补充测试
4. 如果是模式不匹配但功能正确 → 记录到 issues.md，不阻塞

**恢复委托示例:**
```
"Code review found issues in src/api/auth/login.go:

1. Line 34: Password comparison is case-sensitive but should be case-insensitive per spec
2. Line 56: Missing error handling for database.QueryRow -- can return sql.ErrNoRows
3. Line 78-95: Token generation logic duplicates the same code in register.go:80-97
   - Should extract shared token generation to src/core/auth/token.go

Fix all three issues. Extract duplicate code, don't duplicate it."
```

### 类型 5: Phase C 运行时验证失败

**症状:** 实际运行应用时发现问题 (curl 返回错误、浏览器页面崩溃等)

**恢复策略:**
1. 收集具体的运行时错误信息 (status code, error message, stack trace)
2. 识别是代码问题还是环境问题 (数据库未启动、端口被占用等)
3. 如果是环境问题 → 解决环境问题，重试验证
4. 如果是代码问题 → 委托修复 (相同 session)

### 类型 6: 子 Agent "假完成"

**症状:** 子 agent 声称完成但代码实际不完整或有 stub

**恢复策略:**
1. 指出具体的遗漏: "You claimed to implement X but the code has a TODO at line 42"
2. 要求完成遗漏的工作
3. 在 MUST NOT DO 中特别强调: "All TODO comments must be resolved"

**恢复委托示例:**
```
"Verification failed: Subagent claimed task complete but found:

1. src/api/auth/refresh.go:89 -- '// TODO: implement token blacklist check'
   Token refresh MUST verify the token is not blacklisted before issuing a new one.
   
2. src/api/auth/refresh_test.go -- only covers happy path
   Missing test: expired refresh token, blacklisted refresh token, malformed token

3. src/models/refresh_token.go -- the 'ExpiresAt' field exists but is never set
   Must set ExpiresAt = time.Now().Add(7*24*time.Hour) when creating refresh token

Fix all three. Remove ALL TODO comments from production code."
```

## 重试策略

### 重试规则

| 规则 | 说明 |
|------|------|
| 最大重试次数 | 每个任务 3 次 |
| 同 session 重试 | 使用 task_id 恢复同一 session |
| 重试变化 | 每次重试必须有具体的新指示，不只 "再试一次" |
| 重试间隔 | 无间隔 -- 立即重试 |
| 重试失败 | 3 次失败后放弃，标记 BLOCKED |

### 正确的重试方法

```
// CORRECT: task_id 恢复同一 session

// 第一次委托
Delegate task to sw-tdd-agent:
  prompt = "实现用户注册 API..."
  Result: task_id="ses_abc123", status=completed

// 验证发现失败 → 重试
Delegate (same session):
  task_id="ses_abc123"
  prompt = "Verification failed: go build error at register.go:45. Fix the import path."

// 第二次验证仍失败 → 继续同 session
Delegate (same session):
  task_id="ses_abc123"
  prompt = "Still failing: nil pointer at register.go:67. Add nil check before accessing request.Body."
```

### 错误的重试方法

```
// WRONG: 不使用 task_id，重新开始

Delegate task to sw-tdd-agent:
  prompt = "实现用户注册 API..."
  Result: session="ses_abc123"

// 验证失败，但新开一个 session
Delegate task to sw-tdd-agent:
  prompt = "The register API build failed. Fix it. The code is in src/api/auth/register.go."
  // WRONG: 新 session 不知道之前做了什么，需要重复所有上下文
```

### task_id 恢复的优势

1. **Token 节省 70%+**: 不需要重新读取所有文件、不需要重新解释上下文
2. **上下文连续**: 子 agent 知道之前的尝试、失败原因、当前状态
3. **修复更精准**: 直接针对问题修复，不需要重新理解整个任务

## 放弃和标记 BLOCKED

### 放弃条件

同一任务使用同一 session 重试 3 次后仍失败 → 放弃该任务。

### 放弃流程

1. **不再重试** - 3 次已是最多
2. **记录到 problems.md**:
   ```markdown
   ### P{x}: 任务 task-{n} 放弃
   - 时间: 2026-05-10 15:30
   - 任务: {任务描述}
   - 失败尝试:
     1. {方法 1}: {结果}
     2. {方法 2}: {结果}
     3. {方法 3}: {结果}
   - 当前状态: {代码的当前状态}
   - 影响: {哪些下游任务受影响}
   - 所需行动: {需要什么才能解除阻塞}
   ```
3. **标记为 BLOCKED** - 在计划文件中将任务标记为 BLOCKED (如果支持)
4. **评估下游影响**:
   - 依赖该任务的下游任务 → 标记为 BLOCKED_BY_DEPENDENCY
   - 不依赖该任务的任务 → 继续执行

### 波次完成后的重试

当前波次所有独立任务完成后 (包括部分放弃的任务):

1. 回顾 problems.md 中的放弃任务
2. 利用累积的学习 (learnings.md, decisions.md, issues.md) 重新评估
3. 如果新的知识可能解决之前的问题 → 尝试 1 次额外修复
4. 如果仍然失败 → 保持 BLOCKED，继续下一波次

**波次完成后重试示例:**
```
"Previously abandoned task task-2 (登录 API) was blocked by JWT import issue.
We now know (from learnings.md added by task-3):
  - JWT library is at github.com/golang-jwt/jwt/v5, not github.com/dgrijalva/jwt-go
  - Import path pattern: github.com/golang-jwt/jwt/v5

Try task-2 one more time with this corrected knowledge."
```

## 升级到 sw-controller

### 必须升级的情况

1. **跨计划依赖**: BLOCKED 的任务依赖另一个计划的产出
2. **基础设施问题**: 数据库、Consul、网络等基础设施不可用
3. **3 个以上任务 BLOCKED**: 计划大面积阻塞
4. **数据丢失风险**: 继续执行可能覆盖或破坏已有数据
5. **架构决策冲突**: notepad 中的决定与项目现有架构冲突

### 升级模板

```
ESCALATION TO sw-controller

From: sw-plan-executor
Plan: {plan-name}
Progress: {completed}/{total} tasks completed, {n} BLOCKED

Blocked Tasks:
  - task-{id}: {任务描述} -- 3 次重试失败
    原因: {根本原因}
  - task-{id}: {任务描述} -- 被 task-{x} 阻塞
    原因: 上游 BLOCKED
  - task-{id}: {任务描述} -- 外部依赖不可用
    原因: {具体问题}

Notepad: {project-root}/_context/memory/sw-plan-executor/notepads/{plan-name}/

What we need from sw-controller:
  {具体的所需行动}

Continue without blocked tasks? {YES/NO, 理由}
```

## 预防性措施

### 在委托提示中预防失败

良好的委托提示可以预防大部分失败。确保:

1. **MUST DO** 中明确写出质量要求
2. **MUST NOT DO** 中明确禁止常见错误
3. **CONTEXT** 中的 Inherited Wisdom 包含已知陷阱
4. **EXPECTED OUTCOME** 中的验证命令准确

### 在验证中尽早发现失败

及时的验证可以防止小问题变成大问题:

1. 每个委托后立即验证 (Phase A → Phase B → Phase C → Phase D)
2. 不累积验证 → 不等到波次结束时批量验证
3. Phase A 失败的成本远低于 Phase C 失败的成本

### 从失败中学习

每次失败后更新 notepad:
- **issues.md**: 记录问题和解决方案
- **learnings.md**: 记录发现的新模式或约定

下次委托的 Inherited Wisdom 会包含这些知识，避免重复同样的错误。
