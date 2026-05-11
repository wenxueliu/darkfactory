# result-format.md — 结构化输出模板

## 何时加载

每次返回搜索结果时参考本文档，确保输出格式符合规范。

---

## 1. 标准输出模板

每次响应必须按以下结构组织：

```
<analysis>
**Literal Request**: [调用者的字面请求]
**Actual Need**: [调用者真正想要达成的目标]
**Success Looks Like**: [什么样的结果能让调用者立即行动]
</analysis>

<results>
<files>
- /absolute/path/to/file1.ext - [该文件与需求的关联说明]
- /absolute/path/to/file2.ext - [该文件与需求的关联说明]
</files>

<answer>
[针对实际需求的直接回答，附带必要的解释]
</answer>

<next_steps>
[调用者接下来应该做什么]
[如果无需后续操作则写: "Ready to proceed - no follow-up needed"]
</next_steps>
</results>
```

---

## 2. 各区块说明

### 2.1 `<analysis>` — 意图分析（必填）

在开始任何搜索之前输出。帮助调用者确认你理解了他们的真实需求，也让调用者有机会纠正理解偏差。

**关键：** 区分字面请求和实际需求。调用者说的不一定等于他们需要知道的。

### 2.2 `<files>` — 文件列表（必填）

列出所有找到的相关文件，每行一个。

**格式要求：**
- 每个路径必须是**绝对路径**（以 `/` 开头）
- 每个文件附带简短的关联说明（用 ` - ` 分隔）
- 按重要程度排序，最相关的排在最前面
- 如果文件数量超过 10 个，只列出最关键的 10 个，其余归类说明

**示例：**
```
<files>
- /home/user/project/src/auth/login.ts - 登录逻辑入口，处理用户名密码验证
- /home/user/project/src/auth/middleware.ts - 认证中间件，每个请求的 token 验证
- /home/user/project/src/auth/token.ts - JWT token 生成和刷新逻辑
- /home/user/project/src/config/auth.config.ts - 认证配置：token 过期时间、密钥来源
</files>
```

### 2.3 `<answer>` — 直接回答（必填）

回答调用者的**实际需求**，而非字面问题。应该包含：

- 对所发现内容的解释（不只是一个文件列表）
- 代码结构关系（如果相关）
- 任何需要注意的边界情况或陷阱

**示例（好的回答）：**
```
<answer>
认证系统采用 JWT + 中间件模式，分布在 4 个文件：

1. **入口点** — `src/auth/login.ts` 的 `authenticateUser()` 接收用户名密码，
   调用 `bcrypt.compare()` 验证后，调用 token.ts 生成 JWT
2. **令牌管理** — `src/auth/token.ts` 负责 JWT 生成（`generateToken()`）和
   刷新（`refreshToken()`），使用 RS256 算法，密钥来自环境变量 `JWT_PRIVATE_KEY`
3. **请求验证** — `src/auth/middleware.ts` 的 `authMiddleware()` 在每个受保护
   路由上提取 Authorization header，调用 `verifyToken()` 解析
4. **配置** — `src/auth/config.ts` 集中管理 token 过期时间（默认 15min）、
   刷新窗口（7天）、白名单路径

认证流程: login.ts → token.ts → middleware.ts；调用链完整可追踪。
</answer>
```

### 2.4 `<next_steps>` — 后续步骤（必填）

告诉调用者接下来该做什么。可能包括：

- 可以直接进行下一步操作
- 需要读取某个文件了解更多细节
- 发现的代码使用了特定模式，修改时应该注意什么
- 存在风险点需要注意

---

## 3. 完整示例

### 3.1 示例 1：好的输出 — "auth 实现在哪里？"

```
<analysis>
**Literal Request**: 查找 auth 相关的代码位置
**Actual Need**: 理解项目的认证机制，可能是为了修改认证逻辑或添加新功能
**Success Looks Like**: 了解认证系统的完整结构：入口点、核心逻辑、配置、中间件，
  以及它们之间的关系
</analysis>

<results>
<files>
- /home/user/project/src/auth/login.ts - 登录入口，`authenticateUser()` 处理凭证验证
- /home/user/project/src/auth/token.ts - JWT 令牌生成和刷新，`generateToken()` / `refreshToken()`
- /home/user/project/src/auth/middleware.ts - 认证中间件，`authMiddleware()` 拦截受保护路由
- /home/user/project/src/auth/config.ts - 认证配置常量（过期时间、算法、白名单）
- /home/user/project/src/auth/types.ts - 认证相关 TypeScript 类型定义
</files>

<answer>
认证系统使用 JWT + 中间件模式实现，5 个文件构成了完整的认证层：

**核心流程：**
1. `login.ts` — `authenticateUser()` 接收凭证，bcrypt 验证后调用 token.ts
2. `token.ts` — 生成 RS256 JWT（15min 有效期），支持 refresh token（7天窗口）
3. `middleware.ts` — `authMiddleware()` 解析 Authorization header 并验证 token
4. `config.ts` — 集中管理：`TOKEN_EXPIRY=900s`, `REFRESH_WINDOW=604800s`, `ALGORITHM=RS256`
5. `types.ts` — `AuthPayload`, `TokenPair`, `AuthConfig` 接口

**关键发现：**
- 密码使用 bcrypt（12 rounds），不可逆
- 密钥来自 `JWT_PRIVATE_KEY` 环境变量，未配置时启动失败
- 白名单路径在 config.ts 的 `PUBLIC_ROUTES` 数组中定义
</answer>

<next_steps>
- 如果要修改认证逻辑：从 login.ts 开始，跟随调用链到 token.ts
- 如果要添加新的认证方式（如 OAuth）：在 middleware.ts 中添加新的验证策略
- 如果要调整 token 过期时间：修改 config.ts 即可，无需改业务代码
- 注意：修改 auth 相关代码后，确保 JWT_PRIVATE_KEY 环境变量在测试环境中已配置
</next_steps>
</results>
```

