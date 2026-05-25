# Intent Analysis: Mid-sized Task (中型任务)

## 核心挑战

Mid-sized Task 是**最常见的意图类型**，也是 **AI-slop 最常发生的场景**。因为任务"中等"——既不是简单到不会出错，也不是复杂到 AI 会谨慎。在这个舒适区，AI 最容易放松边界意识，自动扩展范围。

核心原则: **定义精确边界，然后死守边界。**

## Phase 1: 边界定义 (Boundary Definition)

### 边界维度

对于每个中型任务，必须定义以下五个维度的边界:

| 边界维度 | 定义 | 示例 |
|----------|------|------|
| **File Boundary** | 哪些文件可以被修改? | `src/auth/login.ts`, `src/auth/session.ts` — 不能触及 `src/payment/` |
| **Module Boundary** | 哪些模块/包可以被修改? | `auth` 模块 — 不能修改 `user` 或 `payment` 模块 |
| **Interface Boundary** | 哪些公开接口可以被修改? | 只能修改 `login()` 内部实现 — 不能改 `login()` 签名 |
| **Behavior Boundary** | 哪些行为必须保持不变? | 登录失败返回 401 — 不能改为 403 |
| **Dependency Boundary** | 可以新增什么依赖? | 不新增任何第三方依赖 — 或只能新增 `bcrypt` |

### 边界检测启发式

从用户请求中提取边界信息:

```
用户说: "Add rate limiting to the login endpoint"
↓
File Boundary: src/auth/login.ts (+ possibly src/middleware/rate-limit.ts)
Module Boundary: auth 模块 (+ possibly middleware 模块)
Interface Boundary: login() 签名不变，返回可能新增 429 状态码
Behavior Boundary: 登录成功行为和失败行为不变，新增频率超限行为
Dependency Boundary: 可能需要一个 rate-limiting 库，或不新增依赖而自己实现
```

### 边界模糊时的处理

如果请求未明确边界:

```
"这个变更的精确范围是什么?
 
 具体来说:
 - 是否只能修改 auth 模块的代码? 还是可以扩展 middleware 基础设施?
 - 是否需要保持 login endpoint 的响应时间不变 (新增的 rate limit 检查不应
   显著增加延迟)?
 - 是否需要支持配置化的 rate limit 规则? 还是硬编码即可?"
```

## Phase 2: AI-Slop 防护 (四大防护)

### 防护 1: Scope Inflation (范围膨胀)

**AI 的典型行为**: 看到相关问题时自动扩展任务范围。
**检测**: 请求中存在 "also"、"additionally"、"while we're at it"、隐含的关联变更。

**针对 rate limiting 示例的膨胀检测**:
- "While adding rate limiting, also normalize error response format" ← 膨胀
- "The auth module could also use better logging" ← 膨胀
- "Rate limiting should be configurable per-endpoint and per-user-type" ← 可能是膨胀

**Counter-Directive**:
```
MUST NOT modify files outside the defined [File Boundary].
MUST NOT refactor or "clean up" unrelated code in the target files.
If a change touches files outside the boundary, STOP and ask for scope confirmation.
```

### 防护 2: Premature Abstraction (过早抽象)

**AI 的典型行为**: 为一个具体用例创建通用抽象层。
**检测**: 请求涉及 "可配置"、"可扩展"、"通用" 但只有一个具体使用场景。

**针对 rate limiting 示例的抽象检测**:
- "Create a generic rate-limiting middleware" ← 只有一个 login endpoint 需要
- "Support pluggable rate-limit backends (Redis, Memcached, in-memory)" ← 只有一个场景
- "Design a rule DSL for rate limit configuration" ← 过度设计

**Counter-Directive**:
```
MUST implement the simplest solution that solves the immediate problem.
MUST NOT introduce abstraction layers unless explicitly required.
SHOULD solve for ONE concrete use case before generalizing.
MAY add an Architecture Decision Record documenting how the solution can be
generalized later, WITHOUT implementing the generalization.
```

### 防护 3: Over-Validation (过度验证)

**AI 的典型行为**: 在核心功能实现前就试图处理所有边界情况和异常路径。
**检测**: 请求中包含详尽的验证/错误处理需求，或请求 "handle all edge cases"。

