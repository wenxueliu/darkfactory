# Notepad System: 记事本系统

## 设计目的

子 Agent 是**无状态的**。每次委托启动的新 session 不知道之前发生了什么。Notepad 是跨委托的**累积智能**——将每次执行中学到的知识永久化，供后续委托使用。

## 目录结构

```
{project-root}/_context/memory/sw-plan-executor/notepads/
└── {plan-name}/
    ├── learnings.md    # 发现的模式、约定、代码库知识
    ├── decisions.md    # 架构选择和理由
    ├── issues.md       # 遇到的问题和解决方案
    └── problems.md     # 未解决的阻塞问题
```

每个计划的 notepad 是独立的。不同计划间不共享 notepad。

## 四个文件详解

### learnings.md -- 学习记录

**内容：** 代码库模式、项目约定、工具用法、文件位置等可复用的知识。

**什么应该记录：**
- 发现的代码路径：`src/middleware/auth.go` 包含 JWT 生成逻辑
- 项目约定：所有 API handler 使用 `func(w http.ResponseWriter, r *http.Request) error` 签名
- 工具用法：测试命令是 `go test ./... -v -count=1`
- 陷阱：`user_id` 是 UUID 字符串，不是整数
- 配置密钥：JWT 密钥来自 `JWT_SECRET` 环境变量
- 依赖版本：项目使用 React 18 + TypeScript 5.3

**格式：**
```markdown
## 项目模式与约定

### API Handler 模式
- 所有 handler 在 `src/api/{domain}/` 下
- 每个 handler 一个文件，命名: `{operation}.go`
- 测试文件: `{operation}_test.go`
- Handler 签名: `func(w http.ResponseWriter, r *http.Request) error`
- 统一错误响应: `{"error": "snake_case_code"}`

### 数据库模式
- 使用 sqlx + PostgreSQL
- Model 定义在 `src/models/`
- 查询在 `src/db/` 下按表名分包

## 编译器/构建
- 构建命令: `go build -o bin/server ./cmd/server`
- 测试命令: `go test ./... -v -count=1`

## 陷阱与注意事项
- `user_id` 是 UUID 字符串，不是 int
- `config.yaml` 中 `db.host` 的值包括端口号
- 前端 Proxy 配置在 `vite.config.ts` 的 server.proxy
```

### decisions.md -- 决策记录

**内容：** 关键选择、权衡和做出该选择的原因。

**什么应该记录：**
- 技术方案选择：选择 bcrypt 而不是 argon2，因为项目已有 bcrypt 库
- 架构决策：access token 存 localStorage 还是 httpOnly cookie（选了后者）
- 命名约定：决定使用 `createUser` 而不是 `registerUser`
- 目录结构：决定将 auth 逻辑放 `src/api/auth/` 而不是 `src/services/auth/`

**格式:**
```markdown
## 决策记录

### D1: bcrypt cost = 12
- 日期: 2026-05-10
- 背景: 需要选择密码哈希的工作因子
- 选项:
  - cost=10 (快但不够安全)
  - cost=12 (平衡安全与性能)
  - cost=14 (最安全但慢)
- 决定: cost=12
- 理由: 在性能测试中 cost=12 的单次哈希耗时 ~250ms，可接受。cost=14 耗时 ~1s，影响注册体验
- 影响: 注册请求的响应时间增加 ~250ms

### D2: refresh token 存储策略
- 日期: 2026-05-10
- 背景: 需要决定 refresh token 的存储方式
- 选项:
  - 存储在客户端 localStorage (XSS 风险)
  - 存储在 httpOnly cookie (CSRF 需要额外防护)
- 决定: httpOnly cookie + SameSite=Strict
- 理由: 防止 XSS 窃取 token。CSRF 通过 SameSite 和 CORS 白名单缓解
- 影响: 前端不需要处理 token 存储，但需要配置 CSRF 防护
```

### issues.md -- 问题与解决方案

**内容：** 遇到的技术难点和调试经验。

**什么应该记录：**
- 遇到的具体错误及解决方案
- 调试过程中发现的非直觉行为
- 依赖冲突的解决方法
- 配置问题及其修复

**格式：**
```markdown
## 已解决的问题

### I1: bcrypt 导入冲突
- 任务: task-1 (用户注册 API)
- 问题: `import "golang.org/x/crypto/bcrypt"` 编译报错 "module not found"
- 原因: 项目使用 `go mod vendor`，需要先 `go mod vendor` 更新 vendor 目录
- 解决: 运行 `go mod tidy && go mod vendor` 后重新编译
- 经验: 添加新导入前先检查 vendor 目录是否包含该包

### I2: 测试数据库连接失败
- 任务: task-1 (用户注册 API)
- 问题: 测试中连接 PostgreSQL 报 "connection refused"
- 原因: 项目测试使用独立的 test database，需要先启动 `docker-compose up -d test-db`
- 解决: 启动测试数据库后测试通过
- 经验: 运行集成测试前确保测试基础设施已启动

### I3: React Hook Form 类型错误
- 任务: task-4 (前端注册页面)
- 问题: `useForm<UserRegisterInput>()` 报类型错误
- 原因: UserRegisterInput 的 confirmPassword 字段与 API 请求类型冲突
- 解决: 创建独立的 `RegisterFormData` 类型（包含 confirmPassword），提交时映射为 `RegisterRequest` 类型
- 经验: 表单数据类型和 API 请求类型最好分开定义
```

