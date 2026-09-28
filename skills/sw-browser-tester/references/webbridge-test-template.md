# Kimi WebBridge E2E 用例执行记录模板

## 用途

本模板把 E2E 设计中的 GIVEN/WHEN/THEN/CLEANUP 转换为 Kimi WebBridge 的
真实浏览器操作和证据记录。它不是 TypeScript 测试脚本；执行结果写入
`browser-e2e-session.json`，并由 `browser-e2e-results.yaml` 汇总。

## Case Record

```yaml
test_id: "E2E-CART-001"
title: "完整购物流程"
category: functional
priority: P0
session_id: "requirement-e2e"
target_url: "https://test.example.com/products"
browser: "user-default"
viewport: "1920x1080"
related_requirement: "AC-1"
related_services: [catalog, order, payment]
status: pending | running | passed | failed | blocked | skipped
steps: []
cleanup:
  status: pending | passed | failed | not_run
  evidence: []
```

## Action Record

每一个交互步骤追加一条记录：

```yaml
- step: 1
  phase: GIVEN | WHEN | THEN | CLEANUP
  action: navigate | find_tab | snapshot | click | fill | evaluate | cdp | screenshot | network
  target: "@e12 or URL or semantic description"
  input: "不含秘密的输入摘要"
  expected: "可验证的预期"
  observed: "实际结果"
  status: pass | fail | skipped
  evidence:
    snapshot: "..."
    screenshot: "..."
    network: "..."
  error: null
```

## Standard Translation

| E2E 设计 | WebBridge 操作 |
|---|---|
| GIVEN 打开页面 | `navigate` 或用户授权的 `find_tab(active:true)`，随后 `snapshot` |
| GIVEN 设置视口 | 使用已配置 browser session；必要时通过 `cdp` 调整并记录结果 |
| WHEN 查找元素 | `snapshot`，从 accessibility tree 获取新鲜 `@e` ref |
| WHEN 点击 | `click` 使用当前 `@e` ref |
| WHEN 输入 | `fill` 使用当前 `@e` ref；不记录密码/令牌 |
| WHEN 复杂事件 | 仅在必要时使用 `evaluate` 或 `cdp` |
| THEN 页面状态 | `snapshot` + 可见文本/角色/状态检查 |
| THEN 网络结果 | `network list/detail` 或已声明 API 断言 |
| THEN 视觉结果 | `screenshot`，关联 baseline/current/review 状态 |
| CLEANUP | 浏览器动作或项目测试 API；记录成功/失败 |

## Fresh Reference Rule

`@e` ref 只对当前 snapshot 有效。页面导航、DOM 状态变化、提交表单或等待
异步结果后，必须重新调用 `snapshot`，不得继续使用旧 ref。若 snapshot
没有目标：

1. 检查页面是否加载完成和 URL 是否正确；
2. 用 CSS selector 作为有证据的 fallback；
3. 最后才用 `evaluate` 读取属性或派发复杂事件；
4. 仍找不到时记录 `failed`，不要修改预期或猜测选择器。

## Example Action Sequence

```text
1. navigate(target_url, newTab=true, group_title="需求浏览器 E2E")
2. snapshot → resolve search input @e7 and submit @e8
3. screenshot(before-search)
4. fill(@e7, "test-product")
5. click(@e8)
6. snapshot → verify result text and resolve buy button @e14
7. click(@e14)
8. network detail → verify order request status
9. screenshot(after-buy)
10. snapshot → verify order number
11. CLEANUP via approved test API, then record result
```

## Assertions

Each THEN assertion must state:

- expected visible text, role, URL, or state;
- expected network status/body fields where applicable;
- expected persistence/API state when the design requires it;
- evidence path proving the observation.

“页面看起来正常”不是可接受断言；必须转成 snapshot、screenshot、network
detail 或 API/data evidence。
