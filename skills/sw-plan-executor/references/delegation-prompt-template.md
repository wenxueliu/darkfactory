# Delegation Prompt Template: 6-Section 委托提示模板

## 核心规则

**每个委托提示必须包含全部 6 个 section。如果提示不足 30 行，则太短了。**

## 6-Section 结构

```
## 1. TASK
[从计划文件中精确引用任务描述。极其具体，不概括。]

## 2. EXPECTED OUTCOME
- [ ] Files created/modified: [精确的文件路径列表]
- [ ] Functionality: [精确行为描述]
- [ ] Verification: `[验证命令]` exits clean

## 3. REQUIRED TOOLS
- [工具]: [要搜索/检查什么]
- [工具]: [查找什么库/文档]
- [工具]: `[具体命令或 pattern]`

## 4. MUST DO
- 遵循 [参考文件:行号] 中的模式
- 为 [具体场景] 编写测试
- 将发现追加到 notepad (从不覆盖)

## 5. MUST NOT DO
- 不要修改 [范围之外] 的文件
- 不要添加新依赖
- 不要跳过测试验证

## 6. CONTEXT
### Notepad Paths
- READ: {project-root}/_bmad/memory/hw-plan-executor/notepads/{plan-name}/*.md
- WRITE: 追加到对应的分类文件

### Inherited Wisdom
[从 notepad 中提取的累积智慧]

### Dependencies
[之前任务产出的内容和位置]
```

## 完整示例 1: 后端 API 任务

```
## 1. TASK

实现用户注册 API:
- POST /api/auth/register
- 接收 email + password 作为 JSON body
- 验证 email 格式和 password 强度
- 密码 bcrypt 哈希后存储到 PostgreSQL users 表
- 返回 JWT access token (有效期 1h) + refresh token (有效期 7d)
- 重复 email 注册返回 409 Conflict
- Acceptance: curl POST /api/auth/register 返回 201 + JWT

## 2. EXPECTED OUTCOME

- [ ] Files created/modified:
  - src/api/auth/register.go (新建, register handler)
  - src/api/auth/register_test.go (新建, handler 测试)
  - src/models/user.go (可能修改, 添加 User struct)
- [ ] Functionality:
  - POST /api/auth/register 接受 {"email":"...", "password":"..."}
  - 成功: 201 + {"access_token":"...", "refresh_token":"...", "expires_in": 3600}
  - email 格式错误: 400 + {"error":"invalid_email"}
  - password 太弱: 400 + {"error":"weak_password"}
  - email 已存在: 409 + {"error":"email_exists"}
- [ ] Verification:
  - `go test ./src/api/auth/ -v -run TestRegister` -- ALL tests pass
  - `go build ./...` exits 0
  - curl POST localhost:8080/api/auth/register 返回 201

## 3. REQUIRED TOOLS

- Read: src/api/auth/ (查看现有 auth handler 模式)
- Read: src/models/ (查看现有 model 定义)
- Read: src/middleware/auth.go (查看 JWT 生成方式)
- Grep: 搜索 "bcrypt" 确认项目中使用的哈希库
- Grep: 搜索 "INSERT INTO users" 确认数据库操作模式

## 4. MUST DO

- 遵循 src/api/auth/ 中现有 handler 的模式 (函数签名、错误处理、日志)
- 使用项目已有的 JWT 生成函数 (在 src/middleware/auth.go)
- 密码强度验证: 最少 8 位，包含大小写字母和数字
- 编写 table-driven tests，覆盖: 成功注册、email 格式错误、password 太弱、email 重复、空 body
- 所有错误信息使用统一格式: {"error": "snake_case_code"}
- 将发现追加到 notepad (不要覆盖)

## 5. MUST NOT DO

- 不要修改 src/api/auth/login.go (登录是独立任务)
- 不要修改 src/middleware/auth.go (JWT 函数是共享的，只使用不修改)
- 不要添加新的 Go 依赖 (使用项目已有的 bcrypt 和 JWT 库)
- 不要修改数据库 schema (users 表已存在)
- 不要跳过测试编写 -- TDD 铁律

## 6. CONTEXT

### Notepad Paths
- READ: {project-root}/_bmad/memory/hw-plan-executor/notepads/user-auth-feature/learnings.md
- READ: {project-root}/_bmad/memory/hw-plan-executor/notepads/user-auth-feature/decisions.md
- READ: {project-root}/_bmad/memory/hw-plan-executor/notepads/user-auth-feature/issues.md
- WRITE: {project-root}/_bmad/memory/hw-plan-executor/notepads/user-auth-feature/learnings.md (追加)

### Inherited Wisdom

来自 learnings.md:
- 项目使用 Go 1.22 + chi router + sqlx + PostgreSQL
- 所有 API handler 返回 JSON，使用统一的 Response struct: {data, error}
- 测试使用 testify/assert + httptest
- JWT 密钥来自环境变量 JWT_SECRET，通过 os.Getenv 读取

来自 decisions.md:
- 决定使用 access/refresh token 双 token 模式
- access token 1h，refresh token 7d
- refresh token 存储在数据库中有独立的 refresh_tokens 表

来自 issues.md:
- bcrypt cost 设为 12（之前用 10 在性能测试中不够安全）
- email 验证使用 regexp.MustCompile(`^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`)

### Dependencies

本任务无上游依赖。这是第一个被执行的波次任务。
```

## 完整示例 2: 前端页面任务

