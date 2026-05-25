# BFF 服务设计模板 (BFF Service Design Template)

## 使用说明

用于 BFF (Backend For Frontend) 服务的详细设计。BFF 是前端专属的后端聚合层。

---

# 服务详细设计: {service_id} (bff)

**设计ID:** `{DESIGN-YYYYMMDD-NNN}-{service_id}`
**关联特性设计:** `designs/{requirement_id}-design.md`
**服务:** `{service_id}` (语言: {language})
**状态:** `draft | reviewed | approved`

## S1. 技术决策

| ID | 决策 | 理由 | 替代方案 | 权衡 |
|----|------|------|---------|------|
| D-{svc}-1 | {BFF 框架} | {为什么} | {放弃的方案} | {牺牲了什么} |

## S2. BFF 架构

### 聚合模式
```
Frontend → BFF → ┬→ {backend-service-A}
                  ├→ {backend-service-B}
                  └→ {backend-service-C}
```

### 路由与聚合映射

| BFF 端点 | 前端用途 | 聚合的后端调用 | 聚合策略 |
|---------|---------|-------------|---------|
| GET /api/bff/{page_data} | {页面名} 初始化 | user-service + order-service | 并行请求 |
| POST /api/bff/{action} | {操作名} | user-service → order-service | 串行链式 |

## S3. API 设计 (双面)

### 前端面 (对 Frontend 暴露)

| Method | Path | 请求体 | 响应体 | 说明 |
|--------|------|--------|--------|------|
| GET | /api/bff/{resource} | — | `{aggregated}` | {说明} |

### 后端面 (调用的后端服务)

| 后端服务 | 端点 | 调用时机 | 超时 | 降级 |
|---------|------|---------|------|------|
| user-service | GET /api/v1/users/{id} | {条件} | 2s | 返回缓存或 null |
| order-service | GET /api/v1/orders?userId={id} | {条件} | 3s | 返回空列表 |

## S4. 数据聚合与转换

### 聚合逻辑

```
function aggregate{PageData}(userId): {PageData} {
    const [user, orders] = await Promise.all([...]);
    return { user: transformUser(user), recentOrders: orders.slice(0, 5) };
}
```

### 转换规则

| 源字段 (后端) | 目标字段 (前端) | 转换逻辑 |
|-------------|---------------|---------|
| `user.created_at` | `memberSince` | `formatDate(created_at, locale)` |
| `order.amount_cents` | `amount` | `amount_cents / 100` |

## S5. 错误处理与降级

| 后端服务故障 | BFF 行为 | 前端看到的效果 |
|------------|---------|-------------|
| user-service 超时 | 返回缓存值 (如有) / null | 用户信息骨架或缓存 |
| order-service 500 | 返回空列表 + `orderError: true` | 订单区域 "加载失败" + 重试 |
| 全部后端不可用 | 返回 503 | 全页降级 UI |

## S6. 安全设计

| 关注点 | 方案 |
|--------|------|
| 认证传播 | 从 Cookie/Header 提取 token → 转发后端 |
| 数据过滤 | BFF 层过滤不应返前端的字段 (内部 ID、审计字段) |
| 速率限制 | 按用户/IP 限制 BFF 端点调用频率 |
| 输入校验 | 校验前端传入参数，不信任客户端 |

## S7. UT 设计 (L1)

加载 `test-case-template.md`。

| 用例 ID | 被测函数 | 场景 | Mock 后端 | 预期输出 |
|---------|---------|------|---------|---------|
| UT-{缩写}-001 | `aggregate{PageData}` | 全部后端正常 | user+orders 正常 | 聚合数据正确 |
| UT-{缩写}-002 | `aggregate{PageData}` | 部分后端超时 | user 超时 | 缓存值 + orders 正常 |
| UT-{缩写}-003 | `aggregate{PageData}` | 全部后端失败 | 全部 500 | throw Error |

**最少要求:** 每个聚合函数 ≥ 3 UT 用例 (全正常 + 部分失败 + 全部失败)。

## S8. API 测试设计 (L2)

加载 `api-test-case-template.json`。

| 用例 ID | BFF 端点 | 场景 | Mock 后端状态 | 预期状态码 | 预期响应 |
|---------|---------|------|-------------|-----------|---------|
| API-{缩写}-001 | GET /api/bff/{data} | 全部后端正常 | 全部 200 | 200 | 聚合数据 |
| API-{缩写}-002 | GET /api/bff/{data} | 部分后端故障 | user 503 | 200 | 部分数据 + error flag |
| API-{缩写}-003 | GET /api/bff/{data} | 全部后端故障 | 全部 503 | 503 | error |

**最少要求:** 每个 BFF 端点 ≥ 3 用例。
