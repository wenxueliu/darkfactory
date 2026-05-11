# 计划模板 (Plan Template)

完整的工作计划 markdown 模板。包含所有必需的章节和子章节。在下文中的 `{placeholder}` 标记替换为具体内容。

---

## 模板结构

生成计划到: `{project-root}/_bmad/memory/hw-shared/plans/{plan-name}.md`

```markdown
# {Plan Title}

> **计划名称**: {kebab-case reference name}
> **创建时间**: {YYYY-MM-DD}
> **创建者**: hw-strategic-planner (Prometheus)
> **状态**: Ready for Execution

---

## TL;DR

> **Quick Summary**: [1-2 句话捕获核心目标和方案]
>
> **Deliverables**: [具体输出的项目符号列表]
> - [输出 1: 具体文件/端点/功能]
> - [输出 2]
> - [输出 3]
>
> **Estimated Effort**: [Quick (<1h) | Short (1-4h) | Medium (1-2d) | Large (3d+) | XL (5d+)]
> **Parallel Execution**: [YES - N waves | NO - sequential]
> **Critical Path**: [Task X -> Task Y -> Task Z -> Final Verification]

{使用此工作量估算指南:
- Quick: <1 小时，通常 <5 个简单任务
- Short: 1-4 小时，5-15 个任务
- Medium: 1-2 天，15-30 个任务
- Large: 3+ 天，30-50 个任务
- XL: 5+ 天，50+ 个任务}

---

## Context

### Original Request

[用户最初的描述，尽可能使用原话]

### Interview Summary

**Key Discussions**:
- [Point 1]: [用户的决定/偏好]
- [Point 2]: [达成一致的方法]
- [Point 3]: [关键权衡决策]

**Key Decisions**:
- [Decision 1]: [理由]
- [Decision 2]: [理由]

### Research Findings

**Codebase Analysis** (via hw-codebase-explorer):
- [Finding 1]: [含义 — 这对计划意味着什么]
- [Finding 2]: [建议 — 在此基础上该怎么做]

**External Research** (via hw-external-researcher):
- [Finding 1]: [含义]
- [Finding 2]: [建议]

### Pre-Planning Review (hw-pre-planning-consultant)

**Identified Gaps** (addressed):
- [Gap 1]: [如何解决]
- [Gap 2]: [如何解决]

**Guardrails Recommended**:
- [Guardrail 1]
- [Guardrail 2]

---

## Work Objectives

### Core Objective

[1-2 句话: 我们在达成什么目标]

### Concrete Deliverables

{具体的、可计数的、可独立验证的项目}

- [ ] `path/to/file1.ts` — [这个文件做什么]
- [ ] `path/to/file2.ts` — [这个文件做什么]
- [ ] `POST /api/endpoint` — [这个端点做什么]
- [ ] UI Component: `<ComponentName>` — [这个组件做什么]

### Definition of Done

- [ ] [可验证的条件 1 — 带具体命令]
- [ ] [可验证的条件 2]
- [ ] [可验证的条件 3]

{每个条件必须是二元、可测试、可证明的。无主观条件。}

### Must Have

{不可协商的需求。没有这些，工作就是失败的。}

- [Non-negotiable requirement 1]
- [Non-negotiable requirement 2]
- [Non-negotiable requirement 3]

### Must NOT Have (Guardrails)

{来自 Metis 审查的明确排除项 + AI-slop 防范模式 + 范围边界}

- [Explicit exclusion 1]
- [AI slop pattern to avoid — 如: "No premature abstraction — solve the specific case first"]
- [Scope boundary — 如: "Do NOT modify the existing payment module"]
- [Scope boundary — 如: "Do NOT add user registration — out of scope for this plan"]

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** - ALL verification is agent-executed. No exceptions.
> Acceptance criteria requiring "user manually tests/confirms" are FORBIDDEN.

### Test Decision

- **Infrastructure exists**: [YES/NO]
- **Automated tests**: [TDD / Tests-after / None]
- **Framework**: [pytest / jest / vitest / bun test / none]
- **If TDD**: Each task follows RED (failing test) -> GREEN (minimal impl) -> REFACTOR

### QA Policy

Every task MUST include agent-executed QA scenarios.
Evidence saved to `{project-root}/_bmad/memory/hw-shared/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Frontend/UI**: Use Playwright (browser automation skill) — Navigate, interact, assert DOM, screenshot
- **TUI/CLI**: Use tmux (interactive bash) — Run command, send keystrokes, validate output
- **API/Backend**: Use Bash (curl) — Send requests, assert status + response fields
- **Library/Module**: Use Bash (REPL or test runner) — Import, call functions, compare output

