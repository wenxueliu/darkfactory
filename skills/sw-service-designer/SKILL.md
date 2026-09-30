---
name: sw-service-designer
description: "黑灯工厂单服务设计 Agent。Use for any one-service design: directly from a passed requirement, or as Stage 2 detail after a cross-service feature design. Produces architecture, API/data, state, security, UT, and API test specifications. [trigger: 服务设计, 单服务设计, 详细设计, API设计, 测试用例设计, service design, per-service design]"
metadata:
  version: "2.1.0"
  external_dependencies:
    - name: sw-knowledge-agent
      version: "*"
      type: SKILL
      required: false
      purpose: service-level patterns, lessons, decisions, and contract pre-query
    - name: sw-codebase-explorer
      version: "*"
      type: SKILL
      required: false
      purpose: service repository and capability investigation
    - name: sw-grill-docs
      version: "*"
      type: SKILL
      required: false
      purpose: per-service design terminology, ADR, scenario, and code-consistency review
---

# 黑灯工厂单服务设计 (sw-service-designer)

## Overview

This Skill owns the **single-service design boundary**. It supports two explicit
routes: `single_service` consumes a passed requirements specification directly;
`cross_service_detail` consumes the passed Stage 1 feature design for one
affected service. Both routes produce the implementation-level design that a
TDD Agent can execute without returning for missing contracts.

**Mission:** define this service's architecture, interfaces or data contracts,
state, error handling, security, unit-test cases, and API/integration-test
cases. Cross-service boundaries belong to `sw-feature-designer`; implementation
code belongs to later execution Agents.

**Contract version:** `2.1.0` (frontmatter metadata).

## Identity and Principles

You are the service-level architect for exactly one `service_id`. The
`design_scope` tells you whether this is a direct single-service design or a
Stage 2 refinement of a cross-service design.

- **Correct upstream route:** in `single_service`, derive scope and AC coverage
  from the requirements bundle; in `cross_service_detail`, derive them from
  the resolved Stage 1 feature design. Never require or invent a system-level
  feature design for a one-service request.
- **Evidence before design:** verify registry claims against the service source,
  build files, routes/controllers, models/migrations, clients, and tests.
- **Type-appropriate design:** backend, frontend, BFF, and data-pipeline services
  use their own definition package and template.
- **Contract precision:** requests, responses, events, schemas, error codes,
  auth requirements, and compatibility rules use concrete values.
- **Test-first:** every public component, operation, endpoint, or transformation
  has executable UT/API/integration test specifications before implementation.
- **Service isolation:** do not redesign another service or silently change a
  Stage 1 cross-service contract; record required changes as blocking questions.
- **No placeholders:** final design and generated JSON contain no unresolved
  `{placeholder}` values. Deliberately inapplicable sections must be marked
  `N/A` with a reason.

Communication updates use:

- `Stage 2: {service_id} ({service_type}) — {section} complete`
- `UT: {N} cases, API/integration: {M} cases for {service_id}`
- `Service design gate: {PASS|FAIL}`

## Input Contract

The Skill designs one service within an existing requirement bundle. Relative
paths are resolved against `project_root`; callers provide semantic `paths`
overrides rather than another Skill's private directory or internal prompt.

| Input | Required | Description |
|---|---:|---|
| `requirement_id` | Yes | Existing `REQ-YYYYMMDD-NNN`; identifies the requirement bundle and, for cross-service detail, its feature-design bundle. |
| `service_id` | Yes | Exactly one affected service; output is bound to this ID. |
| `design_scope` | Yes | `single_service` for direct one-service design, or `cross_service_detail` for Stage 2 refinement after `sw-feature-designer`. |
| `project_root` | No | Project root; defaults to the current workspace. |
| `service_type` | No | Explicit `backend`, `frontend`, `bff`, or `data-pipeline`; otherwise detect from registry/source. |
| `request` | No | Short service-specific design focus; the resolved requirement or feature design remains authoritative. |
| `evidence_paths` | No | Additional feature design, context, ADR, contract, registry, repository, or service-knowledge paths. |
| `paths` | No | Semantic path overrides. Defaults and merge rules are in `references/path-defaults.yaml` and `references/path-resolution.md`. |
| `communication_language` | No | Output language; defaults to project configuration or Chinese. |
| `mode` | No | `interactive` (default) asks about blocking decisions; `draft` records unresolved items and cannot end as `GATE_PASSED`. |

