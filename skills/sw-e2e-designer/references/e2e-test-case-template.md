# E2ETestCaseTemplate: 端到端测试用例模板

## What This Is

端到端 (E2E) 测试用例的结构化设计模板。覆盖功能、非功能、兼容性三大类测试场景，并支持用户自定义扩展。E2E 验证从用户入口到数据库再返回的完整链路——跨页面、跨组件、跨服务。

**定位:** 设计阶段由 sw-controller 加载，填充后写入设计文档 Section 10.5。执行阶段由 `sw-browser-tester` 生成 Playwright `.spec.ts` 脚本并通过 `npx playwright test` 运行。E2E 不在 TDD Agent 的两层循环（UT+API）内——E2E 用例在 UT+API 全量通过后再执行。

## When to Use

设计文档编写到 Section 10.5 时加载此模板。根据需求特征和 `business_domain` 配置，选择适用的场景类别。

---

## 1. 用例元数据 (统一格式，所有类别共用)

| Field | Value |
|-------|-------|
| **Test ID** | `E2E-{缩写}-{NNN}` (e.g., `E2E-CART-001`, `E2E-AUTH-005`) |
| **Category** | `functional` / `non-functional` / `compatibility` / `custom:{name}` |
| **Subcategory** | `happy` / `error` / `boundary` / `state` / `auth` / `perf` / `security` / `a11y` / `reliability` / `i18n` / `browser` / `device` / `network` / `custom:{name}` |
| **Priority** | P0 / P1 / P2 / P3 |
| **Related Requirement** | AC-{N} 或 Task ID |
| **Related User Journey** | Section 2.1 中的旅程名，标注 N/A 如不涉及 UI |
| **Framework** | Playwright / Cypress / Selenium / 其他 |

---

## 2. 功能测试场景 (Functional)

### 2.1 正常流程 (Happy Path)

验证用户完成目标的最短成功路径。每个用户旅程至少 1 条。

```
GIVEN {起始状态: 用户已登录 / 购物车有商品 / 余额充足 / ...}
WHEN  {用户依次执行: 步骤1 → 步骤2 → 步骤3 → ...}
THEN  {预期结果}
AND   {持久化验证: DB/API 状态一致}
```

| 设计要素 | 要求 | 示例 |
|---------|------|------|
| 起始状态 | 具体的数据行、配置、权限 | `INSERT INTO users VALUES ('e2e-u-001', 'e2e@test.com', role='member', balance=1000.00)` |
| 操作步骤 | 每步含: 页面路由 + 元素定位(data-testid 必填) + 操作 + 等待条件 | `1. 打开 /products → 2. data-testid="search-input" type "test-product" → 3. 等待 .result-list 可见 → 4. data-testid="buy-btn" click` |
| 选择器 | **必须指定 `data-testid`**，供 `sw-browser-tester` 生成 Playwright 脚本使用。回退: ARIA role/name → text → CSS class | `data-testid="search-input"`, `data-testid="buy-btn"`, `data-testid="order-number"` |
| 验证点 | UI 断言 + API 断言 + DB 断言 | `页面显示"支付成功" AND GET /orders?userId=e2e-u-001 → status=PAID AND DB orders 表 status='PAID'` |
| 数据清理 | 具体的 DELETE/UPDATE 语句，恢复原始状态 | `DELETE FROM orders WHERE user_id='e2e-u-001'; UPDATE inventory SET stock=100 WHERE id=1` |

**最少要求:** 每个用户旅程 ≥ 1 条。

### 2.2 异常流程 (Error Path)

验证系统在异常输入/操作下的行为。每个用户旅程覆盖主要失败分支。

