# API 测试 — Postman Collection JSON 规范

## 概述

API 层测试用例使用 Postman Collection v2.1 JSON 格式承载，通过 Newman 命令行执行。设计文档（Section 10.3）中的 API 测试用例表是**设计视图**（给人读的），JSON 文件是**执行视图**（给 Newman 跑的）。二者必须一一对应。

## 文件组织

```
_bmad/memory/hw-shared/tests/
├── api-{requirement_id}.json          # Postman Collection — 所有 API 测试用例
├── api-{requirement_id}-env.json      # Postman Environment — 变量（baseUrl, tokens, 动态值）
└── api-{requirement_id}-data.json     # 测试数据文件 (Newman -d 参数) — 数据驱动测试的数据集
```

## Postman Collection 结构模板

### 必须遵循的 Schema

- Schema 版本: `https://schema.getpostman.com/json/collection/v2.1.0/collection.json`
- 文件编码: UTF-8
- 变量命名: camelCase，环境变量用 `{{doubleBraces}}`

### Collection 骨架

```json
{
  "info": {
    "name": "{requirement_id} — {需求标题}",
    "description": "关联设计: designs/{requirement_id}-design.md\n生成时间: {timestamp}",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "baseUrl",
      "value": "http://localhost:8080",
      "type": "string"
    },
    {
      "key": "authToken",
      "value": "",
      "type": "string"
    }
  ],
  "item": []
}
```

### 单个测试用例结构

```json
{
  "name": "API-{resource}-{NNN}: {场景描述}",
  "event": [
    {
      "listen": "test",
      "script": {
        "id": "{uuid}",
        "type": "text/javascript",
        "exec": [
          "// === 状态码验证 ===",
          "pm.test('[API-{resource}-{NNN}] 状态码应为 {expected_status}', function () {",
          "    pm.response.to.have.status({expected_status});",
          "});",
          "",
          "// === 响应体结构验证 ===",
          "pm.test('[API-{resource}-{NNN}] 响应体应包含 {字段名}', function () {",
          "    pm.response.to.have.jsonBody('{field_path}');",
          "});",
          "",
          "// === 响应体数据验证 ===",
          "pm.test('[API-{resource}-{NNN}] {字段} 应为 {期望值}', function () {",
          "    pm.expect(pm.response.json().{field}).to.eql({expected_value});",
          "});",
          "",
          "// === 副作用验证 (如有) ===",
          "pm.test('[API-{resource}-{NNN}] {副作用描述}', function () {",
          "    // 如: 检查 DB 记录数、检查缓存状态",
          "    // 通过 pm.sendRequest 做额外的 GET 请求验证数据已持久化",
          "    pm.sendRequest({",
          "        url: `${pm.variables.get('baseUrl')}/api/v1/{resource}/${pm.response.json().id}`,",
          "        method: 'GET'",
          "    }, function (err, res) {",
          "        pm.expect(res.status).to.eql(200);",
          "        pm.expect(res.json().status).to.eql('{expected_status}');",
          "    });",
          "});"
        ]
      }
    },
    {
      "listen": "prerequest",
      "script": {
        "id": "{uuid}",
        "type": "text/javascript",
        "exec": [
          "// === 前置条件: 数据准备 ===",
          "// 如果测试需要先创建依赖数据",
          "// pm.sendRequest({...}) 创建前置资源",
          "",
          "// === 动态变量生成 ===",
          "// 用时间戳保证唯一性，避免测试数据冲突",
          "const ts = Date.now();",
          "pm.variables.set('unique_id', ts);",
          "pm.variables.set('unique_email', `test-${ts}@example.com`);"
        ]
      }
    }
  ],
  "request": {
    "method": "{GET|POST|PUT|PATCH|DELETE}",
    "url": {
      "raw": "{{baseUrl}}/api/v1/{resource}/{path_param}",
      "host": ["{{baseUrl}}"],
      "path": ["api", "v1", "{resource}", "{path_param}"],
      "query": [
        {
          "key": "{param_name}",
          "value": "{param_value}",
          "description": "{参数说明}"
        }
      ]
    },
    "header": [
      {
        "key": "Content-Type",
        "value": "application/json"
      },
      {
        "key": "Authorization",
        "value": "Bearer {{authToken}}"
      }
    ],
    "body": {
      "mode": "raw",
      "raw": "{\n  \"{field}\": \"{concrete_value}\",\n  \"{field2}\": {numeric_value}\n}",
      "options": {
        "raw": {
          "language": "json"
        }
      }
    }
  }
}
```