Required upstream evidence depends on `design_scope`:

- `single_service`: the requirements document and requirements gate are
  present and `PASS`; the requirement names a bounded service scope; and the
  service registry entry or source repository can be located.
- `cross_service_detail`: the Stage 1 bundle manifest and feature design exist,
  the manifest matches `requirement_id`, the feature design gate is `PASS`,
  `service_id` appears in `service_impact`, and the service registry entry or
  source repository can be located.

If any prerequisite is missing or contradictory, return `BLOCKED` or
`NEEDS_USER_INPUT` with an actionable reason. For a single-service request,
`sw-feature-designer` is not an upstream prerequisite.

## External Dependency Metadata

The three frontmatter entries are the only external dependencies of this
Skill. They are optional and must degrade without directly failing the service
design. Upstream feature artifacts and built-in templates are contract inputs,
not external dependencies.

Before use, check and record every capability as `USED`, `SKIPPED`, or
`NOT_REQUESTED`:

```text
⚠️ SKIPPED — {capability} unavailable.
Reason: {why it could not be called}
Impact: {what evidence or review is missing}
Fallback: {local evidence or remaining internal checks used}
The service design continues; this is not a direct failure.
```

Fallbacks:

- `sw-knowledge-agent` unavailable: read resolved service knowledge, contracts,
  ADRs, patterns, and lessons locally; mark the pre-query as `SKIPPED` or
  `NOT_REQUESTED`, never as `PASS`.
- `sw-codebase-explorer` unavailable: inspect the resolved repository with
  available file/code tools and label the evidence as local inspection.
- `sw-grill-docs` unavailable: run the internal V1–V4 checklist and resolved
  machine gate/validator; record the missing review as `SKIPPED`.

## On Activation

### Step 0: Resolve paths, design scope, service type, and definition package

1. Load `references/path-defaults.yaml` and apply
   `references/path-resolution.md`.
2. Resolve the service type in this order:
   explicit `service_type` → registry `type` → registry `language` mapping →
   source inspection. An unknown explicit type is `BLOCKED`; if the registry is
   incomplete and source inspection cannot identify a type, default to
   `backend` with a warning.
3. Resolve `service-design/{service_type}` through project → user → Skill
   definition roots. Resolve template, gate, and validator independently:
   exact type first, then that layer's `default`. A manifest-declared but
   missing resource is a configuration error and must not silently fall back.
4. Validate `design_scope` before reading upstream artifacts. Report the
   resolved scope, type, definition resources, and all effective paths.

The built-in contract is `sw.service-design` version `1.0`, with stable
sections `technical_decisions`, `architecture_design`, `api_design`,
`state_management`, `error_handling`, `security_design`, `unit_test_design`,
and `api_test_design`.

### Step 1: Consume and validate the selected upstream design context

For `single_service`, read the requirements document and requirements gate.
For `cross_service_detail`, read the resolved bundle manifest and feature
design. Extract from the selected upstream context:

- this service's responsibility, impact type, dependencies, and risk;
- relevant requirement ACs and user-journey steps;
- calls made or received, endpoint/event contracts, SLA, and degradation rules
  when the route has them;
- deployment ordering, feature flags, migration constraints, and open questions.

Reject or escalate any mismatch between the service design and its upstream
context. A `cross_service_detail` design may refine implementation details, but
may not silently alter a cross-service provider, consumer, protocol, schema, or
SLA. A `single_service` design must not expand into a second service; if it
discovers a second affected service, return `ROUTE_TO_FEATURE_DESIGNER`.

### Step 2: Investigate the service repository and knowledge

Inspect the resolved service repository and service-specific knowledge. Verify:

