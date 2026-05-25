# E2E 设计协调 (E2E Design Coordination)

## 核心理念

E2E 测试设计的目标是基于 Stage 1 的用户旅程和 Stage 2 的 per-service API 契约，设计跨服务的端到端测试用例。E2E 不属于任何单一服务——它验证的是整个系统在用户视角下的行为。

**E2E 设计文档是测试执行阶段的输入——由 Playwright/Cypress 等框架运行，验证完整用户旅程。**

## 协调流程 (4 步)

### 第 1 步: 输入加载

1. 读取 Stage 1 输出: `designs/{requirement_id}-design.md`
   - Section 3: 用户旅程设计 (交互流程 + 关键时刻 + 交互状态矩阵)
   - Section 5: 服务交互设计 (跨服务调用序列、SLA、降级策略)
   - Section 6: 跨服务契约
2. 读取所有 Stage 2 输出: `designs/{requirement_id}-service-*-design.md`
   - 每个服务的 S3: API/接口设计 (端点、数据模型)
   - 每个服务的 S5: 错误处理策略
3. 读取配置: `_bmad/config.yaml` → `hw.business_domain` (驱动场景启用矩阵)
4. 读取扩展配置: `_bmad/config.yaml` → `hw.e2e_extensions` (自定义场景/类别/钩子)

### 第 2 步: 场景规划

加载 `references/e2e-test-case-template.md`，根据 `business_domain` 查 Section 6 场景启用矩阵:

| 类别 | 需要确定的内容 |
|------|-------------|
| 功能-正常 | 从用户旅程 (Section 3.1) 提取每个旅程的 happy path 步骤 |
| 功能-异常 | 从错误处理策略 (per-service S5) 提取跨服务异常场景 |
| 功能-边界 | 识别涉及多服务协作的边界条件 |
| 功能-状态转换 | 从 per-service S4 状态机提取跨服务的状态转换 |
| 功能-权限 | 从 per-service S6 提取跨服务权限验证 |
| 非功能-性能 | 从服务交互 SLA (Section 5) 提取 E2E 性能阈值 |
| 非功能-安全 | 检查跨服务安全关注点 (Token 传播、数据泄露) |
| 非功能-可靠性 | 从降级策略 (Section 5) 提取 E2E 可靠性场景 |
| 兼容性 | 按 domain 矩阵确定浏览器/设备/屏幕/网络覆盖 |
| 自定义 | 加载 `hw.e2e_extensions` 配置 |

### 第 3 步: 用例填充

对每个确定的场景类别，按 `e2e-test-case-template.md` 的 GIVEN/WHEN/THEN/CLEANUP 结构填充:

#### 功能 E2E

```
GIVEN {起始状态: 哪些服务的 DB 要有数据，数据具体值是什么}
WHEN  {用户操作序列: 页面路由 + data-testid + 操作 + 等待条件}
THEN  {UI 断言 + API 断言 (跨服务) + DB 断言 (跨服务)}
CLEANUP {回滚所有受影响服务的测试数据}
```

**数据构造关键点:** 
- GIVEN 中的起始数据分布在多个服务的数据库中
- CLEANUP 需要清理所有受影响服务的测试数据
- 每个值必须是具体的 (表名、字段名、值)

#### 非功能 E2E

性能、安全、可靠性场景基于服务交互 SLA 和降级策略:
- 性能: 从 Section 5 的 SLA 表提取阈值
- 安全: 从 per-service S6 提取跨服务安全验证
- 可靠性: 从 Section 5 的降级策略提取故障注入场景

#### 兼容性 E2E

按 domain 矩阵选择浏览器/设备/屏幕/网络条件组合。

#### 自定义 E2E

如果 `hw.e2e_extensions.custom_categories` 有定义，逐类别填充。

### 第 4 步: 输出

**输出产物:**
- 写入 `designs/{requirement_id}-e2e-design.md`

**过渡条件 (E2E 设计完成):**
- [ ] 每个用户旅程 ≥ 1 条 functional happy E2E
- [ ] 关键旅程 ≥ 1 条 functional error E2E + ≥ 1 条 boundary E2E
- [ ] 非功能场景按 domain 矩阵最少数量达标
- [ ] 兼容性场景按 domain 矩阵覆盖
- [ ] 自定义扩展场景 (如配置) 已填充
- [ ] 所有 E2E 用例的 GIVEN/WHEN/THEN/CLEANUP 都是具体值
- [ ] 每个 E2E 用例自包含 (无跨用例隐式依赖)

**完成确认语:** "E2E 测试设计完成。功能: {N} 用例, 非功能: {M} 用例, 兼容性: {K} 用例, 自定义: {J} 用例。共计 {T} 条 E2E 场景。"

## 与其他阶段的集成

| 上游 | 集成方式 |
|------|---------|
| Stage 1 特性设计 | 用户旅程 (Section 3) → E2E 功能场景 |
| Stage 1 特性设计 | 服务交互 SLA (Section 5) → E2E 性能场景 |
| Stage 1 特性设计 | 降级策略 (Section 5) → E2E 可靠性场景 |
| Stage 2 Per-service 设计 | API 端点 + 数据模型 → E2E GIVEN 数据构造 |
| Stage 2 Per-service 设计 | 错误处理策略 → E2E 异常场景 |
| Stage 2 Per-service 设计 | 安全方案 → E2E 安全场景 |
