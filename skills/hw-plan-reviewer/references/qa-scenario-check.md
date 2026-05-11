# QAScenarioCheck: QA 场景可执行性判断

本参考提供判断 QA 场景是否"可执行"的完整决策逻辑。加载本参考后，对计划中的每个 QA 场景进行判断。

---

## 可执行 QA 场景的三要素

一个 QA 场景必须同时满足以下 3 个要素才算**可执行**：

### 1. 具体工具 (Specific Tool)

场景必须指定用来验证的工具。可接受的工具形式：

| 类型 | 示例 | 说明 |
|------|------|------|
| HTTP 测试命令 | `curl`、`httpie`、`wget` | 精确的 HTTP 请求 |
| 测试框架命令 | `pytest -k test_name`、`npm test -- -t "test"`、`go test -run TestX` | 测试运行器 |
| 浏览器操作 | 期望的 CSS selector + 操作 | 如 `#login-btn` 元素存在且可点击 |
| 数据库查询 | `psql -c "SELECT ..."`、`mongo --eval "..."` | 数据验证 |
| 脚本命令 | `python scripts/check.py`、`bash verify.sh` | 自定义验证脚本 |
| 日志检查 | `grep "ERROR" /var/log/app.log` | 日志验证 |

不接受的"工具"：

| 不可接受 | 为什么 | 
|----------|--------|
| "手动在浏览器中" | 不是自动化工具，也无法描述具体交互 |
| "肉眼检查" | 主观且不可复现 |
| "让 QA 人员验证" | 委托给未定义的人类，没有工具和步骤 |

### 2. 具体步骤 (Concrete Steps)

步骤必须是可逐步执行的操作序列，不是模糊的方向。

```
可执行:
1. 发送 POST 请求到 /api/users，附带 body {"name":"test","email":"test@example.com"}
2. 检查响应 status code 为 201
3. 从响应中提取 user.id
4. 发送 GET 请求到 /api/users/{user.id}
5. 检查响应 body 中 name 为 "test"

不可执行:
- "测试 CRUD 功能"（太模糊，哪一步？）
- "通过 UI 测试"（没有具体的 UI 操作序列）
- "检查所有字段"（哪几个字段？怎么检查？）
```

### 3. 预期结果 (Expected Results)

预期结果必须是**可验证的断言**，不能是主观评价。

```
可验证的预期（PASS）:
- "status code = 201"
- "响应 JSON 中 data.id 为非空字符串"
- "响应时间 < 200ms"
- "页面包含文本 'Welcome, test'"
- "`grep 'ERROR' app.log | wc -l` 输出 0"
- "数据库 users 表中新增了一条记录"

不可验证的预期（FAIL）:
- "看起来正常" → 主观
- "工作正常" → 主观，没有断言的数值
- "没有明显问题" → 主观
- "用户体验良好" → 主观
- "响应应该是正确的" → 循环推理，没有具体描述什么是"正确"
```

---

## 可执行性决策树

```
对每个 QA 场景:
  │
  ├─ 场景中提到具体工具了吗？
  │   ├─ 否 → FAIL (不可执行: 缺少工具)
  │   └─ 是 → 继续
  │
  ├─ 场景列出了具体步骤（≥2 步）吗？
  │   ├─ 否 → FAIL (不可执行: 缺少步骤)
  │   └─ 是 → 继续
  │
  ├─ 场景给出了可验证的预期结果吗？
  │   ├─ 否 → FAIL (不可执行: 缺少预期结果)
  │   └─ 是 → PASS (可执行)
```

---

## 具体示例

### 可执行的 QA 场景 ✓

#### 示例 1: curl 命令（后端 API）

```
QA for Task 2 (user registration API):
- 工具: curl
- 步骤:
  1. curl -X POST http://localhost:3000/api/register \
     -H "Content-Type: application/json" \
     -d '{"username":"testuser","password":"Test1234!"}'
  2. 检查 status code 为 201
  3. 提取 token: echo $RESPONSE | jq -r '.token'
  4. 用 token 请求受保护端点: curl http://localhost:3000/api/me -H "Authorization: Bearer $TOKEN"
- 预期: 步骤 2 → status 201，步骤 4 → status 200 + 响应 body 含 username "testuser"
```

判定: **PASS** — 有具体工具(curl)，有 4 步具体操作，每一步都有可验证的预期(status code + JSON 字段)。

#### 示例 2: 测试运行器（单元测试）

