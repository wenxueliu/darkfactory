# Kimi WebBridge 浏览器 E2E 执行计划

## What This Is

本计划定义 L3 浏览器 E2E 的真实浏览器会话、目标环境、设备/视口覆盖、
认证、测试数据和证据策略。执行工具是 `kimi-webbridge`，它操作用户当前
浏览器及其登录态，不安装独立浏览器或本地自动化运行时。

## Environment Verification

执行任何用例前：

1. 确认 Kimi WebBridge daemon 和浏览器 extension 可用；工具调用失败时按
   `kimi-webbridge` Skill 的指引启动 daemon：

   ```bash
   ~/.kimi-webbridge/bin/kimi-webbridge start
   ```

2. 创建本任务唯一的 session，并在首次 `navigate` 时设置中文
   `group_title`。一个任务全程复用同一个 session。
3. 使用 `navigate` 或用户明确授权的 `find_tab(active:true)` 打开目标页。
4. 使用 `snapshot` 验证页面标题、关键文本和交互元素。
5. 用独立健康检查确认后端和测试数据端点可用；不得把健康检查结果当作
   浏览器用例通过。
6. 检查目标 URL、认证状态和测试数据。不得把密码、cookie 或 token 写入
   会话日志。

## Browser Session Selection

Kimi WebBridge 使用真实浏览器 tab，而不是固定的浏览器二进制。兼容性覆
盖通过配置不同的浏览器/设备 session 完成；当前 session 的实际 browser、
viewport 和 OS 必须写入报告。

```yaml
sw:
  browser_e2e:
    browser_session: "requirement-e2e"
    group_title: "需求浏览器 E2E"
    reuse_active_tab: false
    capture_network: true
    visual_review: "required"
    sessions:
      - name: "desktop-primary"
        browser: "user-default"
        viewport: "1920x1080"
      - name: "mobile-review"
        browser: "user-mobile-profile"
        viewport: "375x812"
```

如果需要另一个浏览器或设备，创建新的明确 session，不能在同一个 session
中假装完成未执行的兼容性覆盖。

## Viewport and Device Evidence

用例设计可以声明目标视口和设备：

| Name | Width | Height | Use Case |
|---|---:|---:|---|
| Desktop HD | 1920 | 1080 | 默认桌面流程 |
| Desktop | 1366 | 768 | 常见笔记本 |
| Tablet | 768 | 1024 | 平板竖屏 |
| Mobile | 375 | 812 | 移动端 |
| Mobile Small | 320 | 568 | 小屏兼容性 |

实际执行时记录浏览器当前视口。若通过 `cdp` 调整了设备指标，记录调用
参数和调整结果；无法调整时返回 `NEEDS_USER_INPUT` 或明确标记该覆盖未执行。

## WebBridge Interaction Protocol

每个用例遵循以下顺序：

```text
navigate/find_tab → snapshot → screenshot(before)
→ click/fill/evaluate/cdp → snapshot
→ screenshot(after) → network list/detail → CLEANUP
```

规则：

- 优先使用 `snapshot` 返回的 `@e` 引用；引用过期时重新 snapshot，不复用
  旧引用。
- 常规输入使用 `fill`，提交使用 `click`；没有独立 Enter 工具时使用
  `evaluate` 派发键盘事件或直接点击提交按钮。
- 只有在页面没有可用 `@e` 引用、需要读取属性或需要复杂事件时使用
  `evaluate`/`cdp`。
- 关键流程前后使用 `screenshot`；关键 API 交互使用
  `network start/list/detail/stop`。
- `snapshot`、截图和网络记录均写入会话日志索引。

## Network and Failure Conditions

WebBridge 可以观察网络请求，但不等价于网络故障注入器。网络中断、超时、
服务降级等场景应通过项目已有的测试环境开关、故障注入接口或部署配置准
备；若环境不支持，记录为未执行，不伪造浏览器网络故障。

| Network Case | Preparation | Evidence |
|---|---|---|
| 正常网络 | 目标环境健康 | request/response detail |
| API 5xx | 测试环境故障注入或 stub 开关 | network detail + UI snapshot |
| 超时 | 测试环境 timeout profile | duration + UI recovery |
| 断网 | 用户浏览器/环境级网络开关 | action record + recovery screenshot |

## Authentication State

优先使用用户已登录的浏览器 session：

1. 用户明确允许时，用 `find_tab(active:true)` 接管当前页面；
2. 否则用本任务的 `navigate` 新开 tab，通过已有浏览器 profile 的登录态访问；
3. 如果需要登录，停在登录步骤并请求用户完成可信交互；不要在命令、日志或
   产物中收集密码、验证码、cookie 或 token；
4. 报告只记录 `auth: PASS|FAIL|NEEDS_USER_INPUT`。

## Test Data Strategy

- **Seeding:** 优先使用 API、测试夹具或项目既有 seed 命令，不直接改生产数据库。
- **Isolation:** 每个用例使用唯一数据标识，不依赖其他用例留下的数据。
- **Cleanup:** CLEANUP 必须在成功和失败后都尝试，结果写入会话日志。
- **Repeatability:** 用例的 GIVEN、操作、THEN 和 CLEANUP 均必须可复现；无法
  复现的前置条件需要记录为 blocker。

## Configurable Execution Policy

```yaml
sw:
  browser_e2e:
    action_timeout_ms: 30000
    settle_delay_ms: 500
    capture_network: true
    capture_before_after_screenshots: true
    visual_review: "required"
    active_tab_policy: "ask"
```

- `active_tab_policy: ask`：没有用户明确授权时不得借用当前 tab。
- `capture_network: true`：关键流程必须有网络证据；无法捕获时记录原因。
- `visual_review: required`：基线和当前截图缺少审查结论时不能返回全量 `PASS`。

## Session Lifecycle

- 一个需求的一次执行使用一个固定 session 名称和一个 tab group。
- 同一 session 可按兼容性矩阵打开多个明确 tabs，但每个 tab 的 URL、浏览器、
  视口和用例 ID 必须记录。
- 执行结束后不要自动调用 `close_session`；仅在用户明确要求关闭时执行。