| 异常类型 | 触发方式 | 验证点 |
|---------|---------|--------|
| **输入校验失败** | 提交空表单、非法格式、超长输入 | 前端错误提示可见 + 数据未写入 DB |
| **服务器错误** | Mock API 返回 500 / 模拟后端宕机 | 用户看到友好错误页 + 重试按钮可用 |
| **网络中断** | 断网 / 超时 (Playwright `route.abort()`) | 离线提示可见 + 数据不丢失 |
| **并发冲突** | 两个用户同时修改同一资源 | 后者看到冲突提示 + 数据一致性保持 |
| **资源不存在** | 访问已删除的资源 ID | 404 页面 + 引导回首页 |
| **会话过期** | Token 过期后继续操作 | 跳转登录页 + 未保存数据提示 |
| **支付失败** | 余额不足 / 支付网关超时 / 3D Secure 失败 | 明确失败原因 + 订单保留 PENDING + 可重试 |

```
GIVEN {起始状态}
WHEN  {触发异常的操作}
THEN  {系统如何响应}
AND   {数据未损坏}
AND   {用户有恢复路径}
```

**最少要求:** 每个用户旅程 ≥ 1 条异常路径。关键旅程（支付/数据修改/权限变更）≥ 3 条（覆盖校验失败 + 网络中断 + 业务异常）。

### 2.3 边界条件 (Boundary)

| 边界类型 | 测试场景 | 验证点 |
|---------|---------|--------|
| **数值边界** | 数量=0, 数量=MAX, 金额=0.01, 金额=MAX | 前端校验 + 后端校验一致 |
| **字符串边界** | 空字符串, 单字符, 最大长度, 超长 1 字符, emoji, 特殊字符 `'; DROP--` | 不崩溃 + 不注入 + 合理截断 |
| **列表边界** | 空列表, 1 条, 满页, 跨页, 10000+ 条 (虚拟滚动) | 空状态引导 + 分页正确 + 无性能退化 |
| **时间边界** | 过去时间、未来时间、时区边界 (UTC+14 / UTC-12) | 时区转换正确 + 不出现负时间 |
| **文件上传** | 0 字节, 1 字节, 最大允许, 超限 1 字节, 非允许类型 | 提示明确 + 不拖垮服务 |
| **并发边界** | 快速双击提交、同时开两个 Tab 操作 | 幂等 + 无重复数据 |

```
GIVEN {边界数据或状态}
WHEN  {触发操作}
THEN  {边界行为: 拒绝 OR 接受 OR 截断}
AND   {提示清晰}
```

**最少要求:** 每个涉及用户输入的旅程 ≥ 1 条边界用例。

### 2.4 状态转换 (State Transition)

基于 Section 7 的状态机设计，验证每个合法转换和非法转换。

```
GIVEN 当前状态: {STATE_A}
WHEN  触发事件: {EVENT}
THEN  目标状态: {STATE_B}
AND   副作用: {通知/审计日志/下游更新}
```

| 用例 ID | 当前状态 | 触发事件 | 目标状态 | 前置条件 | 副作用验证 | 是否合法 |
|---------|---------|---------|---------|---------|-----------|---------|
| E2E-STATE-001 | DRAFT | submit | IN_REVIEW | 必填字段完整 | 通知已发送 + 审计日志已写 | ✅ |
| E2E-STATE-002 | DRAFT | approve | — | — | 无 | ❌ (非法转换，应拒绝) |

**最少要求:** 每个状态机 ≥ 覆盖所有合法转换。每个状态 ≥ 覆盖 1 条非法转换尝试。

### 2.5 权限控制 (Authorization)

| 用例 ID | 角色 | 操作 | 预期结果 | UI 验证 |
|---------|------|------|---------|---------|
| E2E-AUTH-001 | admin | 删除任意资源 | 成功 | 删除按钮可见且可点击 |
| E2E-AUTH-002 | member | 删除他人资源 | 403 / 拒绝 | 删除按钮不可见或点击后提示无权限 |
| E2E-AUTH-003 | anonymous | 访问需登录页面 | 302 → /login | 页面不可见，自动跳转 |
| E2E-AUTH-004 | member | 访问自己的数据 | 成功 | 只看到自己的数据 |
| E2E-AUTH-005 | member | 通过直接 URL 访问他人数据 | 403 | 拒绝访问页 |

**最少要求:** 每个角色 ≥ 1 条权限边界用例。

---

## 3. 非功能测试场景 (Non-Functional)

非功能场景按 `business_domain` 选择性启用。`internal-tools` 可跳过大多数非功能场景。

