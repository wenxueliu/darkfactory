# DEPRECATED: 此模板已被 3 阶段设计流程取代

此模板的章节已拆分到 3 个独立 Agent 的模板中。请勿直接加载本文件。

## 章节迁移映射

| 原章节 | 新归属 | Agent | 新模板 |
|--------|--------|-------|--------|
| Section 1-3: 概述/用户旅程/页面 | Cross-service 特性设计 | sw-feature-designer | `feature-design-template.md` |
| Section 4-9: 技术决策/架构/API/状态/错误/安全 | Per-service 详细设计 | sw-service-designer | `service-design-template-{type}.md` |
| Section 10.1-10.4: UT/API 测试设计 | Per-service 详细设计 | sw-service-designer | `test-case-template.md` + `api-test-case-template.json` |
| Section 10.5: E2E 测试设计 | Cross-service E2E 设计 | sw-e2e-designer | `e2e-test-case-template.md` |
| Section 10.6-10.7: 追溯/数据策略 | Cross-service 特性设计 | sw-feature-designer | `feature-design-template.md` |
| Section 11-13: 部署/问题/引用 | Cross-service 特性设计 | sw-feature-designer | `feature-design-template.md` |

---

# 设计文档模板

## 使用说明

此模板在需求门禁 PASS 后使用。基于 `requirements/{requirement_id}.md` 创建。

### 架构模式适配

| 架构模式 | 文档结构 | 模板使用方式 |
|---------|---------|------------|
| `monolith` (默认) | 一份文档包含全部 13 章 | 直接使用本模板 |
| `microservices` | N 个 per-service 文档 + 1 个 cross-service 文档 | 见 `microservice-adaptation.md` — 本模板章节按拆分原则分属不同文档 |

### 微服务模式下的章节归属

当 `architecture: "microservices"` 时，本模板的章节按以下原则拆分:

**Per-service 文档** (`designs/{id}-service-{service_id}-design.md`) — 使用本模板的 Section 4-10.4:
- Section 4 技术决策 → per-service S1
- Section 5 架构设计 → per-service S2
- Section 6 API/接口设计 → per-service S3
- Section 7 状态管理 → per-service S4
- Section 8 错误处理策略 → per-service S5
- Section 9 安全设计 → per-service S6
- Section 10.1-10.4 测试设计 (UT + API) → per-service S7-S8

**Cross-service 文档** (`designs/{id}-design.md`) — 使用本模板的其余章节:
- Section 1-3 设计概述/用户旅程/页面设计
- Section 10.5 E2E 测试设计
- Section 10.6-10.7 三层追溯矩阵/测试数据策略
- Section 11-13 部署/开放问题/下游引用
- 加上微服务专属: 服务交互设计 + 跨服务契约 + per-service 文档引用指针

**拆分原因:** UT 和 API 测试随服务——测试的是该服务的代码和端点。E2E 跨服务——验证的是完整用户旅程，不归属单一服务。

### 单体模式

填入后写入 `{project-root}/_context/memory/sw-shared/designs/{requirement_id}-design.md`。

设计文档是开发阶段的唯一技术事实源。代码实现必须回溯到设计决策。

---

# 设计文档: {需求标题}

**设计ID:** `{DESIGN-YYYYMMDD-NNN}`
**关联需求:** `{REQ-YYYYMMDD-NNN}`
**状态:** `draft | reviewed | approved | implemented`
**创建时间:** `{timestamp}`

## 1. 设计概述

{2-3 句话描述技术方案的核心思路。一个不熟悉项目的工程师应该在 30 秒内理解方案。}

## 2. 用户旅程设计

需求规格描述了用户"应该经历什么"（WHAT）。本章节描述系统"如何交付这个体验"（HOW）——从系统视角设计用户在功能中的每一步交互。如果功能没有用户交互（纯后端服务/数据管道），本章可标注 N/A 后跳过。

### 2.1 交互流程

```
{入口} → {步骤1} → {步骤2} → {步骤3} → {步骤4} → {完成}
   │         │         │         │         │         │
   ▼         ▼         ▼         ▼         ▼         ▼
[怎么进来?] [系统做什么?] [用户选什么?] [系统反馈?] [成功长啥样?] [状态怎么变?]
```

