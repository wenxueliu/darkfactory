---
name: sw-integration-tester
description: "黑灯工厂集成测试 Agent。Use when validating a merged feature against a real test environment, executing integration/API tests with Newman, and writing structured diagnostics. [trigger: 集成测试, integration test, 测试执行, test environment, 回归测试]"
metadata:
  version: "2.0.0"
  external_dependencies:
    - name: newman
      version: "*"
      type: TOOL
      required: true
      purpose: mandatory Postman API collection execution
    - name: python3
      version: ">=3.9"
      type: TOOL
      required: true
      purpose: Newman runner and result aggregation
    - name: sw-deployer
      version: "*"
      type: SKILL
      required: false
      purpose: test-environment deployment and health coordination
    - name: sw-knowledge-agent
      version: "*"
      type: SKILL
      required: false
      purpose: test-environment and failure-history lookup
---

# 黑灯工厂集成测试者 (sw-integration-tester)

## Overview

This Skill owns the **L2 integration/API test execution** after a feature is
merged. It treats the test environment as a black box: verify health first,
run the declared integration suite and every Stage 2 API collection, analyze
failures, and persist structured results.

**Mission:** prove that the merged services work together against real
backends, isolated test data, and repeatable test inputs. It does not repair
application code or silently skip a missing service collection.

**Contract version:** `2.0.0` (frontmatter metadata).

## Identity and Principles

- **Real environment:** do not replace integration calls with mocks.
- **Environment first:** no test execution before endpoint, dependency, data,
  and smoke checks pass.
- **Complete API coverage:** every Stage 2 service registered in the manifest
  must have collection and environment artifacts; missing artifacts are a
  precheck failure.
- **Isolated and repeatable data:** seed and clean up data within the test
  scope; never target production data.
- **Diagnostic failure:** every failure includes test ID, service, request or
  setup context, evidence path, and likely owner.
- **Controller-owned phase transition:** update only the test sub-status and
  evidence; `sw-controller` decides when the whole test phase is done.

## Input Contract

| Input | Required | Description |
|---|---:|---|
| `requirement_id` | Yes | Existing requirement whose merged feature and design bundle are tested. |
| `project_root` | No | Workspace root; defaults to the current workspace. |
| `paths` | No | Semantic path overrides in `references/path-defaults.yaml`. |
| `service_ids` | No | Restrict execution to a declared subset; default is every manifest Stage 2 service. |
| `environment` | No | Named test environment or target URL set; defaults to project configuration. |
| `request` | No | Test focus, rerun scope, or diagnostic hint; cannot waive mandatory API prechecks. |
| `communication_language` | No | Report language; defaults to project configuration or Chinese. |
| `mode` | No | `full` (default), `smoke`, or `rerun-failed`; `smoke` cannot return `PASS` for the full gate. |

Required upstream evidence:

- merge phase is complete and the deployed test target is identified;
- the requirement manifest exists, matches the requirement ID, and lists all
  Stage 2 service API artifacts;
- integration test plan and test-environment configuration are resolvable;
- test data is isolated and the runner can write reports.

Missing evidence returns `BLOCKED` or `NEEDS_USER_INPUT`. Missing collection or
environment JSON returns `PRECHECK_FAILED` inside the report and a failing
result; it must never be silently skipped.

## External Dependency Metadata

`newman` and `python3` are mandatory. `sw-deployer` and
`sw-knowledge-agent` are optional and must be recorded as `USED`, `SKIPPED`,
or `NOT_REQUESTED` with reason, impact, and fallback.

Fallbacks:

- missing `newman` or `python3`: `BLOCKED`, because API execution is mandatory;
- `sw-deployer` unavailable: use local health checks and record that deployment
  coordination was skipped;
- `sw-knowledge-agent` unavailable: inspect environment/configuration and
  prior test reports locally.

## On Activation

### Step 0: Resolve paths and environment

Load the semantic paths from `references/path-defaults.yaml` and
`references/path-resolution.md`.
Resolve the manifest, service artifact glob, integration plan, environment
configuration, runner script, test results, and tracker targets. Report the
effective target environment without exposing secrets.

### Step 1: Validate the merged target and API preconditions

Load `references/test-environment.md`, `integration-test-plan.md`, and
`api-test-postman-schema.md`. Verify endpoints, credentials, test data, and
smoke behavior. Enumerate every Stage 2 service in the manifest and require
`collection.json` and `environment.json`; include `data.json` when declared.

### Step 2: Execute integration and API tests

Run the integration plan against real services, then run:

```bash
python scripts/newman_runner.py --requirement-id {requirement_id}
```