### 3.1 性能 (Performance)

| 场景 | 指标 | 阈值 | 测量方式 |
|------|------|------|---------|
| **首次内容绘制 (FCP)** | 白屏时间 | < 1.5s | `performance.getEntriesByType('paint')` |
| **最大内容绘制 (LCP)** | 主要内容可见 | < 2.5s | `new PerformanceObserver(...)` |
| **累计布局偏移 (CLS)** | 视觉稳定性 | < 0.1 | LayoutShift 事件累计 |
| **首次输入延迟 (FID)** | 交互响应 | < 100ms | `performance.getEntriesByType('first-input')` |
| **TTIM (可交互时间)** | 页面可用 | < 3.5s | Lighthouse / Web Vitals |
| **API 响应时间** | 关键 API | P95 < 200ms | `page.waitForResponse()` 计时 |
| **大列表渲染** | 1000 行渲染 | < 1s | 虚拟滚动 benchmark |
| **内存泄漏** | 连续操作 100 次 | JS heap 增长 < 20% | `performance.memory` |

```
GIVEN {页面/功能}
WHEN  {加载 / 操作 / 持续使用}
THEN  {指标} < {阈值}
```

### 3.2 安全 (Security)

| 场景 | 测试方法 | 验证点 |
|------|---------|--------|
| **XSS 注入** | 在输入框填入 `<script>alert(1)</script>` | 不被执行，显示为纯文本 |
| **CSRF 防护** | 跨域 POST 不带 CSRF Token | 请求被拒绝 (403) |
| **敏感数据暴露** | 检查 HTML 源码 / localStorage / sessionStorage | 无 Token/密码/PII |
| **SQL 注入** | 输入 `' OR '1'='1` | 不改变查询语义，不返回非授权数据 |
| **点击劫持** | 检查 `X-Frame-Options` / CSP header | `X-Frame-Options: DENY` 或 `SAMEORIGIN` |
| **CORS 配置** | 非允许 Origin 的跨域请求 | 拒绝非白名单 Origin |
| **文件上传安全** | 上传 `.php`, `.exe`, `../../etc/passwd` | 拒绝 + 病毒扫描 |
| **速率限制** | 连续 100 次登录请求 | 触发 rate limit (429) |

**安全场景启用规则:**

| business_domain | 最少安全场景数 | 必测项 |
|-----------------|-------------|--------|
| `fintech` | ≥ 6 | XSS, CSRF, 注入, 敏感数据, 速率限制, 审计日志 |
| `ecommerce` | ≥ 4 | XSS, CSRF, 敏感数据, 支付安全 |
| `general` | ≥ 2 | XSS, CSRF |
| `internal-tools` | 可选 | — |

### 3.3 可用性与无障碍 (Usability & Accessibility)

| 场景 | 测试方法 | 标准 |
|------|---------|------|
| **键盘导航** | Tab / Shift+Tab / Enter / Escape 遍历全流程 | 所有可交互元素可聚焦 + 焦点顺序合理 + 无键盘陷阱 |
| **屏幕阅读器** | 检查 ARIA label / role / alt text | 关键交互有语义化标签 |
| **颜色对比度** | 检查文字/背景对比度 | WCAG AA: ≥ 4.5:1 (正文), ≥ 3:1 (大文本) |
| **焦点指示器** | Tab 遍历检查焦点样式 | 当前焦点元素有可见轮廓 |
| **错误提示关联** | 表单校验失败后检查 | 错误信息通过 `aria-describedby` 关联到输入框 |
| **跳过导航** | 检查 skip-link | 页面有 "跳到主要内容" 链接 |
| **缩放支持** | 200% 缩放 | 内容不溢出、不重叠、不截断 |
| **减少动画** | `prefers-reduced-motion: reduce` | 动画禁用或大幅降速 |

### 3.4 可靠性 (Reliability)