```
QA for Task 3 (user validation logic):
- 工具: pytest
- 步骤:
  1. 运行: pytest tests/test_user_validation.py -v
  2. 确认 "test_validate_email_invalid" 状态为 FAILED (RED phase)
  3. 补充验证逻辑使该测试通过
  4. 重新运行: pytest tests/test_user_validation.py -v
- 预期: 所有 test_user_validation 测试 GREEN (PASSED)
```

判定: **PASS** — 工具是 pytest，有具体测试文件路径和预期结果(GREEN/PASSED)。

#### 示例 3: 浏览器元素验证

```
QA for Task 5 (login page UI):
- 工具: 浏览器 / Playwright
- 步骤:
  1. 访问 http://localhost:3000/login
  2. 检查 input#username 元素存在且可聚焦
  3. 检查 input#password 元素存在且 type="password"
  4. 检查 button[type="submit"] 文本为 "Sign In"
  5. 提交空表单，检查 .error-message 元素显示 "Username is required"
- 预期: 
  - 步骤 2-4 → 对应元素存在于 DOM 且属性正确
  - 步骤 5 → .error-message 可见且包含指定文本
```

判定: **PASS** — 工具是浏览器，有 5 步具体操作(selector + 交互)，预期结果绑定到具体 DOM 元素和文本。

---

### 不可执行的 QA 场景 ✗

#### 示例 4: 主观判断（典型不可执行）

```
QA for Task 4:
- 确认功能正常
- 检查页面没有问题
- 验证用户体验良好
```

判定: **FAIL** — 无工具，无步骤，三个预期全是主观评价。

#### 示例 5: "手动检查"（无工具）

```
QA for Task 2:
- 手动在浏览器中测试所有 API 接口
```

判定: **FAIL** — "手动在浏览器中测试"不是可复现的工具。"所有 API 接口"没有列出具体端点。无预期结果。

#### 示例 6: 工具存在但预期主观

```
QA for Task 3:
- 工具: curl
- 步骤: 发送 GET /api/health
- 预期: 看起来应该正常
```

判定: **FAIL** — 有工具和步骤，但预期"看起来应该正常"是主观的。应改为: `预期 status 200, body {"status":"ok"}`。

#### 示例 7: 步骤太模糊

```
QA for Task 1:
- 工具: pytest
- 步骤: 运行测试
- 预期: 测试通过
```

判定: **FAIL** — 有工具(pytest)但步骤只有"运行测试"——没有指定测试文件、测试名称。预期"测试通过"也没有具体说明是哪些测试。应改为 `pytest tests/test_auth.py::test_login_success -v`，预期输出 `PASSED`。

---

## 边界情况处理

### 情况: QA 场景在验收标准中

```
任务没有独立的 QA 区段，但在验收标准中有:
Acceptance Criteria:
- 发送 POST 请求返回 201
- GET 请求返回包含创建资源的 200 响应
```

**判定: OKAY。** 验收标准中的验证步骤起到 QA 场景的作用，只要它们满足三要素要求。但如果验收标准也是主观的（"功能符合预期"），则仍 FAIL。

### 情况: QA 场景引用另一个测试文件

```
QA for Task 2: 见 tests/integration/test_users.py 中的 test_user_crud 测试
```

**判定: OKAY。** 只要引用路径是有效的（文件实际存在），则接受。验证该文件是否存在，如果存在包含合理的测试逻辑，PASS。

### 情况: 只有部分任务有 QA 场景

```
Task 1: 有 QA 场景
Task 2: 有 QA 场景
Task 3: 无 QA 场景
Task 4: QA: "手动测试"
```

**判定: REJECT。** Task 3 缺少 QA 场景，Task 4 的 QA 场景不可执行。两个问题，都在 3 个限制内，列出。

---

## 汇总表: QA 场景快速判断

| 工具 | 步骤 | 预期 | 判定 |
|------|------|------|------|
| 具体(curl, pytest, etc.) | 明确(≥2 步) | 可验证(status/值/文本) | **PASS** |
| 具体 | 明确 | 主观("正常","没问题") | **FAIL** |
| 具体 | 模糊("运行测试") | 可验证 | **FAIL** |
| 缺失("手动","肉眼") | 无论 | 无论 | **FAIL** |
| 具体 | 明确 | 缺失 | **FAIL** |
| 缺失 | 缺失 | 缺失 | **FAIL** |