### problems.md -- 未解决的阻塞

**内容：** 当前无法解决、需要外部干预的问题。

**什么应该记录：**
- 3 次重试后仍失败的阻塞问题
- 需要人工决策的技术分歧
- 外部依赖不可用
- 配置或权限不足

**格式：**
```markdown
## 未解决的阻塞问题

### P1: 数据库迁移缺少权限
- 任务: task-1 (用户注册 API)
- 时间: 2026-05-10 14:30
- 问题: 需要执行 `CREATE EXTENSION IF NOT EXISTS "uuid-ossp"` 但数据库用户缺少 SUPERUSER 权限
- 已尝试:
  1. 直接执行迁移脚本 — "permission denied"
  2. 使用 ALTER ROLE 提权 — "must be superuser"
  3. 联系 DBA — 等待回复
- 所需行动: DBA 执行扩展安装，或授予 SUPERUSER 权限
- 影响: task-1 的数据库部分被阻塞，但不影响纯代码部分
```

## 何时读取 Notepad

**在每个委托之前，必须读取 notepad：**

1. 执行 `glob("{project-root}/_context/memory/sw-plan-executor/notepads/{plan-name}/*.md")` 确认文件存在
2. 读取 `learnings.md` -- 了解项目模式和约定
3. 读取 `decisions.md` -- 了解影响当前任务的架构决策
4. 读取 `issues.md` -- 了解之前遇到的问题和解决方案
5. 跳过 `problems.md` -- 这些是协调器的责任，不给子 agent

将提取的智慧放入委托提示的 "Inherited Wisdom" section。

**如果在波次 1 的第一次委托，notepad 可能为空。这是正常的。** 如果 notepad 文件只有初始标题或为空，在 Inherited Wisdom 中写 "No prior learnings — this is the first task in the plan."

## 何时写入 Notepad

**在每个验证通过的委托完成后，更新 notepad：**

### 协调器操作 (你操作)

在验证完成后，你直接:
1. **更新 learnings.md**：追加你的审查中发现的模式、约定、项目知识
2. **更新 decisions.md**：记录你做出的架构/策略决策
3. **更新 problems.md**：记录放弃的阻塞问题

### 委托子 Agent 写入

在委托提示的 MUST DO 中，指示子 agent:
```
将发现追加到 {project-root}/_context/memory/sw-plan-executor/notepads/{plan-name}/learnings.md (追加，不覆盖)
将发现追加到 {project-root}/_context/memory/sw-plan-executor/notepads/{plan-name}/issues.md (追加，不覆盖)
```

### 写入格式规则

- **追加 (Append)，不覆盖 (Never overwrite)**：使用追加方式在文件末尾添加新条目，保留历史
- **不要使用 Edit 工具**：子 agent 应该只追加内容
- **包含时间戳**：每条记录前加 `## [时间戳]` 或 `### [时间戳]` 以便追溯

子 agent 写入示例：
```markdown
### 2026-05-10 15:20 — Task: task-2

发现项目使用 Go 1.22 的 `net/http` 新路由模式 `mux.HandleFunc("POST /api/auth/login", handler)`。
旧 handler 使用 `if r.Method != "POST"` 手动检查方法，新代码应采用新模式。
```

## Notepad 生命周期

- **创建**：Step 2 (Initialize Notepad) -- 当开始执行计划时创建
- **累积**：每个委托前读取，每个验证后写入
- **归档**：Final Verification Wave 全部通过后，整个 notepad 目录可以考虑合并到共享知识库 `_context/memory/sw-shared/knowledge-base/`
- **清理**：不自动删除。如需清理，这是人工决策。

## Notepad 使用示例

### 场景：波次 2 委托前

```
1. 读取 learnings.md -- 发现:
   - API handler 使用特定签名
   - 测试框架是 pytest + httpx
   - JWT 生成在 src/core/security.py

2. 读取 decisions.md -- 发现:
   - 密码哈希用 bcrypt cost=12
   - refresh token 存 httpOnly cookie

3. 读取 issues.md -- 发现:
   - 上次测试失败因为 docker-compose 未启动测试数据库
   - 注意: src/core/db.py 中的 get_db() 使用 async session

4. 将以上内容精简后放入新生委托的 "Inherited Wisdom"
```

### 场景：验证完成后

```
1. 协调器回顾审查中的发现:
   - 子 agent 使用了正确的 handler 签名 ✓
   - 子 agent 遇到的 bcrypt 版本问题解决了 (记录到 issues.md)
   - 发现新的项目约定: 所有 Python type hint 使用 from __future__ import annotations

2. 更新 learnings.md -- 追加新的约定发现
3. 更新 issues.md -- 追加解决的新问题
```
