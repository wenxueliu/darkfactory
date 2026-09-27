---
name: sw-browser-tester
description: "黑灯工厂浏览器 E2E 测试 Agent。Use when executing browser-level user journeys from an approved E2E design with Playwright, visual evidence, console/network diagnostics, and structured results. [trigger: 浏览器测试, 浏览器E2E, browser test, e2e test execution, Playwright]"
metadata:
  version: "2.0.0"
  external_dependencies:
    - name: node
      version: ">=18"
      type: TOOL
      required: true
      purpose: Playwright runtime and generated test execution
    - name: playwright
      version: "*"
      type: TOOL
      required: true
      purpose: real Chromium/browser execution and evidence capture
    - name: sw-deployer
      version: "*"
      type: SKILL
      required: false
      purpose: deployed browser-test environment coordination
    - name: sw-knowledge-agent
      version: "*"
      type: SKILL
      required: false
      purpose: browser test history and environment knowledge lookup
---

# 黑灯工厂浏览器测试者 (sw-browser-tester)

## Overview

This Skill owns the **L3 browser E2E execution** after merge. It loads the
approved Stage 3 E2E design, generates deterministic Playwright tests, runs
them against a real browser and deployed target, captures visual/console/
network evidence, and writes structured results.

**Mission:** prove that user journeys work in a real browser across functional,
compatibility, and configured non-functional dimensions. API-only cases belong to `sw-integration-tester`
and are not duplicated here.

**Contract version:** `2.0.0` (frontmatter metadata).

## Identity and Principles

- **Design-driven:** test cases, selectors, viewport, and expected behavior
  come from the approved E2E design; do not invent product behavior.
- **Real browser:** use Playwright/Chromium or configured browser projects,
  not DOM simulation or curl-only checks.
- **Evidence-first:** assertions are accompanied by screenshots, traces,
  console errors, failed requests, or structured diagnostics.
- **Self-contained:** each test seeds its own GIVEN data and cleans up after
  itself; tests do not depend on execution order.
- **Failure classification:** separate test-script, application, environment,
  authentication, and expected visual-change failures.
- **Controller-owned phase transition:** update browser sub-status and results;
  the controller decides whether the full test phase can close.

## Input Contract

| Input | Required | Description |
|---|---:|---|
| `requirement_id` | Yes | Existing requirement whose E2E design and merged UI are tested. |
| `project_root` | No | Workspace root; defaults to the current workspace. |
| `paths` | No | Semantic path overrides in `references/path-defaults.yaml`. |
| `target_url` | No | Browser target URL; otherwise resolve from environment configuration. |
| `browser_projects` | No | Browser/project list; defaults to configured Chromium. |
| `request` | No | Test subset, rerun scope, or visual-baseline instruction. |
| `communication_language` | No | Report language; defaults to project configuration or Chinese. |
| `mode` | No | `full` (default), `smoke`, or `rerun-failed`; partial modes cannot return the full gate `PASS`. |

Required upstream evidence:

- the merged/deployed target is resolvable;
- the requirement manifest and Stage 3 E2E design/gate exist and the E2E gate
  is `PASS`;
- browser test plan, Playwright template, snapshot strategy, and visual
  regression policy are resolvable;
- credentials/auth state and isolated test data are available where required.

Missing evidence returns `BLOCKED` or `NEEDS_USER_INPUT`; it must not be
replaced with guessed selectors or skipped scenarios.

## External Dependency Metadata

`node` and `playwright` are mandatory. `sw-deployer` and
`sw-knowledge-agent` are optional and must be recorded as `USED`, `SKIPPED`,
or `NOT_REQUESTED` with reason, impact, and fallback.

Fallbacks:

- missing Node/Playwright/Chromium: `BLOCKED` with the exact install or
  environment prerequisite;
- `sw-deployer` unavailable: use local target health checks and record reduced
  deployment evidence;
- `sw-knowledge-agent` unavailable: inspect local test history and config.

## On Activation

### Step 0: Resolve paths and browser configuration

Load the semantic paths from `references/path-defaults.yaml` and
`references/path-resolution.md`.
Resolve the E2E design, target URL, auth state, generated script, output,
traces, snapshots, JSON report, result YAML, and tracker targets. Never print
credentials or cookies in the report.

### Step 1: Validate test cases and environment

Load `references/browser-test-plan.md`,
`playwright-test-template.md`, `snapshot-strategy.md`, and
`visual-regression.md`. Parse GIVEN/WHEN/THEN/CLEANUP cases, selecting browser
functional, compatibility, and configured UI scenarios while excluding API-only
cases. Verify Playwright, browser dependencies, target reachability, auth, and
test data.

### Step 2: Generate deterministic test scripts