### 3.2 示例 2：好的输出 — "哪里处理了错误重试？"

```
<analysis>
**Literal Request**: 查找错误重试的代码位置
**Actual Need**: 理解系统的容错机制，可能为了调试重试行为或调整重试策略
**Success Looks Like**: 找到所有实现重试逻辑的位置，包括重试次数、退避策略、适用场景
</analysis>

<results>
<files>
- /home/user/project/src/utils/retry.ts - 通用重试工具函数 `withRetry()`，支持指数退避
- /home/user/project/src/api/client.ts - HTTP 客户端的 `request()` 方法调用 `withRetry()`
- /home/user/project/src/services/queue.ts - 消息队列消费者的 `processWithRetry()` 死信队列处理
- /home/user/project/src/config/retry.config.ts - 重试配置：maxRetries=3, backoffMultiplier=2, maxDelay=30s
</files>

<answer>
错误重试在 3 个层级实现：

1. **通用层** — `src/utils/retry.ts` 的 `withRetry(fn, options)` 是核心重试原语。
   实现指数退避：每次重试等待 `min(baseDelay * multiplier^attempt, maxDelay)`。

2. **HTTP 层** — `src/api/client.ts` 的 `request()` 方法对所有 5xx 和网络错误
   自动重试，使用默认配置（maxRetries=3）。

3. **消息队列层** — `src/services/queue.ts` 的 `processWithRetry()` 处理消费失败，
   超过重试次数后消息进入死信队列。

**配置统一入口：** `src/config/retry.config.ts` 控制全局重试参数。
</answer>

<next_steps>
- 调整重试次数：修改 retry.config.ts 的 maxRetries 即可全局生效
- 调试特定重试行为：在 retry.ts 的 withRetry() 中添加日志
- API 层和队列层使用同一个 withRetry() 原语，修改这里会影响所有重试行为
</next_steps>
</results>
```

### 3.3 示例 3：坏输出 — 应该避免的模式

```
❌ 坏输出 1 — 只回答了字面问题
<files>
- src/auth/login.ts
- src/auth/token.ts
</files>

问题：路径是相对路径；没有解释文件的作用；没有回答认证流程是什么


❌ 坏输出 2 — 没有意图分析
<results>
<files>
- /home/user/project/src/auth/login.ts - auth file
</files>
</results>

问题：缺少 <analysis> 区块；说明过于简单；只找到一个文件就停止了


❌ 坏输出 3 — 只有文件列表，没有回答
<results>
<files>
- /home/user/project/src/auth/login.ts - 登录处理
- /home/user/project/src/auth/token.ts - 令牌处理
</files>
<answer>
See the files above.
</answer>
</results>

问题：<answer> 是空的 — 没有解释代码如何工作；没有回答调用者的实际需求


❌ 坏输出 4 — 过度使用 emoji
<results>
<files>
- 🔐 /home/user/project/src/auth/login.ts - 登录入口 🚪
</files>

问题：使用了 emoji，违反输出约束；破坏可解析性
```

---

## 4. 特殊情况处理

### 4.1 找不到结果时

```
<analysis>
**Literal Request**: [字面请求]
**Actual Need**: [实际需求]
**Success Looks Like**: [理想结果]
</analysis>

<results>
<files>
（未找到匹配的文件）
</files>

<answer>
在代码库中未找到 [搜索目标]。搜索覆盖了：
- LSP 符号搜索：[搜索范围]
- grep 文本搜索：[搜索的 pattern]
- glob 文件搜索：[搜索的 pattern]
- ast_grep 结构搜索：[搜索的 pattern]

可能的原因：
1. 功能尚未实现
2. 使用了不同的命名约定
3. 代码位于独立仓库中
</answer>

<next_steps>
- 建议确认搜索关键词是否正确
- 提供更多线索（如相关的类名、文件名片段、提交信息）后重新搜索
</next_steps>
</results>
```

### 4.2 搜索结果过多时（> 50 个文件）

```
<files>
核心文件（最相关的 10 个）:
- /path/to/file1.ext - [说明]
- ...

其余约 40 个匹配文件分布在以下目录：
- /project/src/handlers/ (15 files) — 各类请求处理器
- /project/src/middleware/ (12 files) — 中间件函数
- /project/src/utils/ (8 files) — 工具函数
- /project/tests/ (5 files) — 测试文件
</files>
```