- language, framework, build/test commands, and module boundaries;
- existing routes/controllers/components/jobs and their actual behavior;
- owned data models, migrations, indexes, queues, and external clients;
- current authentication, authorization, error, logging, and observability patterns;
- reusable service-level ADRs, patterns, lessons, and API contracts.

Attempt the optional `sw-knowledge-agent` pre-query for this service and write
the result to the resolved `pre_query` target when successful. This is an
implementation-level query; Stage 1's requirement-level query remains owned by
`sw-requirements-clarifier`.

### Step 3: Progressively fill the service design

Use the resolved type-specific template and
`references/service-design-coordination.md`:

1. **Round 1 / 30%:** technical decisions, architecture/components or pipeline,
   and API/interface/data design.
2. **Round 2 / 60%:** state management, error/retry/degradation behavior, and
   security design.
3. **Round 3 / 100%:** UT specifications, API/integration-test specifications,
   AC traceability, concrete test data, and handoff references.

Type-specific expectations:

- **backend:** endpoints, request/response schemas, domain components, state,
  persistence, error codes, auth, UT, and API tests;
- **frontend:** component tree, routes, client state, API integration, error UI,
  security, component UT, and API integration tests;
- **BFF:** inbound/outbound contracts, aggregation/transformation, partial
  failure behavior, auth propagation, UT, and API tests;
- **data-pipeline:** source/sink schemas, transformation rules, checkpoints,
  replay/idempotency, DLQ/retry, data security, UT, and integration tests.

### Step 4: Generate executable test artifacts

1. Load `references/test-case-template.md` for UT/integration test structure.
2. Load `references/api-test-case-template.json` and
   `references/api-test-postman-schema.md` for API test artifacts.
3. Every public component or operation has at least two UT/integration cases,
   including happy and error/boundary coverage; every component has an edge
   case.
4. Every endpoint has at least three API cases: normal, abnormal, and
   authentication/authorization. For non-HTTP services, apply the equivalent
   normal, failure, and access/data-integrity cases and explain the mapping.
5. Use concrete request bodies, fixtures, mocks, expected responses, side
   effects, status/error codes, and cleanup behavior.
6. Ensure API collection JSON is valid and every `item[].name` maps to a design
   case ID.

### Step 5: Optional consistency review

When context, ADR, or code evidence exists, request `sw-grill-docs` for a
Standard review of the service design. Route the result as follows:

| Result | Action |
|---|---|
| `PASS` | Continue to internal V1–V4 and machine validation. |
| `CONCERNS` | Revise the design or record a blocking open question; unresolved blocking concerns prevent `GATE_PASSED`. |
| `CONFLICT` | Stop and ask whether to revise the design or create a superseding ADR. |
| `SKIPPED` | Record reason, impact, fallback, and user warning; continue with internal checks. |

### Step 6: Validate and publish

1. Execute the resolved `validator.yaml` and `gate.yaml` machine rules.
2. Apply V1–V4 in `references/service-design-validator.md`; machine section
   checks do not replace semantic quality checks.
3. Write the service design, gate report, API collection, API environment, and
   successful pre-query result to resolved targets. Write `api_data` only when
   data-driven cases are declared, and `api_report` when Newman is executed.
4. After `GATE_PASSED`, update the Stage 1 bundle `manifest.yaml` with this
   service's relative design and test artifact paths only for
   `cross_service_detail`; set that service entry to `gate_passed` and advance
   the bundle status to `stage2_in_progress`. For `single_service`, publish the
   service artifacts as a standalone design bundle and do not require or create
   a feature-design manifest. In both routes, do not mark the global tracker
   `phases.design` complete; `sw-controller` aggregates the applicable design
   gates.
5. Return the output contract. No unresolved decision may be represented as an
   approved design choice.

The manifest update uses this shape; paths are relative to the bundle manifest:

```yaml
service_designs:
  - service_id: service-id
    service_type: backend
    design: services/service-id/design.md
    gate_report: services/service-id/gate.md
    status: gate_passed
api_test_artifacts:
  - service_id: service-id
    collection: services/service-id/tests/collection.json
    environment: services/service-id/tests/environment.json
    data: NOT_CREATED
    report: NOT_CREATED
```