| 步骤 | 用户动作 | 系统行为 | 成功条件 | 失败处理 | 对应需求 AC |
|------|---------|---------|---------|---------|------------|
| 1. {步骤名} | {用户做什么} | {系统如何响应} | {怎样算成功} | {失败时怎么办} | AC-{N} |
| 2. {步骤名} | {用户做什么} | {系统如何响应} | {怎样算成功} | {失败时怎么办} | AC-{N} |
| 3. {步骤名} | {用户做什么} | {系统如何响应} | {怎样算成功} | {失败时怎么办} | AC-{N} |

**最少要求:** 覆盖需求的完整 happy path。每个步骤标注对应的 AC 编号（追溯到需求）。

### 2.2 关键交互时刻 (Moments of Truth — 设计视角)

需求规格的 Moments of Truth 描述了用户的情感判断点。设计必须确保系统在这些节点上**不会失败**:

| 关键时刻 | 用户体验目标 | 系统设计要求 | 降级方案 |
|---------|------------|------------|---------|
| {如: 首次加载 < 2s} | {无等待感} | {CDN + 骨架屏 + 预加载} | {静态缓存版本} |
| {如: 支付确认} | {确定性反馈} | {同步返回 + 异步通知双通道} | {轮询 + 客服介入} |
| {如: 搜索无结果} | {不沮丧} | {智能纠错 + 相似推荐 + 空状态引导} | {人工客服入口} |

### 2.3 交互状态矩阵

用户在每个步骤可能遇到的状态必须全部覆盖:

| 步骤 | 正常态 | 加载中 | 空状态 | 错误态 | 边界态 |
|------|--------|--------|--------|--------|--------|
| 步骤1 | {正常展示} | {skeleton/spinner} | {引导文案} | {错误提示 + 重试} | {极限输入/并发} |
| 步骤2 | {正常展示} | {进度条} | {创建引导} | {降级方案} | {权限不足} |

**设计原则:**
- 每个状态都要有 UI 方案（哪怕一句描述）
- 空状态是用户的第一印象——不要留白，用引导文案填充
- 错误状态要说人话（不是 "500 Internal Server Error"）

## 3. 页面设计

如果功能涉及 UI 页面，为每个页面编写设计说明。纯后端/API 功能可标注 N/A 后跳过本章。

### 3.1 页面清单

| 页面 ID | 页面名称 | 路由 | 来源（从哪个页面跳过来） | 去向（跳转到哪个页面） |
|---------|---------|------|---------------------|---------------------|
| P-1 | {页面名} | `/path/:param` | {上一页} / 直接访问 / 外部链接 | P-2, P-3 |
| P-2 | {页面名} | `/path/:param` | P-1 | P-3 |

### 3.2 页面布局 (每个页面)

```
# P-{N}: {页面名称}

## 布局结构
┌─────────────────────────────────────────┐
│  Header / 导航栏                         │
├─────────────────────────────────────────┤
│  ┌─────────────┐  ┌───────────────────┐  │
│  │  侧边栏      │  │  主内容区          │  │
│  │  (如有)      │  │                   │  │
│  │             │  │  {组件 A}         │  │
│  │             │  │  {组件 B}         │  │
│  │             │  │  {组件 C}         │  │
│  └─────────────┘  └───────────────────┘  │
├─────────────────────────────────────────┤
│  Footer / 操作栏                         │
└─────────────────────────────────────────┘
```

## 组件清单

| 组件 | 类型 | 数据来源 | 交互行为 | 复用? |
|------|------|---------|---------|-------|
| {组件 A} | 表单/列表/卡片/图表/... | API-{X} / 本地状态 / props | {点击 → 什么 / 输入 → 校验} | 已有/新建 |
| {组件 B} | ... | ... | ... | ... |

## 交互细节

| 触发 | 前置条件 | 行为 | 反馈 | 异常 |
|------|---------|------|------|------|
| 点击「提交」 | 表单已通过前端校验 | POST /api/v1/{resource} | loading → toast 成功/失败 | 网络错误 → 保留表单数据 + 重试提示 |
| 输入搜索关键词 | 输入 ≥ 2 字符 | debounce 300ms → GET search | 下拉建议列表 | API 超时 → 提示"搜索暂不可用" |

## 响应式行为 (如适用)