---

## Execution Strategy

### Parallel Execution Waves

> Maximize throughput by grouping independent tasks into parallel waves.
> Each wave completes before the next begins.
> Target: 5-8 tasks per wave. Fewer than 3 per wave (except final) = under-splitting.

```
Wave 1 (Start Immediately — foundation + scaffolding):
├── Task 1: Project scaffolding + config
├── Task 2: Design system tokens / constants
├── Task 3: Type/interface/schema definitions
├── Task 4: Storage/DB interface + mock impl
├── Task 5: Shared middleware/utilities
└── Task 6: Client/API base module

Wave 2 (After Wave 1 — core modules, MAX PARALLEL):
├── Task 7: Core business logic (depends: 3, 4)
├── Task 8: API endpoints (depends: 3, 4, 6)
├── Task 9: Secondary impl (depends: 4)
├── Task 10: Error handling + retry (depends: 7)
├── Task 11: UI layout + navigation (depends: 2)
├── Task 12: API client + hooks (depends: 3, 6)
└── Task 13: Monitoring/telemetry (depends: 5)

Wave 3 (After Wave 2 — integration + UI):
├── Task 14: Main route combining modules (depends: 5, 10, 13)
├── Task 15: UI data visualization (depends: 11, 12)
├── Task 16: Integration tests (depends: 14, 15)
...

Wave FINAL (After ALL tasks — 4 parallel reviews, then user okay):
├── F1: Plan Compliance Audit
├── F2: Code Quality Review
├── F3: Real Manual QA
└── F4: Scope Fidelity Check
→ Present results → Get explicit user okay

Critical Path: T1 -> T4 -> T7 -> T10 -> T14 -> T16 -> F1-F4 -> user okay
Parallel Speedup: ~{N}% faster than sequential
Max Concurrent: {N} (Wave {X})
```

### Dependency Matrix

{完整列出所有任务的依赖关系}

```
- Task 1-6: No dependencies (Wave 1 — Start Immediately)
- Task 7: depends on 3 (types), 4 (storage interface)
- Task 8: depends on 3 (types), 4 (storage), 6 (client base)
- Task 9: depends on 4 (storage interface)
- ...
```

### Agent Dispatch Summary

{按 Wave 汇总推荐 Agent 配置}

```
- Wave 1: {N} tasks — T1->quick, T2->quick, T3->quick, ...
- Wave 2: {N} tasks — T7->deep, T8->unspecified-high, ...
- Wave 3: {N} tasks — ...
- Wave FINAL: 4 tasks — F1->oracle, F2->unspecified-high, F3->unspecified-high, F4->deep
```

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: WHAT TO DO + QA SCENARIOS + References + Commit info.
> **A task WITHOUT QA Scenarios is INCOMPLETE. No exceptions.**

---

{Each TODO follows this exact format:}