| 场景 | 模拟方式 | 验证点 |
|------|---------|--------|
| **API 超时** | `page.route()` 延迟 10s+ | 超时提示 + 重试按钮 |
| **API 返回 5xx** | `page.route()` 返回 503 | 降级 UI + 不影响其他功能 |
| **WebSocket 断开** | 断网 / 关闭 WS 连接 | 自动重连 + 重连期间数据排队 |
| **第三方脚本失败** | Block 第三方 CDN | 核心功能不受影响 |
| **localStorage 满** | 填充 localStorage 到 QuotaExceededError | 优雅降级，不 crash |
| **Service Worker 更新** | 部署新版本 SW | 提示用户刷新 + 不丢数据 |
| **后退/前进导航** | `page.goBack()` / `page.goForward()` | 表单状态保留 / 页面不崩溃 |
| **浏览器刷新** | F5 / Ctrl+R | 未提交数据警告 / 已提交数据不重复 |

### 3.5 国际化 (i18n / Localization)

按 `communication_language` 配置决定是否启用。单语言项目可标注 N/A 跳过。

| 场景 | 测试方法 | 验证点 |
|------|---------|--------|
| **文本翻译** | 切换语言 → 检查所有静态文本 | 无 fallback key 裸露 (如 `user.greeting`) |
| **日期格式** | 切换 locale → 检查日期显示 | `zh-CN: 2026/05/02` vs `en-US: 05/02/2026` |
| **数字/货币** | 切换 locale → 检查金额显示 | `zh-CN: ¥1,234.56` vs `en-US: $1,234.56` |
| **RTL 布局** | 切换阿拉伯语/希伯来语 | 布局镜像 + 图标方向正确 |
| **时区** | 切换浏览器时区 | 时间显示为用户时区 + 排序不受影响 |
| **内容长度** | 德语/俄语 (通常比中文长 30-50%) | UI 不截断、不溢出 |

---

## 4. 兼容性测试场景 (Compatibility)

### 4.1 浏览器兼容

| 浏览器 | 版本 | 最少覆盖 |
|--------|------|---------|
| Chrome | Latest, Latest-1 | P0 用例全量 |
| Firefox | Latest | P0 用例全量 |
| Safari | Latest (macOS/iOS) | P0 用例全量 + apple pay 等平台特性 |
| Edge | Latest | P0 用例抽样 (基于 Chromium，与 Chrome 高度一致) |

```
GIVEN 浏览器: {Chrome 130 / Firefox 128 / Safari 18}
WHEN  执行: {P0 用例集}
THEN  全部 PASS
```

**启用规则:** `business_domain: fintech/ecommerce` → 必测 Chrome + Firefox + Safari。`internal-tools` → 仅测团队默认浏览器。

### 4.2 设备与操作系统

| 设备类型 | 操作系统 | 屏幕 | 最少覆盖 |
|---------|---------|------|---------|
| Desktop | Windows 11 | 1920×1080 | P0 全量 |
| Desktop | macOS 15 | 2560×1440 (Retina) | P0 全量 |
| Desktop | Linux (Ubuntu 24.04) | 1920×1080 | P0 抽样 |
| Tablet | iPadOS 18 | 1024×1366 | P0 全量 + 关键旅程 |
| Tablet | Android 14 | 800×1280 | P0 抽样 |
| Mobile | iOS 18 (Safari) | 390×844 (iPhone 15) | P0 全量 + 关键旅程 |
| Mobile | Android 14 (Chrome) | 360×800 | P0 全量 + 关键旅程 |

### 4.3 屏幕尺寸与响应式

| 断点 | 宽度 | 验证点 |
|------|------|--------|
| **Desktop** | 1920px, 1366px, 1024px | 侧边栏可见 + 多列布局 + hover 交互可用 |
| **Tablet** | 768px | 侧边栏折叠 + 触摸目标 ≥ 44×44px |
| **Mobile** | 375px, 320px | 单列布局 + 汉堡菜单 + 底部固定操作栏 |
| **横屏** | 812px (iPhone 横屏) | 布局不崩溃 + 关键操作不隐藏 |

### 4.4 网络条件