| 断点 | 布局变化 | 隐藏/显示 |
|------|---------|----------|
| Desktop (>1024px) | 侧边栏 + 主内容区 | 全部显示 |
| Tablet (768-1024px) | 侧边栏折叠为汉堡菜单 | 次要信息可隐藏 |
| Mobile (<768px) | 单列布局 | 只保留核心操作 |
```

### 3.3 页面间导航

```
P-1: {页面名} ──[点击按钮A]──▶ P-2: {页面名}
    │                              │
    └──[点击链接B]──▶ P-3: {页面名} ◀──[提交成功]──┘
```

**路由参数传递:**

| 从 | 到 | 传递方式 | 参数 |
|----|----|---------|------|
| P-1 | P-2 | URL param | `?id={resource_id}` |
| P-1 | P-3 | 查询后内部跳转 | `state: { from: 'P-1' }` |

## 4. 技术决策

| ID | 决策 | 理由 | 替代方案 | 权衡 |
|----|------|------|---------|------|
| D-1 | {选择的技术方案} | {为什么选这个} | {考虑过但放弃的方案} | {牺牲了什么} |
| D-2 | {选择的技术方案} | {为什么选这个} | {考虑过但放弃的方案} | {牺牲了什么} |

## 5. 架构设计

### 5.1 组件图

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Component │────▶│   Component │────▶│   Component │
│      A      │     │      B      │     │      C      │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 5.2 数据流

```
INPUT → VALIDATION → BUSINESS LOGIC → PERSISTENCE → OUTPUT
  │         │             │               │           │
  ▼         ▼             ▼               ▼           ▼
[nil?]   [invalid?]   [exception?]    [conflict?]  [encoding?]
```

### 5.3 组件职责

| 组件 | 职责 | 输入 | 输出 | 依赖 |
|------|------|------|------|------|
| {Name} | {一句话职责} | {输入类型} | {输出类型} | {依赖组件} |

## 6. API/接口设计

### 6.1 API 端点

| Method | Path | 请求体 | 响应 | 错误码 |
|--------|------|--------|------|--------|
| POST | /api/v1/{resource} | `{json schema}` | `{json schema}` | 201, 400, 409, 500 |
| GET | /api/v1/{resource}/{id} | — | `{json schema}` | 200, 404, 500 |

### 6.2 数据模型

```yaml
# {entity_name}
fields:
  - name: {field}
    type: {type}
    nullable: true/false
    constraints: {validation rules}
    description: {business meaning}
```

## 7. 状态管理

### 7.1 状态机

```
           ┌──────────┐
           │  DRAFT   │
           └────┬─────┘
                │ submit
           ┌────▼─────┐
           │ IN_REVIEW│
           └────┬─────┘
          ┌─────┴─────┐
    approve           reject
   ┌──▼──┐         ┌──▼──┐
   │LIVE │         │DRAFT│
   └─────┘         └─────┘