## 用例命名规范

```
API-{资源缩写}-{NNN}: {场景描述}

示例:
  API-USER-001: 创建用户成功 — 必填字段完整
  API-USER-002: 创建用户失败 — email 格式无效
  API-USER-003: 创建用户失败 — email 重复
  API-USER-004: 创建用户失败 — 无认证 Token
  API-USER-005: 查询用户成功 — ID 存在
  API-USER-006: 查询用户失败 — ID 不存在
```

命名必须与设计文档 Section 10.3 的 `用例 ID` 列一一对应。

## 测试脚本编写规范

### pm.test() 命名格式

```
[用例ID] 断言描述

示例:
  pm.test('[API-USER-001] 状态码应为 201', ...)
  pm.test('[API-USER-001] 响应体应包含 id 字段', ...)
  pm.test('[API-USER-001] email 应为请求中发送的值', ...)
```

### 必须验证的维度

每个正常路径 (happy path) 用例必须包含:

| 验证维度 | Newman 脚本 | 说明 |
|---------|------------|------|
| 状态码 | `pm.response.to.have.status(N)` | 201/200/204/... |
| 响应体结构 | `pm.response.to.have.jsonBody('field')` | 必填字段存在 |
| 字段类型 | `pm.expect(typeof res.field).to.eql('string')` | 类型正确 |
| 字段值 | `pm.expect(res.field).to.eql(expected)` | 值正确（与请求数据一致） |
| 副作用 | `pm.sendRequest(GET /.../id)` | 数据已持久化（POST/PUT/PATCH） |
| 响应时间 | `pm.expect(pm.response.responseTime).to.be.below(N)` | 性能 SLA |

每个异常路径 (error) 用例必须包含:

| 验证维度 | Newman 脚本 |
|---------|------------|
| 状态码 | `pm.response.to.have.status(4xx/5xx)` |
| 错误结构 | `pm.response.to.have.jsonBody('error')` |
| 错误消息 | `pm.expect(res.error.message).to.include('expected_text')` |
| 无副作用 | 确认数据未被修改（如: GET 查询应返回原始状态） |

### pm.expect vs pm.response.to.have

```
# 状态码 — 用 to.have
pm.response.to.have.status(201);

# 响应头 — 用 to.have
pm.response.to.have.header('Content-Type', 'application/json');

# 字段存在性 — 用 to.have.jsonBody
pm.response.to.have.jsonBody('data.id');

# 字段值 — 用 pm.expect + to.eql/to.include/to.be.above
pm.expect(pm.response.json().data.email).to.eql('test@example.com');
pm.expect(pm.response.json().error.message).to.include('not found');
pm.expect(pm.response.json().data.length).to.be.above(0);

# 响应时间 — 用 pm.expect + to.be.below
pm.expect(pm.response.responseTime).to.be.below(500);
```

## 测试数据构造 (Test Data Construction)

**这是 AI 能够自动验证的前提。** 所有输入数据必须是**具体的、可执行的值**——不能是 `{field}` 这样的占位符。

### 数据硬编码 vs 动态变量

| 场景 | 方式 | 示例 |
|------|------|------|
| 固定值（与预期输出强关联） | 硬编码在 body 中 | `"email": "test@example.com"` |
| 需要唯一性（如唯一键） | `pm.variables.set` 动态生成 | `` `test-${ts}@example.com` `` |
| 跨用例复用（如创建后 ID） | `pm.collectionVariables.set` | `pm.collectionVariables.set('userId', res.id)` |
| 环境相关（如 baseUrl） | 环境变量 `{{baseUrl}}` | `{{baseUrl}}/api/v1/users` |

### 数据构造原则

