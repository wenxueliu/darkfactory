# 前端服务设计模板 (Frontend Service Design Template)

## 使用说明

用于前端服务 (React/Vue/Angular 等) 的详细设计。

---

# 服务详细设计: {service_id} (frontend)

**设计ID:** `{DESIGN-YYYYMMDD-NNN}-{service_id}`
**关联特性设计:** `designs/{requirement_id}-design.md`
**服务:** `{service_id}` (语言: {language})
**状态:** `draft | reviewed | approved`

## S1. 技术决策

| ID | 决策 | 理由 | 替代方案 | 权衡 |
|----|------|------|---------|------|
| D-{svc}-1 | {UI 框架} | {为什么} | {放弃的方案} | {牺牲了什么} |
| D-{svc}-2 | {状态管理库} | {为什么} | {放弃的方案} | {牺牲了什么} |

## S2. 组件架构

### 组件树
```
<App>
├── <Layout>
│   ├── <Header> → <NavBar>, <UserMenu>
│   ├── <MainContent>
│   │   ├── <{PageComponent}>
│   │   │   ├── <{FeaturePanel}>
│   │   │   └── <{SidePanel}>
│   │   └── <ErrorBoundary>
│   └── <Footer>
```

### 组件规格

| 组件 | 职责 | Props | State | 事件 | 复用? |
|------|------|-------|-------|------|-------|
| {Component} | {职责} | `{prop}: {type}` | `{state}` | `{event}` → `{handler}` | 已有/新建 |

### 路由设计

| 路由 | 页面组件 | 权限 | 数据预加载 |
|------|---------|------|----------|
| `/path/:param` | {PageName} | {role} | {API calls} |

## S3. API 集成

| 组件 | 调用 API | 方法 | 请求数据来源 | 响应处理 | Loading | Error |
|------|---------|------|------------|---------|---------|-------|
| {Component} | {endpoint} | GET/POST | {props/state} | {存储到 state} | Skeleton | ErrorBoundary |

### API Client 配置
- Base URL: `{base_url}`
- 认证方式: Bearer Token / Cookie / Session
- 请求拦截: token 注入
- 响应拦截: 401 → 跳转登录, 5xx → 重试/提示

## S4. 客户端状态管理

```typescript
interface AppState {
  {domain}: {
    {entity}: {Entity}[];
    selected{Entity}: {Entity} | null;
    loading: boolean;
    error: string | null;
  };
}
```

| Action | 触发时机 | 状态变更 | 副作用 (API 调用) |
|--------|---------|---------|-----------------|
| `fetch{Entities}` | 页面加载 | loading=true → data=... | GET /api/v1/{r} |
| `create{Entity}` | 表单提交 | 追加到列表 | POST /api/v1/{r} |

## S5. 错误处理与降级 UI

| 错误场景 | 组件表现 | 用户行动 |
|---------|---------|---------|
| API 超时 | Toast: "请求超时" + 保留表单 | 点击重试 |
| API 500 | ErrorBoundary 降级 UI + "系统繁忙" | 刷新页面 |
| 网络断开 | 全局提示: "网络已断开" | 恢复后自动重试 |
| 空列表 | 空状态插图 + "暂无数据" + 创建引导 | 点击创建 |
| 404 页面 | 404 页面 + 返回首页链接 | 点击返回 |

## S6. 安全设计

| 关注点 | 方案 |
|--------|------|
| XSS 防护 | 框架默认转义 + DOMPurify (如有 rich text) |
| Token 存储 | httpOnly cookie (首选) / memory only / 禁止 localStorage |
| CSP | `Content-Security-Policy` header |
| 敏感数据 | 不在 URL/console.log 暴露 PII |
| 点击劫持 | `X-Frame-Options: DENY` |

## S7. UT 设计 (L1 — 组件测试)

加载 `test-case-template.md`。

| 框架 | 覆盖目标 |
|------|---------|
| Jest + Testing Library / Vitest / ... | 核心组件 ≥ 80% |

### UT 用例规格

| 用例 ID | 组件 | 场景类型 | Props/State | 用户交互 | 预期渲染/行为 |
|---------|------|---------|------------|---------|-------------|
| UT-{缩写}-001 | {Component} | happy | `{props}` | — | 渲染 {elements} |
| UT-{缩写}-002 | {Component} | user-action | `{props}` | click({button}) | {callback} 被调用 |
| UT-{缩写}-003 | {Component} | error | `error={msg}` | — | 渲染 error UI |

**最少要求:** 每个组件 ≥ 2 UT 用例 (1 render + 1 interaction/error)。

## S8. API 集成测试设计 (L2)

加载 `api-test-case-template.json`。

| 用例 ID | 测试场景 | Mock API | 期望行为 |
|---------|---------|---------|---------|
| INT-{缩写}-001 | 数据加载成功 | `GET /api/v1/{r}` → 200 + data | 列表渲染 N 条 |
| INT-{缩写}-002 | 数据加载失败 | `GET /api/v1/{r}` → 500 | 显示 error UI + 重试按钮 |
| INT-{缩写}-003 | 创建成功 | `POST /api/v1/{r}` → 201 | 跳转到详情页 |

**最少要求:** 每个 API 集成点 ≥ 2 用例 (1 success + 1 error)。