```

### 7.2 状态转换规则

| 当前状态 | 触发事件 | 目标状态 | 前置条件 | 副作用 |
|---------|---------|---------|---------|--------|
| DRAFT | submit | IN_REVIEW | 所有必填字段完整 | 发送通知 |
| IN_REVIEW | approve | LIVE | reviewer 批准 | 写入审计日志 |

## 8. 错误处理策略

| 错误场景 | 异常类型 | HTTP 状态码 | 用户消息 | 重试策略 | 日志级别 |
|---------|---------|------------|---------|---------|---------|
| 资源不存在 | ResourceNotFound | 404 | "未找到 {resource}" | 不重试 | WARN |
| 并发冲突 | OptimisticLockException | 409 | "数据已被修改，请刷新重试" | 用户手动重试 | WARN |
| 上游超时 | UpstreamTimeout | 503 | "服务暂时不可用" | 指数退避 ×3 | ERROR |

## 9. 安全设计

| 关注点 | 方案 | 验证方式 |
|--------|------|---------|
| 认证 | {方案描述} | {测试方式} |
| 授权 | {方案描述} | {测试方式} |
| 输入校验 | {方案描述} | {测试方式} |
| 数据保护 | {方案描述} | {测试方式} |
| 审计日志 | {方案描述} | {测试方式} |

## 10. 测试设计 — 三层验收循环

Harness Engineering 的自动执行依赖三层反馈循环驱动。本章为每一层定义**可执行的测试用例规格**——不是策略摘要，而是 agent 可以直接照着写的测试规格。执行阶段的铁律: **没有 failing test 之前，不写生产代码。**

### 10.1 测试数据构造原则 (Test Data Construction)

**这是 AI 能够自动验证的前提。** 占位符 `{field}` 对 agent 没有任何价值——agent 需要的是可以写入代码的具体值。每层测试设计的输入/输出列必须包含**具体的数据值**，而非描述。

**数据构造规范:**

| 原则 | 要求 | 反例 | 正例 |
|------|------|------|------|
| **具体到值** | 输入和预期输出必须是具体值 | `"email": "{有效邮箱}"` | `"email": "test-tc001@example.com"` |
| **唯一性** | 每个用例的数据有唯一标识，避免并行冲突 | `"username": "admin"` | `"username": "ut-user-001-1706000000"` |
| **可预测** | 给定相同输入 → 相同输出 | 依赖随机数/当前时间戳 | 用固定种子或显式时间戳 |
| **边界可见** | 边界值直接写出来 | `"age": {边界值}` | `"age": 0`, `"age": 150`, `"age": -1` |
| **类型精确** | 值与 Section 6.2 数据模型类型一致 | `"id": "123"` (当 id 是 integer) | `"id": 123` |
| **自包含** | 每个用例自己构造前置数据，自己清理 | 用例 B 依赖用例 A 的执行结果 | `pm.sendRequest` 在 prerequest 中创建依赖 |

**UT 数据构造格式:**
```
# 输入数据构造
var input = new CreateUserRequest(
    username: "ut-user-001",       // 正常用户名
    email: "ut-001@example.com",   // 正常邮箱
    password: "Test@123456",       // 满足密码策略
    role: UserRole.MEMBER          // 默认角色
);

# Mock 依赖行为
when(userRepository.existsByEmail("ut-001@example.com")).thenReturn(false);
when(passwordEncoder.encode("Test@123456")).thenReturn("$2a$10$encrypted...");

