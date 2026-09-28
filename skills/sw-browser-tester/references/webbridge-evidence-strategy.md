# Kimi WebBridge 浏览器证据策略

## Evidence Model

Kimi WebBridge 的证据来自真实浏览器会话：

| Evidence | WebBridge action | Purpose |
|---|---|---|
| Accessibility snapshot | `snapshot` | 页面结构、文本、角色和新鲜 `@e` refs |
| Before screenshot | `screenshot` | 关键操作前的视觉状态 |
| After screenshot | `screenshot` | 操作完成后的视觉状态 |
| Network capture | `network start/list/detail/stop` | 请求、响应、失败和耗时 |
| DOM/property evidence | `evaluate` | 仅补充 snapshot 不暴露的属性 |
| Browser protocol evidence | `cdp` | 视口/设备或特殊事件的明确操作 |
| URL/title | `navigate`/`snapshot` result | 页面身份和导航断言 |

所有证据写入 `{test_root}`，并在 session log 中按 `test_id`、`step`、时间和
URL 建立索引。

## Checkpoint Strategy

### Before action

在点击、删除、支付、提交或状态转换前：

1. `snapshot` 确认页面和目标 `@e` ref；
2. `screenshot` 保存 before 状态；
3. 关键流程调用 `network start`。

### After action

操作完成并重新 `snapshot` 后：

1. 记录可见文本、角色、URL、按钮状态和业务状态；
2. `screenshot` 保存 after 状态；
3. 调用 `network list/detail` 保存关键请求；
4. 停止网络采集并把日志路径写入 action record。

### On failure

失败时至少保留：

- 当前 URL 和页面标题；
- 最新 accessibility snapshot；
- 全页或关键区域 screenshot；
- 失败 action、目标 ref/CSS selector 和错误信息；
- 相关 network detail；
- CLEANUP 是否执行及结果。

## Console and Network Diagnostics

如果 WebBridge/浏览器提供 console 或 request failure 信息，写入
`diagnostics.console_errors` 和 `diagnostics.failed_requests`。不能获得某类
诊断时记录 `NOT_CAPTURED` 及原因，不得填充空的 `PASS`。

## Evidence Naming

```text
{test_root}/
├── browser-e2e-session.json
├── screenshots/
│   ├── E2E-CART-001-step-01-before.png
│   └── E2E-CART-001-step-04-after.png
├── network.json
└── visual/
    ├── E2E-CART-001-baseline.png
    ├── E2E-CART-001-current.png
    └── E2E-CART-001-review.md
```

文件名不得包含密码、token、cookie 或用户隐私数据。

## Session Rules

- 一个任务固定一个 session 名称；所有 `navigate`、`snapshot`、`click`、
  `fill`、`screenshot` 和 `network` 请求都带同一个 session。
- 首次导航设置用户语言的 `group_title`，并向用户说明页面属于该 tab group。
- 不要自动调用 `close_session`。用户明确要求清理时才关闭整个 session。
- 不要借用用户当前 tab，除非输入明确包含 `active_tab: true` 或等价授权。
