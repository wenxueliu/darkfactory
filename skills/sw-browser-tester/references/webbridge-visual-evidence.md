# Kimi WebBridge 视觉证据策略

## What This Is

Kimi WebBridge 负责捕获真实浏览器截图；视觉回归由基线、当前截图、DOM/
accessibility snapshot 和结构化审查结论组成。WebBridge 本身不提供独立的
像素级测试 runner，因此不能把“截图已生成”直接判定为视觉通过。

## When Visual Review Is Required

| Scenario | Review | Rationale |
|---|---|---|
| Critical checkout/payment flow | Required P0 | 视觉变化可能影响交易完成 |
| Landing/marketing page | Required P0 | 首屏和转化路径敏感 |
| Dashboard/data visualization | Required P1 | 数据展示和布局必须稳定 |
| Internal tool | Optional P2 | 以功能正确性为主 |
| Loading/spinner | Not required | 状态具有时间不确定性 |
| Third-party embed | Not required | 内容不由本系统控制 |

## Baseline and Current Capture

首次执行或明确创建基线时：

1. 使用固定 browser session、URL、用户、数据和视口；
2. `snapshot` 记录页面结构；
3. `screenshot` 保存 baseline；
4. 在结果中标记 `baseline_created: true`，不能直接标记视觉 PASS。

后续执行：

1. 复现同一 GIVEN 状态；
2. 截取 current screenshot；
3. 对照 baseline、snapshot 和预期变化；
4. 写入 review 状态：`PASS`、`EXPECTED_CHANGE`、`REGRESSION` 或
   `NEEDS_HUMAN`。

## Dynamic Content

在截图前通过测试数据和环境配置固定日期、随机 ID、头像、广告、实时图表
等动态内容。无法稳定的区域应：

- 在设计中声明为动态区域并排除视觉结论；
- 通过 DOM/文本/网络断言验证其功能；
- 不使用模糊的“差不多相同”作为视觉验收。

## Review Record

```yaml
test_id: E2E-CART-001
baseline: visual/E2E-CART-001-baseline.png
current: visual/E2E-CART-001-current.png
snapshot: screenshots/E2E-CART-001-after.json
review: PASS | EXPECTED_CHANGE | REGRESSION | NEEDS_HUMAN | NOT_REQUIRED
reviewer: sw-media-interpreter | human | sw-browser-tester
observations:
  - "Order total remains aligned and success banner is visible"
blocking_issue: null
```

## Decision Rules

- `PASS`：基线和当前状态等价，或变化已被需求/设计明确允许。
- `EXPECTED_CHANGE`：变化是本次需求预期结果，并记录依据；需按项目策略
  更新基线。
- `REGRESSION`：变化违反设计或影响用户旅程，阻塞 E2E gate。
- `NEEDS_HUMAN`：证据不足、动态内容未固定或审查结果不确定，阻塞全量
  `PASS`。
- `NOT_REQUIRED`：场景在配置或设计中明确不需要视觉审查。

基线更新必须有明确授权，并保留旧基线路径和更新原因。