# 预期输出
var expected = new User(
    id: 1L,
    username: "ut-user-001",
    email: "ut-001@example.com",
    role: UserRole.MEMBER,
    status: UserStatus.ACTIVE,
    createdAt: testClock.instant()  // 固定时钟，可预测
);
```

**API 数据构造格式 (Postman prerequest):**
```javascript
// 见 api-test-postman-schema.md 完整规范
// API 测试数据在 Postman Collection JSON 文件中以具体值存在
// 以下为设计视图中的摘要格式:
```

### 10.2 测试策略概述

| 层次 | 目的 | 反馈速度 | 覆盖目标 | 框架/工具 | 预估用例数 |
|------|------|---------|---------|----------|-----------|
| **L1: UT** | 验证每个函数/方法的逻辑正确性 | 秒级 | 核心业务逻辑 ≥ 90%, 工具类 ≥ 80% | {JUnit/pytest/Jest/...} | ~{N} |
| **L2: API** | 验证接口契约、数据一致性、错误处理 | 秒~分钟级 | 所有 API 端点(正常+异常+边界) | Newman (Postman Collection v2.1) | ~{N} |
| **L3: E2E** | 验证完整用户旅程、跨组件协作、UI 交互 | 分钟级 | 关键用户旅程(每个旅程至少 1 条) | {Playwright/Cypress/Selenium/...} | ~{N} |

**测试金字塔约束:**
- L1 用例数 > L2 用例数 > L3 用例数
- L2 不重复 L1 覆盖的逻辑（L2 验证集成，不验证算法细节）
- L3 不重复 L2 覆盖的 API（L3 验证旅程，不验证每个端点）

### 10.3 第一层: UT 设计 (单元测试)

对每个架构组件（Section 5.3），定义具体的单元测试用例。TDD Agent 按此表执行 RED → GREEN → REFACTOR。

**输入/输出必须是具体值，不能是 `{占位符}`。** Agent 需要能直接写入测试代码的数据。参考 10.1 数据构造原则。

**UT 用例规格:**

| 用例 ID | 组件 | 被测方法 | 场景类型 | 输入 (具体值) | Mock/Stub 依赖 (含返回值) | 预期输出/行为 (具体值) |
|---------|------|---------|---------|-------------|------------------------|---------------------|
| UT-{组件缩写}-001 | {组件名} | `{方法签名}` | happy | 见下方数据构造 | `{mockObj}.{method}()` → `{具体返回值}` | `{具体对象/值}` 或 `void (无异常)` |
| UT-{组件缩写}-002 | {组件名} | `{方法签名}` | error | `null` / `""` / invalid object | `{mockObj}.{method}()` → `{具体返回值}` | `throws {具体异常类型}("{消息}")` |
| UT-{组件缩写}-003 | {组件名} | `{方法签名}` | boundary | `{边界值: 0, -1, MAX, 空集合}` | `{mockObj}.{method}()` → `{具体返回值}` | `{具体返回值}` 或 `throws {异常}` |
| UT-{组件缩写}-004 | {组件名} | `{方法签名}` | edge | `{并发线程数}/{重入次数}/{超时ms}` | `{mockObj}.{method}()` → `{模拟行为}` | `{预期行为描述 + 验证方法}` |

**每条 UT 用例必须附带数据构造代码块:**

```
// UT-{组件缩写}-001: {场景}
// === 输入数据构造 ===
var input = new {Type}(
    field1: "{concrete_value}",
    field2: {numeric_value},
    field3: {enum_value}
);
// === Mock 依赖 ===
when({dependency}.{method}({argumentMatcher})).thenReturn({returnValue});
// === 预期输出 ===
var expected = new {Type}(
    field1: "{expected_value}",
    field2: {expected_numeric}
);
// === 执行 + 断言 ===
var result = {component}.{method}(input);
assertThat(result).isEqualTo(expected);
// 或: assertThrows({Exception}.class, () -> {component}.{method}(input));
```

**场景类型说明:**
- **happy:** 正常输入 → 正常输出（至少 1 个）
- **error:** 异常输入 → 正确的错误处理（至少 1 个）
- **boundary:** 边界值 → 正确行为（null, 空字符串, 0, MAX_INT, 空列表）
- **edge:** 并发、重入、超时、资源耗尽（按需）

**最少要求:** 每个 public 方法 ≥ 2 个 UT 用例（1 happy + 1 error/boundary）。每个组件 ≥ 1 个 edge 用例。

**追溯到需求:**

| UT 用例 | 覆盖的需求 AC | 覆盖的设计决策 |
|---------|-------------|-------------|
| UT-{id} | AC-{N} | D-{N} |

### 10.4 第二层: API 测试设计 (接口测试 — Newman/Postman)

对每个 API 端点（Section 6.1），定义 API 级别的验收用例。API 测试通过 **Newman** 执行 Postman Collection JSON 文件。

**双重载体:**
- **设计视图 (本章):** Markdown 表格 — 给人读的测试设计，描述场景和验证意图
- **执行视图 (JSON 文件):** Postman Collection v2.1 — 给 Newman 跑的，含具体请求体、测试脚本、数据构造

JSON 文件格式规范见 `references/api-test-postman-schema.md`。

**API 测试用例规格 (设计视图):**

| 用例 ID | 端点 | 场景 | 前置条件 | 请求 (具体值) | 预期状态码 | 预期响应体 (具体字段+值) | 预期副作用 | Postman JSON 对应 |
|---------|------|------|---------|-------------|-----------|---------------------|-----------|-----------------|
| API-{资源缩写}-001 | POST /api/v1/{r} | 创建成功 | DB 中不存在 `{unique_key}` | `{"field": "concrete_value", "field2": 123}` | 201 | `id: {非空}, status: "ACTIVE", field: "concrete_value"` | DB 新增 1 行，`field` = 请求值 | `item[].name` = "API-{资源缩写}-001: ..." |
| API-{资源缩写}-002 | POST /api/v1/{r} | 字段校验失败 | — | `{"field": ""}` 或 `{}` | 400 | `error: "VALIDATION_ERROR", message: "field is required"` | 无 DB 变更 | 同上 |
| API-{资源缩写}-003 | POST /api/v1/{r} | 重复创建 | DB 中存在 `{unique_key}` | `{"field": "same_value"}` | 409 | `error: "CONFLICT", message: "already exists"` | DB 记录数不变 | 同上 |
| API-{资源缩写}-004 | POST /api/v1/{r} | 认证失败 | — | 无 `Authorization` header | 401 | `error: "UNAUTHORIZED"` | 无 | 同上 |
| API-{资源缩写}-005 | POST /api/v1/{r} | 权限不足 | 使用非授权角色 token | `{"field": "valid", ...}` | 403 | `error: "FORBIDDEN"` | 无 | 同上 |
| API-{资源缩写}-006 | GET /api/v1/{r}/{id} | 查询存在 | 通过 prerequest 创建 | — (使用上一步返回的 id) | 200 | `{完整对象, 与创建时一致}` | 无 | 同上 |
| API-{资源缩写}-007 | GET /api/v1/{r}/{id} | 查询不存在 | — | `/api/v1/{r}/999999` | 404 | `error: "NOT_FOUND", message: "resource not found"` | 无 | 同上 |

**最少要求:** 每个端点 ≥ 3 个用例。必须覆盖: 正常 ×1 + 异常(4xx) ×1 + 认证/权限 ×1。

**请求列必须是具体的 JSON 值:**
```json
// 正例 ✅
{"username": "api-test-001", "email": "api-001@example.com", "password": "Test@123456"}