1. **每个用例的数据自包含。** 用例之间不能有隐式依赖（如: 用例 B 依赖用例 A 的执行结果）。如果必须依赖，用 `pm.sendRequest` 在 prerequest 中显式创建。
2. **清理后不影响其他用例。** DELETE 在 test 脚本的最后执行，或使用独立的数据集。
3. **敏感数据永不硬编码。** Token、密码、密钥 → 环境变量 `{{variable}}`。
4. **值必须与设计文档中的预期一致。** 设计文档 10.3 表中的"请求"列和 JSON 中的 `body.raw` 必须完全一致。

### 数据构造示例

```javascript
// === Prerequest: 构造测试数据 ===
const ts = Date.now();

// 硬编码 + 动态组合
pm.variables.set('testUser', JSON.stringify({
    username: `testuser-${ts}`,
    email: `testuser-${ts}@example.com`,
    password: 'Test@123456',    // 固定测试密码
    role: 'member'
}));

// 跨用例共享 ID
pm.collectionVariables.set('createdUserId', '');  // 初始化为空
```

```javascript
// === Test: 验证数据已持久化 ===
const createdId = pm.response.json().id;
pm.collectionVariables.set('createdUserId', createdId);  // 保存给后续用例

// 通过额外请求验证副作用
pm.sendRequest({
    url: `${pm.variables.get('baseUrl')}/api/v1/users/${createdId}`,
    method: 'GET',
    header: { 'Authorization': `Bearer ${pm.variables.get('authToken')}` }
}, function (err, res) {
    pm.expect(res.status).to.eql(200);
    pm.expect(res.json().email).to.eql(JSON.parse(pm.variables.get('testUser')).email);
});
```

## Environment 文件模板

```json
{
  "name": "{requirement_id} — 测试环境",
  "values": [
    {
      "key": "baseUrl",
      "value": "http://localhost:8080",
      "type": "default",
      "enabled": true
    },
    {
      "key": "authToken",
      "value": "",
      "type": "default",
      "enabled": true
    },
    {
      "key": "testTimeout",
      "value": "10000",
      "type": "default",
      "enabled": true
    }
  ]
}
```

## Newman 执行命令

```bash
# 基础执行
newman run _bmad/memory/hw-shared/tests/api-{requirement_id}.json \
  -e _bmad/memory/hw-shared/tests/api-{requirement_id}-env.json \
  --reporters cli,junit \
  --reporter-junit-export _bmad/memory/hw-shared/tests/api-{requirement_id}-report.xml

# 数据驱动执行 (如有多个数据集)
newman run _bmad/memory/hw-shared/tests/api-{requirement_id}.json \
  -e _bmad/memory/hw-shared/tests/api-{requirement_id}-env.json \
  -d _bmad/memory/hw-shared/tests/api-{requirement_id}-data.json

# CI 模式 — 失败立即退出 + 超时
newman run _bmad/memory/hw-shared/tests/api-{requirement_id}.json \
  -e _bmad/memory/hw-shared/tests/api-{requirement_id}-env.json \
  --bail \
  --timeout-request 10000
```

## 与设计文档的双向追溯

| 设计文档 (Section 10.3) | Postman JSON |
|------------------------|--------------|
| `用例 ID` 列 | `item[].name` 的前缀 |
| `请求` 列 | `item[].request.body.raw` |
| `预期状态码` 列 | `pm.test('状态码...')` 脚本 |
| `预期响应体` 列 | `pm.test('响应体...')` 脚本 |
| `预期副作用` 列 | `pm.sendRequest` 验证逻辑 |

**一致性检查:**
- 设计文档中的每个 API 用例 → Postman JSON 中必须有对应的 item
- Postman JSON 中的每个 item → 设计文档中必须有对应的行
- 请求体中的具体值与设计文档中描述的数据必须一致
- 执行 `newman run` 时，如果设计文档和 JSON 不一致 → 以 JSON 为准，同时更新设计文档

## 输出产物

| 产物 | 路径 | 用途 |
|------|------|------|
| Postman Collection | `tests/api-{requirement_id}.json` | Newman 执行的主文件 |
| Environment 文件 | `tests/api-{requirement_id}-env.json` | 环境变量配置 |
| 测试数据文件 (可选) | `tests/api-{requirement_id}-data.json` | 数据驱动测试 |
| Newman 执行报告 | `tests/api-{requirement_id}-report.xml` | CI 集成 |