| 网络 | 延迟 | 带宽 | 验证点 |
|------|------|------|--------|
| **WiFi / 4G** | 50ms | 10 Mbps | 正常体验 |
| **4G Slow** | 150ms | 1.6 Mbps | 加载指示器可见，不白屏 |
| **3G** | 300ms | 400 Kbps | 关键内容优先加载 + skeleton |
| **2G/Edge** | 800ms | 100 Kbps | 至少文字内容可读 + "网络较慢" 提示 |
| **Offline** | — | 0 | 离线页面 + 缓存内容可用 + 操作排队 |

---

## 5. 用户自定义扩展 (User-Defined Extensions)

### 5.1 扩展方式概览

E2E 模板支持三种扩展方式，互不冲突：

| 扩展方式 | 复杂度 | 适用场景 |
|---------|--------|---------|
| **A. 场景扩类** | 低 | 在现有类别下新增场景子类型 |
| **B. 自定义类别** | 中 | 新增独立的测试类别（如 GDPR 合规、行业特定检查） |
| **C. 脚本钩子** | 高 | 注入自定义验证脚本、自定义数据工厂 |

### 5.2 A. 场景扩类 (Scenario Extension)

在任意现有类别下追加场景子类型。在 `_context/config.yaml` 中声明：

```yaml
sw:
  e2e_extensions:
    scenarios:
      functional:
        boundary:
          - name: "会计精度"
            description: "验证金额计算不丢失精度"
            template: |
              GIVEN {金融交易数据}
              WHEN  {执行 N 次累加/扣减}
              THEN  {余额 = 初始值 ± N × 步长}  -- 不允许浮点误差
      non_functional:
        - name: "compliance:gdpr"
          description: "GDPR 合规检查"
          template: |
            GIVEN 用户数据包含 PII
            WHEN  用户请求数据删除
            THEN  30 天内所有副本清除
            AND   审计日志保留"删除记录"而非数据本身
      compatibility:
        - name: "print"
          description: "打印样式验证"
          template: |
            GIVEN 页面包含 {表格/图表}
            WHEN  触发 `window.print()`
            THEN  @media print 样式生效 + 导航/按钮隐藏 + 内容完整
```

### 5.3 B. 自定义类别 (Custom Category)

当业务领域需要标准模板未覆盖的独立测试维度时，创建自定义类别：

```yaml
sw:
  e2e_extensions:
    custom_categories:
      - name: "regulatory:sox"
        display: "SOX 合规 (萨班斯法案)"
        applies_to: ["fintech"]
        priority: P0
        scenarios:
          - id: "SOX-001"
            description: "财务数据修改必须有审计追踪"
            given: "具有修改财务数据权限的用户"
            when: "修改任意财务字段"
            then: "audit_log 表新增记录"
            verify: "记录包含: who/when/what/old_value/new_value"
          - id: "SOX-002"
            description: "职责分离 — 录入与审批不能是同一人"
            given: "用户 A 录入了一笔交易"
            when: "用户 A 尝试审批同一笔交易"
            then: "审批被拒绝"
            verify: "错误提示: '您不能审批自己创建的交易'"

      - name: "domain:healthcare"
        display: "医疗合规 (HIPAA)"
        applies_to: ["general"]  # 按需启用
        scenarios:
          - id: "HIPAA-001"
            description: "PHI 数据脱敏显示"
            given: "医生查看患者列表"
            when: "列表渲染完成"
            then: "SSN 显示为 ***-**-{last4}，完整数据仅在详情页可见"
```

### 5.4 C. 脚本钩子 (Script Hooks)

注入自定义验证逻辑到 E2E 执行流程。在 `_context/memory/sw-shared/e2e-hooks/` 下放置钩子脚本：

```
_context/memory/sw-shared/e2e-hooks/
├── before-all.js       # 所有用例执行前: 环境准备、全局 mock
├── after-all.js        # 所有用例执行后: 全局清理、报告聚合
├── before-each.js      # 每个用例前: 登录、重置状态
├── after-each.js       # 每个用例后: 截图、日志收集
├── custom-asserts.js   # 自定义断言: expect().toBeAccessible()
└── data-factories/     # 自定义数据工厂
    ├── user-factory.js
    └── order-factory.js
```

