# Browser E2E Results Template

## What This Is

Structured output format for browser E2E test results. Written to `_context/memory/sw-shared/browser-e2e-results.yaml` after test execution completes.

## Results YAML Schema

```yaml
# _context/memory/sw-shared/browser-e2e-results.yaml

requirement_id: "REQ-YYYYMMDD-NNN"
requirement_title: "{title}"
executed_at: "YYYY-MM-DDTHH:MM:SSZ"
execution_duration_seconds: {n}
browser: "chromium"

environment:
  playwright_version: "1.x.y"
  os: "{linux|darwin|win32}"
  viewport: "1920x1080"

# ─── Execution Summary ───────────────────────────

summary:
  total_tests: {n}
  passed: {n}
  failed: {n}
  skipped: {n}
  pass_rate_pct: {n}

# ─── Per-Category Breakdown ──────────────────────

categories:
  functional:
    total: {n}
    passed: {n}
    failed: {n}
    subcategories:
      happy: { total: {n}, passed: {n}, failed: {n} }
      error: { total: {n}, passed: {n}, failed: {n} }
      boundary: { total: {n}, passed: {n}, failed: {n} }
      state_transition: { total: {n}, passed: {n}, failed: {n} }
      authorization: { total: {n}, passed: {n}, failed: {n} }
  non_functional:
    total: {n}
    passed: {n}
    failed: {n}
    subcategories:
      performance: { total: {n}, passed: {n}, failed: {n} }
      security: { total: {n}, passed: {n}, failed: {n} }
      accessibility: { total: {n}, passed: {n}, failed: {n} }
      reliability: { total: {n}, passed: {n}, failed: {n} }
      i18n: { total: {n}, passed: {n}, failed: {n} }
  compatibility:
    total: {n}
    passed: {n}
    failed: {n}

# ─── Per-Test Details ────────────────────────────

tests:
  - id: "E2E-CART-001"
    title: "完整购物流程"
    category: "functional"
    subcategory: "happy"
    priority: "P0"
    status: "passed"
    duration_ms: 3420
    retries: 0

  - id: "E2E-PAY-002"
    title: "支付时网络中断后恢复支付"
    category: "functional"
    subcategory: "error"
    priority: "P0"
    status: "failed"
    duration_ms: 2150
    retries: 1
    error:
      message: "Expected '.success-toast' to be visible"
      step: "THEN: UI assertion"
    artifacts:
      screenshot: "_context-output/test-artifacts/e2e/{req_id}/output/E2E-PAY-002-FAILURE.png"
      trace: "_context-output/test-artifacts/e2e/{req_id}/traces/E2E-PAY-002-trace.zip"

  - id: "E2E-PERF-001"
    title: "首页 LCP 性能验证"
    category: "non_functional"
    subcategory: "performance"
    priority: "P1"
    status: "passed"
    duration_ms: 4500
    metrics:
      lcp_ms: 1850
      fcp_ms: 800
      cls: 0.05

# ─── Visual Regression Results ───────────────────

visual_regression:
  enabled: true
  total_snapshots: 8
  passed: 7
  failed: 1
  baselines_updated: false
  snapshots:
    - name: "checkout-success-page"
      test_id: "E2E-CART-001"
      status: "passed"
      diff_pixels: 0
    - name: "payment-confirmation"
      test_id: "E2E-CART-003"
      status: "failed"
      diff_pixels: 342
      threshold: 100
      diff_image: "output/E2E-CART-003-diff.png"
      diagnosis: "'.order-total' shifted 12px right — likely CSS change"

# ─── Diagnostics ──────────────────────────────────

diagnostics:
  console_errors:
    total: 2
    by_test:
      - test_id: "E2E-PAY-002"
        errors:
          - text: "Uncaught TypeError: Cannot read property 'id' of undefined"
            assessment: "Application error — related to test failure"
  network_failures:
    total: 3
    by_test:
      - test_id: "E2E-NET-001"
        failures:
          - url: "/api/v1/payments"
            status: 503
            assessment: "Expected — test simulates 503"

# ─── Artifacts Index ──────────────────────────────

artifacts:
  test_script: "_context-output/test-artifacts/e2e/{req_id}/browser-e2e.spec.ts"
  playwright_config: "_context-output/test-artifacts/e2e/{req_id}/playwright.config.ts"
  screenshots_dir: "_context-output/test-artifacts/e2e/{req_id}/output/"
  traces_dir: "_context-output/test-artifacts/e2e/{req_id}/traces/"
  json_report: "_context-output/test-artifacts/e2e/{req_id}/results.json"

# ─── Gate Status ──────────────────────────────────

gates:
  all_functional_pass: true
  all_p0_pass: false
  no_console_errors: true
  visual_regression_ok: false

# ─── Overall Result ───────────────────────────────

overall: "FAIL"
blocking_issues:
  - test_id: "E2E-PAY-002"
    severity: "P0"
    description: "Payment recovery test failed"
    recommended_action: "Route to responsible worktree for fix"
```

## Tracker Update

After writing results, update `requirements-tracker.yaml`:

```yaml
phases:
  test:
    status: "done"               # or "failed"
    browser_e2e_status: "pass"   # pass | fail | partial
    browser_e2e_pass_rate: 87.5
    browser_e2e_results: "_context/memory/sw-shared/browser-e2e-results.yaml"
    completed_at: "YYYY-MM-DDTHH:MM:SSZ"
```

## Downstream Consumers

- **sw-controller**: reads `summary.pass_rate_pct` and `gates.*` to determine phase advancement
- **sw-delivery-manager**: reads `blocking_issues` (P0 failures) for delivery checklist
- **Human reviewer**: reads `visual_regression.snapshots` to approve/reject baseline updates
