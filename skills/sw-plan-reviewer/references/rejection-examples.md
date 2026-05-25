# RejectionExamples: 有效的拒绝示例

以下展示了**应该拒绝**的计划场景。注意：拒绝必须满足"真正阻塞工作"的标准。

---

## 示例 1: 引用的文件不存在

### 计划摘要

```markdown
## Task 2: 修改认证逻辑

修改 `src/auth/login.ts` 中的 `authenticateUser` 函数，添加 JWT token 刷新逻辑。
参照 `src/auth/refresh-token-pattern.ts` 中的模式实现。

## Task 3: 添加用户中间件

在 `src/middleware/auth-middleware.ts` 中使用新的 token 验证逻辑。
```

### 验证过程

1. 读取 `src/auth/login.ts` → 文件存在，第 35-60 行确实包含 `authenticateUser` 函数。PASS。
2. 读取 `src/auth/refresh-token-pattern.ts` → **文件不存在。**
3. 不存在的引用使任务 2 无法正确参照模式实现。同时该引用是任务的唯一模式指引。

### REJECT 输出

```
[REJECT]
Summary: 计划中 Task 2 引用的参照文件 `src/auth/refresh-token-pattern.ts` 不存在，开发者缺少关键的模式参照。

Blocking Issues (max 3):
1. Task 2 参照 `src/auth/refresh-token-pattern.ts`，但该文件不存在。需要提供该模式文件的路径，或在任务描述中直接包含 token 刷新的具体步骤说明。
```

---

## 示例 2: 任务完全无法开始（零上下文）

### 计划摘要

```markdown
## Task 4: 完善支付功能

Task 4 继续完善之前未完成的支付功能。

## Task 5: 修复问题

修复用户反馈的一些问题。
```

### 验证过程

1. Task 4: "完善支付功能"——没有文件路径，没有指出要完善什么，没有参照。开发者无从下手。
2. Task 5: "修复问题"——没有说明是哪些问题，没有引用任何 bug 报告或 issue，没有目标文件。

### REJECT 输出

```
[REJECT]
Summary: Tasks 4 和 5 缺少可执行性所需的最低信息——没有目标文件、没有具体做什么、没有任何起点线索。开发者无法开始工作。

Blocking Issues (max 3):
1. Task 4 "完善支付功能"未说明目标文件路径或待完善的具体内容。需指定至少一个目标文件路径和需要修改/添加的功能点。
2. Task 5 "修复问题"未引用任何问题来源（issue/bug 报告），也未说明目标文件。需列出具体的 bug 描述或关联的 issue 编号。
```

---

## 示例 3: 计划内部矛盾

### 计划摘要

```markdown
## 项目背景

本次重构将用户认证从 Session-based 迁移到 JWT-based。

## Task 1: 创建认证模块

创建 `src/auth/session.py`，实现基于 session 的认证中间件。

## Task 3: API 路由改造

修改所有 API 路由，从 session 验证改为从 `Authorization: Bearer` 头读取 JWT token。
```

### 验证过程

1. 项目背景说"迁移到 JWT"
2. Task 1 却说"创建基于 session 的认证中间件"——与背景矛盾
3. Task 3 说"从 session 验证改为 JWT"——但如果 Task 1 创建的是 session 中间件，Task 3 要从 session 改为 JWT，那 Task 1 产出的中间件一创建就要废弃
4. 开发者无法判断应该按背景还是按 Task 1 执行

### REJECT 输出

```
[REJECT]
Summary: Task 1 与项目背景矛盾——背景说迁移到 JWT，但 Task 1 要创建 session 认证中间件。开发者无法判断应遵循哪个方向。

Blocking Issues (max 3):
1. Task 1 创建 `src/auth/session.py`（session 认证中间件）与项目背景"迁移到 JWT"和 Task 3 "从 session 验证改为 JWT"矛盾。应统一为 JWT 路径：Task 1 创建 JWT 认证中间件（如 `src/auth/jwt_auth.py`），或者如果 session 中间件仍有保留必要，需在计划中明确说明保留原因和范围。
```

---

## 示例 4: QA 场景不可执行

### 计划摘要

```markdown
## Task 2: 实现用户列表 API

实现 `GET /api/users` 接口，支持分页和筛选。

QA:
- 手动在浏览器中访问页面，确认用户列表显示正常
- 确认筛选和分页工作正常
```

### 验证过程

1. QA 场景 1: "手动在浏览器中访问页面，确认用户列表显示正常"——没有具体 URL、没有预期数据、没有验证步骤。"显示正常"是主观判断。
2. QA 场景 2: "确认筛选和分页工作正常"——没有工具（curl? 测试?）、没有具体步骤（怎么筛选? 什么参数?）、没有预期结果。"工作正常"是主观判断。

这是一个不可执行的 QA 场景。

### REJECT 输出

```
[REJECT]
Summary: Task 2 的 QA 场景缺少可执行要素——没有具体工具、没有步骤、预期结果是主观的"正常"。

Blocking Issues (max 3):
1. Task 2 QA 场景不可执行："手动在浏览器中访问页面，确认用户列表显示正常"缺少具体 URL、预期响应数据和可验证的断言。应改为具体测试命令，如：`curl -s http://localhost:3000/api/users?page=1&limit=10 | jq '.data | length'` 预期输出 `10`。
```

---

## 关键区别：REJECT vs OKAY

| 场景 | 判定 |
|------|------|
| 文件不存在 | **REJECT** |
| 文件存在但内容一般 | **OKAY** |
| "完善功能" 零上下文 | **REJECT** |
| "完善功能：添加 validation" 有位置 | **OKAY** |
| 两个任务矛盾 | **REJECT** |
| 两个任务描述不够连贯 | **OKAY** |
| QA 场景：手动检查 | **REJECT** |
| QA 场景：curl 命令但预期不精确 (如 "expected JSON") | **OKAY** |
| 缺少整个任务的 QA 场景 | **REJECT** |
| QA 场景有 curl 但预期是 "确认没问题" | **REJECT**（预期主观） |