**钩子规范:**

```javascript
// custom-asserts.js — 自定义断言注册
// 框架无关声明，执行时由具体框架适配

// @e2e-hook: assert
// @name: toBeAccessible
// @description: 验证元素满足 WCAG AA 无障碍标准
async function toBeAccessible(locator) {
    const element = await locator.elementHandle();
    // 检查 role
    const role = await element.getAttribute('role');
    if (!role) {
        throw new Error(`元素缺少 role 属性: ${await locator.textContent()}`);
    }
    // 检查 aria-label 或 innerText
    const label = await element.getAttribute('aria-label') || await locator.textContent();
    if (!label || label.trim() === '') {
        throw new Error(`可交互元素缺少可访问名称`);
    }
    // 检查 contrast (调用浏览器 CDP)
    // ...
}

// @e2e-hook: fixture
// @name: createTestUser
// @description: 创建 E2E 测试用户并返回凭证
async function createTestUser(role = 'member') {
    const ts = Date.now();
    const user = {
        username: `e2e-${role}-${ts}`,
        email: `e2e-${role}-${ts}@example.com`,
        password: 'E2eTest@123',
        role: role
    };
    await db.insert('users', user);
    return { ...user, id: user.id };
}
```

### 5.5 扩展优先级覆盖

自定义扩展可以覆盖模板的默认优先级：

```yaml
sw:
  e2e_extensions:
    priority_overrides:
      # 将支付相关的所有用例提升到 P0
      - pattern: "E2E-PAY-*"
        set_priority: P0
      # 非功能中的性能场景降级 (内部工具)
      - pattern: "E2E-*-perf-*"
        set_priority: P3
        when: "business_domain == 'internal-tools'"
```

---

## 6. 场景启用矩阵

不同 `business_domain` 自动启用不同的场景组合：

| 场景类别 | `fintech` | `ecommerce` | `general` | `internal-tools` |
|---------|-----------|-------------|-----------|-----------------|
| **功能-正常** | ✅ P0 | ✅ P0 | ✅ P0 | ✅ P0 |
| **功能-异常** | ✅ P0 | ✅ P0 | ✅ P1 | ✅ P1 |
| **功能-边界** | ✅ P0 | ✅ P1 | ✅ P2 | ✅ P2 |
| **功能-状态转换** | ✅ P0 | ✅ P1 | ✅ P2 | ❌ 可选 |
| **功能-权限** | ✅ P0 | ✅ P0 | ✅ P1 | ❌ 可选 |
| **非功能-性能** | ✅ P1 (必测) | ✅ P1 (必测) | ✅ P2 | ❌ |
| **非功能-安全** | ✅ P0 (≥6 场景) | ✅ P1 (≥4) | ✅ P2 (≥2) | ❌ |
| **非功能-无障碍** | ✅ P1 (≥4) | ✅ P2 (≥2) | ❌ 可选 | ❌ |
| **非功能-可靠性** | ✅ P0 (≥5) | ✅ P1 (≥3) | ❌ 可选 | ❌ |
| **非功能-国际化** | 按 `communication_language` 决定 | 同左 | 同左 | ❌ |
| **兼容性-浏览器** | Chrome+FF+Safari | Chrome+FF+Safari | Chrome+FF | Chrome |
| **兼容性-设备** | Desktop+Tablet+Mobile | Desktop+Tablet+Mobile | Desktop+Mobile | Desktop |
| **兼容性-屏幕** | 全断点 | 全断点 | Desktop+Mobile | Desktop |
| **兼容性-网络** | 4G+3G+Offline | 4G+3G+Offline | 4G | 4G |
| **自定义扩展** | 按配置 | 按配置 | 按配置 | 按配置 |

可通过 `_context/config.yaml` 覆盖任意默认值：

```yaml
sw:
  e2e:
    scenario_overrides:
      non_functional.performance: "P0"   # 对非金融项目也强制开启性能测试
      compatibility.device: "skip"       # 纯后端项目跳过设备兼容
```

---

## 7. E2E 用例结构模板

所有类别和子类别的用例统一使用此结构：

