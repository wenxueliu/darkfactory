# Browser E2E Results Template — Kimi WebBridge

## What This Is

结构化输出格式，写入 `knowledge/requirements/{requirement_id}/browser-e2e-results.yaml`。结果描述一次
Kimi WebBridge 真实浏览器会话及其截图、snapshot、网络和视觉审查证据。

## Results YAML Schema

```yaml
requirement_id: "REQ-YYYYMMDD-NNN"
requirement_title: "{title}"
executed_at: "YYYY-MM-DDTHH:MM:SSZ"
execution_duration_seconds: 0

environment:
  webbridge_version: "1.11.3"
  session_id: "requirement-e2e"
  group_title: "需求浏览器 E2E"
  browser: "user-default"
  browser_version: "..."
  os: "..."
  viewport: "1920x1080"
  target_url: "https://test.example.com"
  auth_status: "pass | fail | needs_user_input"

summary:
  total_tests: 0
  passed: 0
  failed: 0
  skipped: 0
  blocked: 0
  pass_rate_pct: 0
  partial_run: false

categories:
  functional:
    total: 0
    passed: 0
    failed: 0
    subcategories: {}
  non_functional:
    total: 0
    passed: 0
    failed: 0
    subcategories: {}
  compatibility:
    total: 0
    passed: 0
    failed: 0
    subcategories: {}

tests:
  - id: "E2E-CART-001"
    title: "完整购物流程"
    category: "functional"
    subcategory: "happy"
    priority: "P0"
    status: "passed | failed | skipped | blocked"
    duration_ms: 0
    session_id: "requirement-e2e"
    steps: 0
    failed_step: null
    error:
      message: null
      action: null
      target: null
    artifacts:
      snapshots: []
      screenshots: []
      network: []
      visual_review: null
    cleanup:
      status: "passed | failed | not_run"
      evidence: []

visual_evidence:
  required: true
  baseline_created: false
  reviewed: false
  pass: 0
  expected_change: 0
  regression: 0
  needs_human: 0
  records: []

diagnostics:
  console_errors:
    total: 0
    by_test: []
  failed_requests:
    total: 0
    by_test: []
  webbridge_errors: []

artifacts:
  session_log: "knowledge/requirements/{req_id}/test-artifacts/e2e/browser-e2e-session.json"
  screenshots_dir: "knowledge/requirements/{req_id}/test-artifacts/e2e/output/"
  network_log: "knowledge/requirements/{req_id}/test-artifacts/e2e/network.json"
  visual_evidence_dir: "knowledge/requirements/{req_id}/test-artifacts/e2e/visual/"

gates:
  design_gate_pass: true
  webbridge_session_ready: true
  all_functional_pass: true
  all_p0_pass: true
  no_unclassified_failures: true
  visual_review_ok: true

overall: "PASS | FAIL | BLOCKED | NEEDS_USER_INPUT"
blocking_issues: []
next_action: "..."
```

## Tracker Update

After writing results, update only the browser sub-status:

```yaml
phases:
  test:
    browser_e2e_status: "pass | fail | partial | blocked"
    browser_e2e_pass_rate: 100.0
    browser_e2e_results: "knowledge/requirements/{req_id}/browser-e2e-results.yaml"
```

`sw-controller` owns the global `phases.test.status` transition.

## Downstream Consumers

- `sw-controller`: reads gate fields, pass rate, blocking issues, and artifact paths;
- `sw-delivery-manager`: reads P0 failures and visual review status;
- human or `sw-media-interpreter`: reviews baseline/current screenshots and
  `visual_evidence.records`.