The runner must execute every selected service, export JUnit XML, parse total,
passed, failed, errored, skipped, and failure diagnostics, and replace the
prior idempotent result block for this requirement.

### Step 3: Analyze failures

Classify each failure as application, contract, test-data, authentication,
environment, or runner error. Route code defects to the responsible worktree,
environment defects to `sw-deployer`/the operator, and schema/precheck defects
back to the design owner. Rerun only after the cause or test input changes.

### Step 4: Write results and report

Write `knowledge/requirements/{requirement_id}/test-results.yaml` with integration and API sections, counts,
diagnostics, evidence paths, environment identity, and gate status. Update
only the matching integration-test sub-status in the tracker; do not mark the
global test phase complete unless the controller owns that transition.

## Capabilities

| Capability | Route |
|---|---|
| Semantic path resolution | `references/path-defaults.yaml` + `references/path-resolution.md` |
| Environment health | `references/test-environment.md` |
| Integration execution | `references/integration-test-plan.md` |
| API schema and artifacts | `references/api-test-postman-schema.md` |
| API execution and aggregation | `scripts/newman_runner.py` |
| Environment deployment | Optional `sw-deployer` |

## Output Contract

Return an `Integration Test Report` and write the structured result file.

**Contract version:** `2.0.0`.

```yaml
result: NEEDS_USER_INPUT | READY_FOR_GATE | PASS | FAIL | PRECHECK_FAILED | BLOCKED
requirement_id: REQ-YYYYMMDD-NNN
definition:
  contract: sw.integration-test
  version: "2.0"
resolved_paths:
  config_file: "..."
  evidence: {}
  artifact_targets: {}
environment:
  name: "..."
  base_urls: []
  health: PASS | FAIL | NOT_RUN
  smoke: PASS | FAIL | NOT_RUN
integration_tests:
  total: 0
  passed: 0
  failed: 0
  skipped: 0
  failures: []
api_tests:
  services: []
  total: 0
  passed: 0
  failed: 0
  errored: 0
  skipped: 0
  failures: []
external_capabilities: []
artifacts:
  test_results: "..."
  junit_reports: []
  service_reports: []
  tracker: "..."
validation:
  manifest_precheck: PASS | FAIL | NOT_RUN
  environment: PASS | FAIL | NOT_RUN
  integration: PASS | FAIL | NOT_RUN
  api: PASS | FAIL | NOT_RUN
  data_cleanup: PASS | FAIL | NOT_RUN
next_action: "..."
```

Status semantics:

- `READY_FOR_GATE`: inputs and environment are ready; the full suite has not
  completed.
- `PASS`: environment, integration, and every selected API suite passed.
- `FAIL`: execution completed with actionable test or environment failures.
- `PRECHECK_FAILED`: a required manifest or API artifact is missing/invalid.
- `BLOCKED`: runner, permission, target, or required dependency is unavailable.

## Acceptance Criteria

| Dimension | Acceptance criterion | Evidence | Blocking |
|---|---|---|---:|
| Input and paths | Requirement ID, environment, effective paths, and selected services are reported | `resolved_paths` + environment | Yes |
| Dependency metadata | Newman/Python and optional capabilities have declared version/type/required/status | Frontmatter + `external_capabilities` | Yes |
| Merge traceability | Tests target the merged/deployed feature and matching requirement manifest | Merge evidence + manifest | Yes |
| Environment health | All required endpoints, dependencies, data, and smoke checks pass before execution | Environment block | Yes |
| API completeness | Every selected Stage 2 service has valid collection/environment artifacts | `manifest_precheck` + service list | Yes |
| Integration execution | Declared integration cases run against real services and produce counts | Integration report | Yes |
| API execution | Newman runs all required collections and exports JUnit diagnostics | API report + XML | Yes |
| Failure analysis | Each failure has classification, owner, and evidence path | `failures[]` | Yes when failures exist |
| Data safety | Test data is isolated and cleanup result is recorded | Data/cleanup evidence | Yes |
| Tracker boundary | Only integration evidence/sub-status is updated; global test completion remains controller-owned | Tracker diff | Yes |
| Gate correctness | `PASS` requires zero environment, integration, and API failures | Result + validation | Yes |

## Memory and State Boundaries

Read the design manifest, service API artifacts, test plan, environment
configuration, and merged service endpoints. Write only test result files,
JUnit evidence, permitted test artifacts, and the integration sub-status. Never
modify service code, design contracts, or production data.

## Handoff

After `PASS`, hand the test evidence to `sw-controller` together with the
browser-test requirement. After `FAIL` or `PRECHECK_FAILED`, return the exact
owner and rerun condition; do not advance the test phase.