```
GIVEN {起始状态 — 具体的 DB 行/API 响应/配置/Browser Context}
  AND {附加前置条件}
WHEN  {操作序列 — 每步含路由+元素+操作+等待}
  AND {并发的操作 / 网络条件 / 设备特征}
THEN  {UI 断言 — 可见性/文本/样式/状态}
  AND {API 断言 — 状态码/响应体/副作用}
  AND {DB 断言 — 行数/字段值/审计日志}
  AND {非功能断言 — 性能指标/安全 header/无障碍属性}
CLEANUP {具体的回滚 SQL/API 调用 — 恢复到测试前状态}
```

### 完整示例: 功能-异常 → 支付失败恢复

```
E2E-PAY-002: 支付时网络中断后恢复支付

GIVEN DB: users 表有用户 id='e2e-u-pay-002', balance=1000.00
  AND DB: products 表有商品 id='e2e-p-001', price=299.00, stock=50
  AND 用户已登录，购物车有 1 件商品 id='e2e-p-001'
WHEN  1. 打开 /checkout → 等待 #checkout-form 可见
      2. 点击 [data-testid="confirm-pay-btn"]
      3. 在 POST /api/v1/payments 返回前中断网络
         → page.route('**/api/v1/payments', route => route.abort('internetdisconnected'))
      4. 等待 .network-error-toast 可见（内容: "网络连接失败，请检查网络后重试"）
      5. page.route('**/api/v1/payments').unroute() — 恢复网络
      6. 点击 .network-error-toast 中的 [data-testid="retry-btn"]
THEN  UI: .success-page 可见，显示 "支付成功"
  AND UI: 订单号可见 (格式: ORD-{timestamp}-{random})
  AND API: GET /api/v1/orders?userId=e2e-u-pay-002
           → status=PAID, amount=299.00, items[0].product_id='e2e-p-001'
  AND DB:  orders 表 row_count 增加 1, status='PAID'
  AND DB:  users 表 e2e-u-pay-002 的 balance = 701.00 (1000 - 299)
  AND DB:  products 表 e2e-p-001 的 stock = 49
  AND DB:  audit_log 表有新记录: action='payment_completed', user_id='e2e-u-pay-002'
CLEANUP:
  DELETE FROM orders WHERE user_id='e2e-u-pay-002';
  UPDATE users SET balance=1000.00 WHERE id='e2e-u-pay-002';
  UPDATE products SET stock=50 WHERE id='e2e-p-001';
  DELETE FROM audit_log WHERE user_id='e2e-u-pay-002';
```

---

## 8. 与三层体系的集成

```
L1 UT (test-case-template.md)
  └─ 函数/方法 → 秒级反馈 → sw-tdd-agent 执行
L2 API (api-test-case-template.json)
  └─ 端点/契约 → 秒~分钟级 → Newman + sw-tdd-agent (GATE 1B), sw-integration-tester (GATE 3)
L3 E2E (e2e-test-case-template.md) ← 本模板
  └─ 用户旅程 → 分钟级 → Playwright + sw-browser-tester 执行 (GATE 3)
      ├─ 功能 (happy/error/boundary/state/auth)
      ├─ 非功能 (perf/security/a11y/reliability/i18n)
      ├─ 兼容性 (browser/device/screen/network)
      └─ 自定义 (custom_categories/script_hooks)
```

**E2E 执行时机:** L1 UT 100% PASS → L2 API 100% PASS → L3 E2E 执行。E2E 不在 TDD Agent 的两层循环内。

---

## 9. 输出产物

| 产物 | 路径 | 何时生成 |
|------|------|---------|
| E2E 用例设计 | `designs/{id}-design.md` Section 10.5 | 设计阶段 (sw-controller 加载本模板填充) |
| E2E 测试脚本 | `tests/e2e/{requirement_id}/` | 执行阶段 (由 Worktree Controller 协调生成) |
| 扩展配置 | `_context/config.yaml` (sw.e2e_extensions) | 项目初始化或按需追加 |
| 钩子脚本 | `_context/memory/sw-shared/e2e-hooks/` | 按需创建 |