// 反例 ❌
{"field": "{value}"}
{"body": "..."}
```

**跨端点场景 (流程测试):**

| 用例 ID | 场景 | 步骤 (在 Postman 中用 folder 组织) | 验证点 | Postman JSON |
|---------|------|------|--------|-------------|
| API-FLOW-001 | 创建→查询→更新→删除 | 1. POST 创建 2. `pm.collectionVariables.set('id', ...)` 3. GET 验证 4. PUT 更新 5. GET 验证 6. DELETE 7. GET 验证 404 | 每步状态码和响应体一致 | `item[].item[]` (folder) |

**产出文件 (每个需求生成):**

| 文件 | 路径 | 用途 |
|------|------|------|
| Postman Collection | `_context/memory/sw-shared/tests/api-{requirement_id}.json` | Newman 执行 |
| Environment 文件 | `_context/memory/sw-shared/tests/api-{requirement_id}-env.json` | 环境变量 (baseUrl, tokens) |
| Newman 报告 | `_context/memory/sw-shared/tests/api-{requirement_id}-report.xml` | CI 集成 |

### 10.5 第三层: E2E 测试设计 (端到端集成)

对用户旅程（Section 2.1 + Section 3），定义端到端集成测试用例。这层验证完整流程——从用户入口到数据库再返回用户。

**E2E 用例设计使用独立模板 `references/e2e-test-case-template.md` (sw-tdd-agent)。** 该模板覆盖三大类场景:

| 类别 | 子类型 | 最少要求 |
|------|--------|---------|
| **功能测试** | 正常流程 / 异常流程 / 边界条件 / 状态转换 / 权限控制 | 每旅程 ≥1 happy + ≥1 异常，关键旅程 ≥3 异常 |
| **非功能测试** | 性能 / 安全 / 无障碍 / 可靠性 / 国际化 | 按 business_domain 启用 (见模板 Section 6 场景启用矩阵) |
| **兼容性测试** | 浏览器 / 设备 / 屏幕尺寸 / 网络条件 | 按 business_domain 启用 |
| **自定义扩展** | 场景扩类 / 自定义类别 / 脚本钩子 | 按 `_context/config.yaml` (sw.e2e_extensions) 配置 |

**使用流程:**

1. 加载 `e2e-test-case-template.md` → 根据 `business_domain` 查 Section 6 场景启用矩阵 → 确定应用哪些类别
2. 对每个启用的类别，按模板中的 GIVEN/WHEN/THEN/CLEANUP 结构填充具体用例
3. 填充完成后，用例写入设计文档本节的 "E2E 用例规格" 表中
4. 用例必须遵循执行契约: 自包含、无相互依赖、具体值、可恢复清理

**E2E 用例规格 (汇总表):**

| 用例 ID | 类别 | 子类型 | 用户旅程 | 优先级 | GIVEN (具体) | WHEN (具体) | THEN (具体) | CLEANUP (具体) |
|---------|------|--------|---------|--------|-------------|------------|------------|---------------|
| E2E-{缩写}-001 | functional | happy | {旅程名} | P0 | DB: `users` ... | 1. 打开 `/...`<br>2. `[data-testid="..."]` click | UI: "..." 可见<br>API: 201<br>DB: row+1 | `DELETE FROM ... WHERE ...` |
| E2E-{缩写}-002 | functional | error | {旅程名} | P0 | 同上 | 1-3. ...<br>4. `page.route()` abort | UI: toast "网络失败"<br>DB: 无变更 | 同上 |
| E2E-{缩写}-003 | non-functional | perf | {旅程名} | P1 | ... | 加载页面 | LCP < 2.5s | — |
| E2E-{缩写}-004 | compatibility | browser | {旅程名} | P2 | Firefox 128 | 同 E2E-001 步骤 | UI 同 E2E-001 | 同 E2E-001 |

**最少要求:** 每个用户旅程 ≥ 1 条 happy path (functional)。关键旅程（支付/数据修改/权限变更）≥ 1 条失败恢复 (error) + ≥ 1 条边界 (boundary)。非功能/兼容性按 `business_domain` 矩阵启用。

**数据构造必须写具体值:**
```
# 正例 ✅
起始状态: INSERT INTO users VALUES ('e2e-user-001', 'e2e@test.com', balance=1000.00)
操作步骤: 搜索框输入 "test-product-e2e" → 验证结果显示 ≥ 1 条
验证点: GET /api/v1/orders?userId=e2e-user-001 → 返回 list 中 status=PAID, amount=299.00