```
## 1. TASK

实现用户注册页面:
- 路由: /register
- 表单: email 输入框 + password 输入框 + confirm password 输入框 + 提交按钮
- 客户端验证: email 格式、password 强度、两次密码一致
- 提交: POST /api/auth/register
- 成功: 显示成功消息 + 3 秒后跳转到 /login
- 失败: 显示服务端错误信息 (email 已存在、格式错误等)
- Acceptance: 浏览器中访问 /register，填写表单，成功注册

## 2. EXPECTED OUTCOME

- [ ] Files created/modified:
  - src/pages/Register.tsx (新建, 注册页面组件)
  - src/pages/__tests__/Register.test.tsx (新建, 页面测试)
  - src/router.tsx (修改, 添加 /register 路由)
- [ ] Functionality:
  - /register 页面渲染: email + password + confirm password + 提交按钮
  - 客户端验证: email 格式无效 → 显示 "请输入有效的邮箱地址"
  - 客户端验证: password < 8 位 → 显示 "密码至少需要 8 位"
  - 客户端验证: 两次密码不同 → 显示 "两次输入的密码不一致"
  - 提交中: 显示 loading 状态，按钮 disabled
  - 注册成功: 显示 "注册成功！即将跳转到登录页面..." → 3s 后 redirect 到 /login
  - 注册失败: 显示服务端返回的错误信息
- [ ] Verification:
  - `npm test -- Register.test.tsx` -- ALL tests pass
  - `npm run build` exits 0
  - 浏览器访问 localhost:3000/register 页面正常渲染

## 3. REQUIRED TOOLS

- Read: src/pages/Login.tsx (参考登录页面的表单实现模式)
- Read: src/api/auth.ts (查看已有的 API 调用函数)
- Read: src/components/Button.tsx (使用项目已有的 Button 组件)
- Grep: 搜索 "useForm" 或 "react-hook-form" 确认表单管理方式
- Grep: 搜索 "navigate" 或 "useNavigate" 确认路由跳转方式

## 4. MUST DO

- 遵循 src/pages/Login.tsx 的表单结构和样式模式
- 使用项目已有的 UI 组件 (Button, Input, FormField)
- 使用 React Hook Form (如果项目已使用) 或受控组件模式
- 编写测试覆盖: 页面渲染、表单验证、成功提交、错误提交、loading 状态
- 所有中文文案使用项目 i18n 系统 (不要硬编码中文)
- 将发现追加到 notepad (不要覆盖)

## 5. MUST NOT DO

- 不要创建新的 UI 组件 (使用项目已有的 Button, Input 等)
- 不要修改 src/api/auth.ts (API 函数已完成，只使用)
- 不要添加新的 npm 依赖
- 不要修改 src/pages/Login.tsx (登录页面是独立模块)
- 不要使用 absolute import paths (使用项目配置的路径别名 @/)

## 6. CONTEXT

### Notepad Paths
- READ: {project-root}/_bmad/memory/hw-plan-executor/notepads/user-auth-feature/learnings.md
- READ: {project-root}/_bmad/memory/hw-plan-executor/notepads/user-auth-feature/decisions.md
- READ: {project-root}/_bmad/memory/hw-plan-executor/notepads/user-auth-feature/issues.md
- WRITE: {project-root}/_bmad/memory/hw-plan-executor/notepads/user-auth-feature/learnings.md (追加)

### Inherited Wisdom

来自 learnings.md:
- 项目使用 React 18 + TypeScript + React Router v6
- 所有表单使用 react-hook-form + zod 校验
- 样式使用 Tailwind CSS
- API 调用使用 axios，错误处理统一在 src/api/client.ts
- 路由定义在 src/router.tsx，使用 lazy loading

来自 decisions.md:
- 注册成功后跳转到 /login 而不是自动登录（需要用户验证邮箱后才能登录）
- 密码强度规则: 最少8位，包含大小写字母和数字

来自 issues.md:
- 注意: /api/auth/register 在 email 已存在时返回 409 而不是 400
- 注册 API 的 Content-Type 是 application/json

### Dependencies

上游已完成:
- task-1: 用户注册 API (POST /api/auth/register) -- 已完成，可通过 localhost:8080/api/auth/register 访问
  - API 契约: {email: string, password: string} -> {access_token, refresh_token, expires_in}
  - 错误响应: {error: "invalid_email"|"weak_password"|"email_exists"}
```

## Inherited Wisdom 编写指南

### 从 notepad 提取智慧

在编写每个委托提示前，必须读取 notepad 文件并提取相关内容：

1. **读取 learnings.md**：最近发现的模式、约定、代码库知识
2. **读取 decisions.md**：影响当前任务的架构决策
3. **读取 issues.md**：之前任务遇到并解决的问题
4. **跳过 problems.md**：未解决的问题留给协调器处理，不给子 agent

### Inherited Wisdom 格式

```
来自 learnings.md:
- [模式/约定 1]
- [模式/约定 2]

来自 decisions.md:
- [决策 1 及理由]

来自 issues.md:
- [注意/陷阱 1]
- [注意/陷阱 2]
```

### 继承智慧的质量标准

- **具体，不笼统**："使用 Go 1.22 + chi router" 而不是 "使用 Go"
- **行动导向**："bcrypt cost 设为 12" 而不是 "注意 bcrypt cost"
- **相关**：只提取影响当前任务的内容，不倾倒整个 notepad

## 常见错误

| 错误 | 纠正 |
|------|------|
| 委托提示少于 30 行 | 检查是否遗漏 section，补充具体细节 |
| TASK 部分自己概括 | 必须引用计划文件中的精确描述 |
| EXPECTED OUTCOME 模糊 | 列出精确的文件路径和命令行 |
| CONTEXT 放空 | 必须读取 notepad 并提取相关智慧 |
| MUST NOT DO 写 "不要出错" | 写具体的禁止行为，如 "不要修改 src/api/auth.go" |
| 跨多个任务 | 一个委托只做一件事。多个任务 = 多次委托 |