- [ ] {N}. {Task Title}

  **What to do**:
  - [Clear implementation step 1 — specific, actionable]
  - [Clear implementation step 2]
  - [Clear implementation step 3]
  - [Test cases to cover — specific inputs/outputs]

  **Must NOT do**:
  - [Specific exclusion from guardrails]
  - [Scope boundary to respect]

  **Recommended Agent Profile**:
  > Select category + skills based on task domain. Justify each choice.
  - **Category**: `[quick | deep | unspecified-high | unspecified-low | visual-engineering]`
    - Reason: [Why this category fits the task domain]
  - **Skills**: [`skill-1`, `skill-2`]
    - `skill-1`: [Why needed — domain overlap explanation]
    - `skill-2`: [Why needed — domain overlap explanation]
  - **Skills Evaluated but Omitted**:
    - `omitted-skill`: [Why domain doesn't overlap]

  **Parallelization**:
  - **Can Run In Parallel**: YES | NO
  - **Parallel Group**: Wave {N} (with Tasks {X, Y, Z}) | Sequential
  - **Blocks**: [Tasks that depend on this task completing]
  - **Blocked By**: [Tasks this depends on] | None (can start immediately)

  **References** (CRITICAL — Be Exhaustive):

  > The executor has NO context from your interview. References are their ONLY guide.
  > Each reference must answer: "What should I look at and WHY?"

  **Pattern References** (existing code to follow):
  - `path/to/similar/file.ts:45-78` — [Specific pattern to follow, e.g., "Authentication flow pattern (JWT creation, refresh token handling)"]

  **API/Type References** (contracts to implement against):
  - `path/to/types.ts:TypeName` — [Shape to implement, e.g., "Response shape for user endpoints"]

  **Test References** (testing patterns to follow):
  - `path/to/__tests__/similar.test.ts:describe("section")` — [Test structure and mocking patterns]

  **External References** (libraries and frameworks):
  - Official docs: `https://example.com/docs` — [Specific section and what to look for]

  **WHY Each Reference Matters** (explain the relevance):
  - Don't just list files — explain what pattern/information the executor should extract
  - Bad: `src/utils.ts` (vague, which utils? why?)
  - Good: `src/utils/validation.ts:sanitizeInput()` — Use this sanitization pattern for user input

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.
  > Every criterion MUST be verifiable by running a command or using a tool.

  **If TDD (tests enabled):**
  - [ ] Test file created: `path/to/test.test.ts`
  - [ ] `{test command}` -> ALL PASS ({N} tests, 0 failures)

  **QA Scenarios (MANDATORY — task is INCOMPLETE without these):**

  > **This is NOT optional. A task without QA scenarios WILL BE REJECTED.**
  >
  > Write scenario tests that verify the ACTUAL BEHAVIOR of what you built.
  > Minimum: 1 happy path + 1 failure/edge case per task.
  > Each scenario = exact tool + exact steps + exact assertions + evidence path.
  >
  > **The executing agent MUST run these scenarios after implementation.**
  > **The orchestrator WILL verify evidence files exist before marking task complete.**

  ```
  Scenario: {Happy path — what SHOULD work}
    Tool: [Playwright / interactive_bash / Bash (curl) / Bash (test runner)]
    Preconditions: [Exact setup state — server running, DB populated with X, etc.]
    Steps:
      1. [Exact action — specific command/selector/endpoint, no vagueness]
      2. [Next action — with expected intermediate state]
      3. [Assertion — exact expected value, not "verify it works"]
    Expected Result: [Concrete, observable, binary pass/fail]
    Failure Indicators: [What specifically would mean this failed]
    Evidence: {project-root}/_bmad/memory/hw-shared/evidence/task-{N}-{scenario-slug}.{ext}

  Scenario: {Failure/edge case — what SHOULD fail gracefully}
    Tool: [same format]
    Preconditions: [Invalid input / missing dependency / error state]
    Steps:
      1. [Trigger the error condition]
      2. [Assert error is handled correctly]
    Expected Result: [Graceful failure with correct error message/code]
    Evidence: {project-root}/_bmad/memory/hw-shared/evidence/task-{N}-{scenario-slug}-error.{ext}
  ```

  > **Specificity requirements — every scenario MUST use:**
  > - **Selectors**: Specific CSS selectors (`.login-button`, not "the login button")
  > - **Data**: Concrete test data (`"test@example.com"`, not `"[email]"`)
  > - **Assertions**: Exact values (`text contains "Welcome back"`, not "verify it works")
  > - **Timing**: Wait conditions where relevant (`timeout: 10s`)
  > - **Negative**: At least ONE failure/error scenario per task
  >
  > **Anti-patterns (your scenario is INVALID if it looks like this):**
  > - "Verify it works correctly" — HOW? What does "correctly" mean?
  > - "Check the API returns data" — WHAT data? What fields? What values?
  > - "Test the component renders" — WHERE? What selector? What content?
  > - Any scenario without an evidence path

  **Evidence to Capture**:
  - [ ] Each evidence file named: task-{N}-{scenario-slug}.{ext}
  - [ ] Screenshots for UI, terminal output for CLI, response bodies for API

  **Commit**: YES | NO (groups with {N})
  - Message: `{type}({scope}): {description}`
  - Files: `path/to/file1, path/to/file2`
  - Pre-commit: `{test/lint command}`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must PASS. Present consolidated results to user and get explicit "okay" before completing.
>
> **Do NOT auto-proceed after verification. Wait for user's explicit approval before marking work complete.**
> **Never mark F1-F4 as checked before getting user's okay.** Rejection or user feedback -> fix -> re-run -> present again -> wait for okay.

- [ ] F1. **Plan Compliance Audit** (recommended: `oracle` / strategic review profile)

  Read the plan end-to-end executing the following:
  - **Must Have verification**: For each "Must Have" item, verify implementation exists (read file, curl endpoint, run command)
  - **Must NOT Have verification**: Search codebase for forbidden patterns — reject with file:line if found
  - **Evidence verification**: Check evidence files exist in `_bmad/memory/hw-shared/evidence/`
  - **Deliverable verification**: Compare deliverables list against actual implementation

  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | Evidence [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** (recommended: `unspecified-high` profile)

  Run static analysis and review all changed files:
  - **Build**: Compile/transpile check — `{build command}` must succeed with 0 errors
  - **Lint**: Run linter — `{lint command}` must pass with 0 warnings
  - **Tests**: Run full test suite — `{test command}` must show ALL PASS
  - **Code patterns**: Check for `as any`/`@ts-ignore`, empty catches, console.log in production, commented-out code, unused imports
  - **AI slop detection**: Excessive comments, over-abstraction, generic names (data/result/item/temp)

  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT: APPROVE/REJECT`

- [ ] F3. **Real Manual QA** (recommended: `unspecified-high` + Playwright/browser skill if UI)

  Start from clean state. Execute EVERY QA scenario from EVERY task:
  - **Per-Scenario Execution**: Follow exact steps from each task's QA scenarios, capture evidence
  - **Integration Testing**: Test features working together across tasks, not just in isolation
  - **Edge Cases**: Empty state, invalid input, rapid actions, concurrent access
  - **Evidence Collection**: Save all evidence to `_bmad/memory/hw-shared/evidence/final-qa/`

  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT: APPROVE/REJECT`

- [ ] F4. **Scope Fidelity Check** (recommended: `deep` profile)

  For each task: verify implementation matches specification exactly:
  - **Spec-Implementation Mapping**: Read "What to do" for each task, read actual diff (git diff/log), verify 1:1 match
  - **Completeness Check**: Everything in spec was built (no missing functionality)
  - **Anti-Creep Check**: Nothing beyond spec was built (no unauthorized additions)
  - **Must NOT Do Compliance**: Check each task's "Must NOT do" constraints
  - **Cross-Task Contamination**: Detect Task N touching Task M's files
  - **Unaccounted Changes**: Flag any files modified that aren't listed in any task

  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT: APPROVE/REJECT`

---

## Commit Strategy

{将任务分组到逻辑提交中}

```
Commit 1: {type}({scope}): {description}
  Files: path/to/file1.ts, path/to/file2.ts
  Pre-commit: {test/lint command}

Commit 2: {type}({scope}): {description}
  Files: path/to/file3.ts, path/to/file4.ts
  Pre-commit: {test/lint command}

...
```

---

## Success Criteria

### Verification Commands

```bash
# {What this verifies}
{command}  # Expected: {output}

# {What this verifies}
{command}  # Expected: {output}
```

### Final Checklist

- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tasks completed (N/N)
- [ ] All tests pass (N/N)
- [ ] All QA scenarios executed with evidence
- [ ] All Final Verification reviews APPROVED
- [ ] User explicitly approved completion
- [ ] Evidence directory: `_bmad/memory/hw-shared/evidence/` populated
- [ ] Knowledge base updated (if auto_update enabled)
```

---

## 模板使用规则

### 必须包含的章节

以下章节是 **MANDATORY** 的，不能省略:

1. TL;DR
2. Context (含 4 个子章节)
3. Work Objectives (含 5 个子章节)
4. Verification Strategy (含 Test Decision + QA Policy)
5. Execution Strategy (含 Waves + Dependency Matrix)
6. TODOs (含所有任务)
7. Final Verification Wave (含 F1-F4)
8. Commit Strategy
9. Success Criteria

### 占位符替换规则

- `{Plan Title}`: 用描述性标题替换。格式: `动词 + 名词 + [for/in/on + 上下文]`
  - 好: "Add JWT Authentication for REST API"
  - 好: "Refactor User Module to Clean Architecture"
  - 坏: "Plan for auth stuff"

- `{plan-name}`: kebab-case, 与文件标题匹配
  - `jwt-authentication-rest-api.md`
  - `refactor-user-module-clean-architecture.md`

- `{placeholder}` 标记: 所有花括号占位符必须替换为具体内容。绝不留 `{placeholder}` 在最终计划中。

### 格式规则

- 使用 `##` 作为主要章节标题
- 使用 `###` 作为子章节标题
- 使用 `- [ ]` 作为 TODO 复选框
- 使用 `-` 作为顶级列表项，`  -` 作为嵌套
- 代码块使用三个反引号并指定语言
- 引用块 (`>`) 用于 TL;DR 和 Verification Strategy 摘要
- 水平线 (`---`) 用于章节分隔
- 使用 `|` 管道分隔的表格

### 内容质量规则

1. **具体优于抽象**: 每个声明必须引用具体文件、命令或数字
2. **可验证的完成定义**: 每个 delivery 必须是可独立验证的
3. **零模糊术语**: "完善", "改进", "优化" 在没有具体度量时被视为模糊
4. **QA 场景必须可执行**: 如果 QA 步骤不能从终端执行（需要人类判断），则该场景无效
