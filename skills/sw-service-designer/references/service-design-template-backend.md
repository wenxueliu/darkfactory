# 后端服务设计模板 (Backend Service Design Template)

## 使用说明

用于后端服务 (Java/Go/Python/Rust 等) 的详细设计。由 sw-service-designer 加载填充，输出至 `designs/{requirement_id}-service-{service_id}-design.md`。

---

# 服务详细设计: {service_id} (backend)

**设计ID:** `{DESIGN-YYYYMMDD-NNN}-{service_id}`
**关联特性设计:** `designs/{requirement_id}-design.md`
**服务:** `{service_id}` (语言: {language}, 端口: {port})
**状态:** `draft | reviewed | approved`

## S1. 技术决策

| ID | 决策 | 理由 | 替代方案 | 权衡 |
|----|------|------|---------|------|
| D-{svc}-1 | {本服务的技术选型} | {为什么} | {放弃的方案} | {牺牲了什么} |

## S2. 架构设计

### 组件图
```
┌──────────────────────────────────────┐
│  {service_id}                         │
│  ┌──────────┐  ┌──────────┐         │
│  │ {组件 A}  │──│ {组件 B}  │         │
│  └──────────┘  └──────────┘         │
│       │               │              │
│  ┌──────────┐  ┌──────────┐         │
│  │ {组件 C}  │  │ {组件 D}  │         │
│  └──────────┘  └──────────┘         │
└──────────────────────────────────────┘
```

### 数据流
```
INPUT → VALIDATION → BUSINESS LOGIC → PERSISTENCE → OUTPUT
```

### 组件职责

| 组件 | 职责 | 输入 | 输出 | 依赖 |
|------|------|------|------|------|
| {Name} | {一句话职责} | {输入类型} | {输出类型} | {依赖} |

## S3. API/接口设计

### API 端点

| Method | Path | 请求体 | 响应 | 错误码 |
|--------|------|--------|------|--------|
| POST | /api/v1/{resource} | `{json schema}` | `{json schema}` | 201, 400, 409, 500 |
| GET | /api/v1/{resource}/{id} | — | `{json schema}` | 200, 404, 500 |

### 数据模型

```yaml
# {entity_name}
fields:
  - name: {field}
    type: {type}
    nullable: true/false
    constraints: {validation rules}
    description: {business meaning}
```

## S4. 状态管理

### 状态机
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

### 状态转换规则

| 当前状态 | 触发事件 | 目标状态 | 前置条件 | 副作用 |
|---------|---------|---------|---------|--------|
| DRAFT | submit | IN_REVIEW | 必填字段完整 | 发送通知 + 审计日志 |

## S5. 错误处理策略

| 错误场景 | 异常类型 | HTTP 状态码 | 用户消息 | 重试策略 | 日志级别 |
|---------|---------|------------|---------|---------|---------|
| 资源不存在 | ResourceNotFound | 404 | "未找到 {resource}" | 不重试 | WARN |
| 并发冲突 | OptimisticLockException | 409 | "数据已被修改" | 用户手动重试 | WARN |
| 上游超时 | UpstreamTimeout | 503 | "服务暂不可用" | 指数退避 ×3 | ERROR |
| 输入校验失败 | ValidationException | 400 | 具体字段错误 | 不重试 | INFO |
| 内部错误 | InternalException | 500 | "系统错误" | — | ERROR |

**最少要求:** ≥ 5 种异常场景。

## S6. 安全设计

| 关注点 | 方案 | 验证方式 |
|--------|------|---------|
| 认证 | {方案描述} | {测试方式} |
| 授权 | {方案描述} | {测试方式} |
| 输入校验 | {方案描述} | {测试方式} |
| 数据保护 | {方案描述} | {测试方式} |
| 审计日志 | {方案描述} | {测试方式} |

## S7. UT 设计 (L1 — 本服务组件)

加载 `test-case-template.md`。对本服务 S2 中的每个组件设计 UT 用例。

### UT 用例规格

| 用例 ID | 组件 | 被测方法 | 场景类型 | 输入 (具体值) | Mock 依赖 | 预期输出 (具体值) |
|---------|------|---------|---------|-------------|----------|-----------------|
| UT-{缩写}-001 | {组件名} | `{方法}` | happy | `{具体值}` | `{mock}.{method}()` → `{返回值}` | `{具体对象}` |
| UT-{缩写}-002 | {组件名} | `{方法}` | error | `null` / `""` | `{mock}.{method}()` → throws | `throws {Exception}("{msg}")` |
| UT-{缩写}-003 | {组件名} | `{方法}` | boundary | `{边界值}` | — | `{预期}` |

### 数据构造代码块 (每条 UT 用例必须附带)

```
// UT-{缩写}-001: {场景描述}
// === 输入数据构造 ===
var input = new {Type}(field1: "{concrete}", field2: {numeric});
// === Mock 依赖 ===
when({dependency}.{method}()).thenReturn({value});
// === 预期输出 ===
var expected = new {Type}(field1: "{expected}", field2: {numeric});
// === 执行 + 断言 ===
var result = {component}.{method}(input);
assertThat(result).isEqualTo(expected);
```

**最少要求:** 每个 public 方法 ≥ 2 UT 用例 (1 happy + 1 error/boundary)。每个组件 ≥ 1 edge 用例。

### 追溯到需求

| UT 用例 | 覆盖的需求 AC | 覆盖的设计决策 |
|---------|-------------|-------------|
| UT-{id} | AC-{N} | D-{svc}-{N} |

## S8. API 测试设计 (L2 — 本服务端点)

加载 `api-test-case-template.json` 和 `api-test-postman-schema.md`。

### API 测试用例规格

| 用例 ID | 端点 | 场景 | 请求 (具体值) | 预期状态码 | 预期响应体 (具体值) | 预期副作用 |
|---------|------|------|-------------|-----------|-------------------|----------|
| API-{缩写}-001 | POST /api/v1/{r} | 创建成功 | `{"field": "concrete", "field2": 123}` | 201 | `id: {非空}, status: "ACTIVE"` | DB row+1 |
| API-{缩写}-002 | POST /api/v1/{r} | 字段校验失败 | `{"field": ""}` | 400 | `error: "VALIDATION_ERROR"` | 无 DB 变更 |
| API-{缩写}-003 | POST /api/v1/{r} | 认证失败 | 无 Authorization header | 401 | `error: "UNAUTHORIZED"` | 无 |

**最少要求:** 每个端点 ≥ 3 用例 (正常 ×1 + 异常 ×1 + 认证/权限 ×1)。

### 产出文件

| 文件 | 路径 |
|------|------|
| Postman Collection | `tests/api-{requirement_id}-{service_id}.json` |
| Environment | `tests/api-{requirement_id}-{service_id}-env.json` |