# 反例 ❌
起始状态: {初始数据}
操作步骤: {步骤}
验证点: {验证状态/数据}
```

**E2E 执行契约:**
- 每个 E2E 用例必须自包含: 用具体的 SQL/API 准备数据 + 用具体的 SQL/API 清理
- 用例之间不能有顺序依赖（可并行执行）
- 起始状态的每个数据值必须是具体的——表名、字段名、值
- 清理必须恢复到测试前的状态——不能留脏数据污染后续测试

**UI 自动化要素 (当涉及 UI 时):**

| E2E 用例 | 页面 | 元素定位 | 操作 | 等待条件 |
|----------|------|---------|------|---------|
| E2E-{id}-步骤{N} | P-{N}: {页面名} | `button[data-testid="submit"]` | click | `div.success-message` 可见 |
| E2E-{id}-步骤{N} | P-{N}: {页面名} | `input[name="email"]` | type | — |

**`data-testid` 命名规范:** 所有可交互元素必须在页面设计中标注 `data-testid`，E2E 用例仅通过 `data-testid` 定位元素（不依赖 CSS class 或 XPath）。

### 10.6 三层追溯矩阵

确保每个需求 AC 在三层测试中都有对应覆盖:

| 需求 AC | L1 UT (单元) | L2 API (接口) | L3 E2E (端到端) | 覆盖完整? |
|---------|-------------|--------------|----------------|----------|
| AC-1: {标准} | UT-{ids} | API-{ids} | E2E-{ids} | ✅ / ⚠️ 缺 {层} |
| AC-2: {标准} | UT-{ids} | API-{ids} | — (纯逻辑，无旅程) | ✅ |
| AC-3: {标准} | UT-{ids} | — (无独立端点) | E2E-{ids} | ✅ |

**追溯规则:**
- 每个 AC 至少被一层测试覆盖
- 涉及用户交互的 AC → L3 E2E 必须有
- 涉及 API 端点的 AC → L2 API 必须有
- 涉及算法/逻辑的 AC → L1 UT 必须有
- 如果某 AC 在某一层标注为空，需要给出理由（不是漏了）

### 10.7 测试数据策略

- **测试数据来源:** { fixtures 文件 / factory 方法 / 内存数据库 / 实际 DB 快照 }
- **敏感数据处理:** { 脱敏策略: 假名化 / 合成数据 / 专用测试账号 }
- **数据隔离:** { 每个测试独立事务 / 独立 schema / 独立 database }
- **共享夹具:** { 哪些数据需要跨用例共享，放在哪里 }

## 11. 部署注意事项

- **迁移:** {是否需要数据库迁移，是否向后兼容}
- **特性开关:** {是否需要 feature flag}
- **回滚方案:** {如何回滚，预估回滚时间}
- **监控指标:** {新增哪些监控/告警}

## 12. 开放问题

- {在实现前需要澄清的技术不确定性}
- {设计评审中未达成共识的决策}

## 13. 下游引用

- 需求规格: `requirements/{requirement_id}.md`
- 任务拆分: `_context/memory/sw-shared/tasks.yaml`
- 知识库: `_context/memory/sw-shared/knowledge-base/decisions/`