**针对 rate limiting 示例的过度验证检测**:
- "Must validate all possible invalid IP formats" ← 过度 (IPv6, IPv4-mapped, etc.)
- "Must handle the case where Redis is reconnecting during a rate limit check" ← 过度
- "Must log every rate limit decision with structured metadata" ← 可能是过度

**Counter-Directive**:
```
MUST implement happy path + critical error paths first.
MUST only handle error cases that can occur under normal operation.
SHOULD treat edge-case handling as P2 follow-up tasks, not blockers.
MAY add TODO comments for known unhandled edge cases.
```

### 防护 4: Documentation Bloat (文档膨胀)

**AI 的典型行为**: 为相对小的变更加入过多文档、注释、类型定义。
**检测**: 请求中要求面向多受众的文档，或要求 "comprehensive documentation"。

**Counter-Directive**:
```
MUST document the what and why of the change in the commit message.
MUST update API documentation IF the API surface changes.
MAY add inline comments for non-obvious logic only.
SHOULD NOT create standalone design docs for mid-sized changes unless requested.
```

## 应问的问题

1. **边界定义** (必问 — 如果边界模糊):
   ```
   "这个变更的精确边界是? 
   - 限定文件: [从请求中提取] 
   - 是否只能修改这些文件? 还是相关的 infrastructure 代码也可以动?"
   ```

2. **完成标准** (必问):
   ```
   "什么表示任务完成?
   - 功能可用 (happy path working)?
   - 功能可用 + 测试覆盖 (happy + error paths)?
   - 功能可用 + 测试覆盖 + 文档更新?"
   ```

3. **限时约束** (如果可能涉及 scope inflation):
   ```
   "这个任务是否应该限定在一个时间盒内?
   - 例如: 最多 N 小时/天，超过则拆分任务"
   ```

## Planner Directives for Mid-sized Task Intent

### MUST 指令

```
MUST stay within the defined [File Boundary] — no modifications to files outside this list.
MUST NOT change public API signatures unless explicitly listed in the task definition.
MUST add tests that cover the new/changed behavior (happy path + critical error path).
MUST NOT refactor unrelated code in the target files (separate refactoring tasks for that).
MUST NOT introduce new dependencies without explicit authorization.
```

### SHOULD 指令

```
SHOULD implement the simplest approach first — optimize only if measurements show a problem.
SHOULD limit changes to <N> files (where N is derived from the request scope).
SHOULD keep each commit focused on a single logical change.
```

### MAY 指令

```
MAY flag additional improvements as TODO comments rather than implementing them.
MAY document design decisions inline rather than in separate design docs.
```

## QA / Acceptance Criteria for Mid-sized Task

1. **[Test Command]** 新功能测试通过:
   ```
   验证命令: <test-command> --filter="<new-feature-tests>"
   预期: 所有新功能测试通过
   ```

2. **[Test Command]** 回归测试通过:
   ```
   验证命令: <test-command> --filter="<related-existing-tests>"
   预期: 所有已有测试仍通过，无回归
   ```

3. **[Static Analysis]** 未触及边界外文件:
   ```
   验证命令: git diff --name-only HEAD~1
   预期: 变更文件列表完全在定义的 File Boundary 内
   ```

4. **[Lint Rule]** 无新增 lint 错误:
   ```
   验证命令: <lint-command> <changed-files>
   预期: 0 新增 lint 警告或错误
   ```

5. **[Script]** 功能验证 (端到端):
   ```
   根据任务类型定制:
   - API 变更: curl 脚本验证新端点和已有端点
   - UI 变更: 自动化截图对比或 DOM 断言
   - 性能变更: benchmark 脚本比较前后指标
   ```

## 范围拆分指引

如果中型任务过大的迹象:
- 涉及超过 5 个文件
- 涉及超过 2 个模块
- 用户问题超过 5 个仍不够清晰

建议拆分为更小的任务:
```
"这个任务可能需要拆分为几个小任务:
 1. [核心变更] - [范围]
 2. [测试] - [范围]
 3. [集成验证] - [范围]
 是否按这个顺序推进?"
```