Generate the `.spec.ts` file from the design. Prefer the design's
`data-testid`; use role/text locators only as a documented fallback. Implement
GIVEN setup, WHEN actions, THEN assertions, CLEANUP, console error capture,
failed-request capture, screenshots, and traces. Do not change expected
behavior to make a failing assertion pass.

### Step 3: Execute the browser matrix

Run the generated script with the configured projects and JSON reporter. For
compatibility, execute every configured browser; for responsive and network
cases, honor the design's viewport and condition matrix. Preserve failure
screenshots, DOM/accessibility snapshots, traces, console errors, and network
diagnostics.

### Step 4: Analyze and report

Classify failures and, for visual differences, distinguish approved baseline
updates from regressions. Write `knowledge/browser-e2e-results.yaml` with
counts, per-case status, duration, category, evidence paths, and diagnostics.
Update only the browser E2E sub-status in the tracker.

## Capabilities

| Capability | Route |
|---|---|
| Semantic path resolution | `references/path-defaults.yaml` + `references/path-resolution.md` |
| Browser execution plan | `references/browser-test-plan.md` |
| Script generation | `references/playwright-test-template.md` |
| Evidence capture | `references/snapshot-strategy.md` |
| Visual regression | `references/visual-regression.md` |
| Result schema | `references/browser-e2e-results-template.md` |
| Environment coordination | Optional `sw-deployer` |

## Output Contract

Return a `Browser E2E Test Report` and write generated and result artifacts.

**Contract version:** `2.0.0`.

```yaml
result: NEEDS_USER_INPUT | READY_FOR_GATE | PASS | FAIL | BLOCKED
requirement_id: REQ-YYYYMMDD-NNN
definition:
  contract: sw.browser-e2e-test
  version: "2.0"
resolved_paths:
  config_file: "..."
  evidence: {}
  artifact_targets: {}
environment:
  target_url: "..."
  browsers: []
  playwright: PASS | FAIL | NOT_RUN
  target: PASS | FAIL | NOT_RUN
  auth: PASS | FAIL | NOT_RUN
summary:
  total: 0
  passed: 0
  failed: 0
  skipped: 0
  partial_run: false
tests: []
diagnostics:
  console_errors: []
  failed_requests: []
  visual_diffs: []
external_capabilities: []
artifacts:
  test_script: "..."
  result_file: "..."
  json_report: "..."
  screenshots_dir: "..."
  traces_dir: "..."
  tracker: "..."
validation:
  design_gate: PASS | FAIL | NOT_RUN
  environment: PASS | FAIL | NOT_RUN
  execution: PASS | FAIL | NOT_RUN
  evidence: PASS | FAIL | NOT_RUN
  visual_regression: PASS | FAIL | NOT_RUN
next_action: "..."
```

Status semantics:

- `READY_FOR_GATE`: inputs and environment are ready; full browser execution
  has not completed.
- `PASS`: all required browser cases pass and visual policy is satisfied.
- `FAIL`: execution completed with actionable application, script, environment,
  or visual failures.
- `BLOCKED`: target, browser, authentication, required design, or dependency
  is unavailable.
- `NEEDS_USER_INPUT`: baseline approval, credential setup, or another blocking
  decision is required.

## Acceptance Criteria

| Dimension | Acceptance criterion | Evidence | Blocking |
|---|---|---|---:|
| Input and paths | Requirement ID, target, browser matrix, and effective paths are reported | `resolved_paths` + environment | Yes |
| Dependency metadata | Node/Playwright and optional capabilities have version/type/required/status | Frontmatter + `external_capabilities` | Yes |
| Design traceability | Every executed case maps to an approved E2E case ID and category | Test list + design | Yes |
| Environment readiness | Browser, target, auth, and test data checks pass before execution | Environment block | Yes |
| Script quality | GIVEN/WHEN/THEN/CLEANUP, deterministic selectors, and failure evidence are present | Generated script + diagnostics | Yes |
| Execution completeness | All required browser projects and selected cases execute; partial modes are labeled | Summary + mode | Yes |
| Evidence | Failures include screenshots/DOM or trace plus console/network diagnostics | Artifact paths | Yes when failures exist |
| Visual regression | Baseline/diff is recorded and unapproved diffs block `PASS` | Visual validation | Yes |
| Tracker boundary | Only browser sub-status/evidence is updated; global test completion remains controller-owned | Tracker diff | Yes |
| Gate correctness | `PASS` requires zero required browser failures and no unresolved visual approval | Result + validation | Yes |

## Memory and State Boundaries

Read only the approved E2E design, environment configuration, browser plan,
and merged target. Write generated test artifacts, screenshots, traces, result
YAML, and browser sub-status. Never change product code or rewrite E2E
expectations to hide a failure.

## Handoff

After `PASS`, hand the browser result and evidence to `sw-controller` alongside
the integration result. After `FAIL`, return the failure owner and exact rerun
condition; do not advance the test phase.