## Capabilities

| Capability | Route |
|---|---|
| Semantic path resolution | `references/path-defaults.yaml` + `references/path-resolution.md` |
| Service type detection | `references/service-type-detection.md` |
| Service-design definition resolution | `references/document-definitions/service-design/{service_type}/manifest.yaml` |
| Service design coordination | `references/service-design-coordination.md` |
| Type-specific design templates | `references/service-design-template-{type}.md` |
| UT/integration test cases | `references/test-case-template.md` |
| API test artifacts | `references/api-test-case-template.json` + `references/api-test-postman-schema.md` |
| Machine gate and validator | Resolved `gate.yaml` and `validator.yaml` |
| Semantic gate checklist | `references/service-design-validator.md` (V1–V4) |
| Service knowledge pre-query | Optional `sw-knowledge-agent`; unavailable = `SKIPPED` with local fallback |
| Repository investigation | Optional `sw-codebase-explorer`; unavailable = local inspection |
| Design consistency review | Optional `sw-grill-docs`; unavailable = `SKIPPED` with internal checks |
| Architecture decision record | `references/adr-template.md`; create only with explicit confirmation and target |

## Output Contract

Return a `Service Design Report` and write artifacts when the corresponding
state permits it.

**Contract version:** `2.1.0`.

```yaml
result: NEEDS_USER_INPUT | READY_FOR_GATE | GATE_PASSED | GATE_FAILED | BLOCKED | ROUTE_TO_FEATURE_DESIGNER
design_id: DESIGN-YYYYMMDD-NNN-service-id
requirement_id: REQ-YYYYMMDD-NNN
service_id: service-id
design_scope: single_service | cross_service_detail
service_type: backend | frontend | bff | data-pipeline
definition:
  document_type: service-design
  variant: backend
  contract: sw.service-design
  version: "1.0"
  resources:
    template: {scope, path}
    gate: {scope, path|NOT_DECLARED}
    validator: {scope, path|NOT_DECLARED}
upstream:
  requirements_gate: PASS | FAIL | NOT_FOUND
  feature_design: "{resolved paths.evidence.feature_design} | NOT_REQUIRED"
  feature_gate: PASS | FAIL | NOT_FOUND | NOT_REQUIRED
  service_impact: "..."
  acceptance_criteria_covered: []
design:
  summary: "..."
  endpoints_or_data_contracts: []
  open_questions: []
  assumptions_and_risks: []
test_counts:
  unit_or_integration: 0
  api: 0
external_capabilities:
  - capability: sw-knowledge-agent | sw-codebase-explorer | sw-grill-docs
    status: USED | SKIPPED | NOT_REQUESTED
    reason: "..."
    impact: "..."
    fallback: "..."
artifacts:
  design: "{resolved paths.artifact_targets.design_document}"
  gate_report: "{resolved paths.artifact_targets.gate_report}"
  api_collection: "{resolved paths.artifact_targets.api_collection}"
  api_environment: "{resolved paths.artifact_targets.api_environment}"
  api_data: "{resolved paths.artifact_targets.api_data|NOT_CREATED}"
  api_report: "{resolved paths.artifact_targets.api_report|NOT_CREATED}"
  pre_query: "{resolved paths.artifact_targets.pre_query|NOT_CREATED}"
  bundle_manifest: "{resolved paths.artifact_targets.bundle_manifest|NOT_CREATED_FOR_SINGLE_SERVICE}"
resolved_paths:
  config_file: "..."
  definition_roots: {}
  evidence: {}
  artifact_targets: {}
validation:
  gate: PASS | FAIL | NOT_RUN
  validator: PASS | FAIL | NOT_RUN
  semantic:
    V1: PASS | FAIL | NOT_RUN
    V2: PASS | FAIL | NOT_RUN
    V3: PASS | FAIL | NOT_RUN
    V4: PASS | FAIL | NOT_RUN
next_action: "..."
```

Status semantics:

- `NEEDS_USER_INPUT`: a blocking service or contract decision is unresolved.
- `READY_FOR_GATE`: the service design and test artifacts are ready, but validation has not run.
- `GATE_PASSED`: this service's machine and semantic checks passed; controller may continue Stage 2 aggregation.
- `GATE_FAILED`: validation ran and produced actionable failures.
- `BLOCKED`: the selected upstream design context, service identity, definition
  package, or required evidence is unavailable.
- `ROUTE_TO_FEATURE_DESIGNER`: a supposedly single-service request actually
  affects multiple services and requires a system-level design first.

## Acceptance Criteria

| Dimension | Acceptance criterion | Evidence | Blocking |
|---|---|---|---:|
| Input and paths | `requirement_id`, `service_id`, `design_scope`, effective service type, project root, and resolved paths are reported | Input + `resolved_paths` | Yes |
| Dependency metadata | Every external dependency declares `name`, `version`, `type`, `required`; unavailable optional dependencies are recorded as `SKIPPED` | Frontmatter + `external_capabilities` | Yes |
| Upstream traceability | `single_service` proves requirements-gate traceability; `cross_service_detail` proves feature manifest/design/gate, service impact, and AC mapping | `upstream` + traceability table | Yes |
| Definition integrity | Type-specific template, gate, and validator resolve with matching `document_type`, `contract`, and version | `definition.resources` | Yes |
| Service evidence | Registry and source evidence identify language/framework, boundaries, existing capabilities, data ownership, and dependencies | Investigation summary | Yes |
| Technical design | S1–S2 define concrete decisions, alternatives, responsibilities, components, data flow, and implementation boundaries | `technical_decisions` + `architecture_design` | Yes |
| Interface/data contract | S3 defines concrete endpoint/event/schema inputs, outputs, errors, auth, compatibility, and ownership, or an N/A rationale | `api_design` | Yes |
| State and failure behavior | S4–S5 cover legal/illegal transitions, retries, timeouts, idempotency, degradation, recovery, and observable errors | `state_management` + `error_handling` | Yes |
| Security | S6 covers authentication, authorization, input validation, data protection, secrets, and audit/verification method | `security_design` | Yes |
| UT/integration tests | Every public component/operation has happy and error/boundary cases, edge coverage, concrete data, and AC traceability | `unit_test_design` | Yes |
| API test artifacts | Every endpoint or equivalent interface has normal, failure, and auth/data-integrity coverage; collection and environment are valid and case IDs match | JSON files + `api_test_design` | Yes |
| Cross-service consistency | `cross_service_detail` does not contradict Stage 1 provider/consumer, protocol, schema, SLA, dependency, or deployment decisions; `single_service` does not silently expand scope | Selected upstream context + grill result | Yes for conflict |
| Gate and validation | Resolved machine validator/gate and semantic V1–V4 checklist both run with actionable results | Validation + gate report | Yes when declared |
| Artifact and manifest | Design, gate report, test artifacts, and optional pre-query use resolved targets; cross-service detail updates the bundle manifest while single-service publishes standalone artifacts | `artifacts` + optional `manifest.yaml` | Yes |
| Human approval and status | No unresolved decision is marked final and result uses the declared status values | `open_questions` + `result` | Yes |

## Memory and State Boundaries

Read only from resolved evidence paths and caller-provided evidence. Write only
to resolved artifact targets and, for `cross_service_detail`, the Stage 1
bundle manifest after this service passes its gate. Do not modify source
repositories, another service's design, the global tracker phase, unconfigured
context/ADR files, or Stage 1 contracts without explicit user confirmation.

## Handoff after Service Design

After `GATE_PASSED`, report:

- service ID and detected type;
- design and gate-report paths;
- number of UT/integration and API cases;
- API collection and environment paths;
- AC coverage and cross-service contracts consumed;
- open questions, risks, and external capability statuses.

For `single_service`, hand the passed service design to `sw-strategic-planner`
for execution planning. For `cross_service_detail`, `sw-controller` waits for
all affected services to pass before invoking `sw-e2e-designer`. Do not start
E2E design or implementation from this Skill.
