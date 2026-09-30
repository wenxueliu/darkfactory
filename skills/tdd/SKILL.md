---
name: tdd
description: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
metadata:
  version: "2.0.0"
  external_dependencies: []
---

# Test-Driven Development

TDD is the red → green loop. This skill is the reference that makes that loop produce tests worth keeping: what a good test is, where tests go, the anti-patterns, and the rules of the loop. Every section applies on every cycle — consult them before and during the loop, not after.

When exploring the codebase, read `knowledge/CONTEXT.md` (if it exists) so test names and interface vocabulary match the project's domain language, and respect ADRs in `knowledge/decisions/`.

## What a good test is

Tests verify behavior through public interfaces, not implementation details. Code can change entirely; tests shouldn't. A good test reads like a specification — "user can checkout with valid cart" tells you exactly what capability exists — and survives refactors because it doesn't care about internal structure.

See [tests.md](tests.md) for examples and [mocking.md](mocking.md) for mocking guidelines.

## Seams — where tests go

A **seam** is the public boundary you test at: the interface where you observe behavior without reaching inside. Tests live at seams, never against internals.

**Test only at pre-agreed seams.** Before writing any test, write down the seams under test and confirm them with the user. No test is written at an unconfirmed seam. You can't test everything — agreeing the seams up front is how testing effort lands on the critical paths and complex logic instead of every edge case.

Ask: "What's the public interface, and which seams should we test?"

When the shape of that interface is itself in question — how deep the module is, where the seam belongs, what the interface should expose — call the Skill tool with "codebase-design" for the vocabulary. It is the shared source of the module, interface, depth, seam, adapter, leverage and locality terms, and it is a reference to consult, not a session to run.

## Anti-patterns

- **Implementation-coupled** — mocks internal collaborators, tests private methods, or verifies through a side channel (querying the database instead of using the interface). The tell: the test breaks when you refactor but behavior hasn't changed.
- **Tautological** — the assertion recomputes the expected value the way the code does (`expect(add(a, b)).toBe(a + b)`, a snapshot derived by hand the same way, a constant asserted equal to itself), so it passes by construction and can never disagree with the code. Expected values must come from an independent source of truth — a known-good literal, a worked example, the spec.
- **Horizontal slicing** — writing all tests first, then all implementation. Bulk tests verify _imagined_ behavior: you test the _shape_ of things rather than user-facing behavior, the tests go insensitive to real changes, and you commit to test structure before understanding the implementation. Work in **vertical slices** instead — one test → one implementation → repeat, each test a **tracer bullet** that responds to what the last cycle taught you.

## Rules of the loop

- **Red before green.** Write the failing test first, then only enough code to pass it. Don't anticipate future tests or add speculative features.
- **One slice at a time.** One seam, one test, one minimal implementation per cycle.
- **Refactoring is not part of the loop.** It belongs to the review stage (see the `code-review` skill), not the red → green implementation cycle.

## Input Contract

| Input | Required | Description |
|---|---:|---|
| `requirement_or_bug` | Yes | 需求、缺陷或待验证行为。 |
| `seams` | Yes | 用户确认的测试 seam 和边界。 |
| `project_root` | No | 项目根目录。 |

## External Dependency Metadata

`metadata.external_dependencies` 为空。该 Skill 只描述 TDD 方法，可独立应用到 pytest、Jest、JUnit、Go test 等测试栈。

## Output Contract

返回或写入测试变更摘要，包含已确认 seam、RED 测试、最小实现、GREEN 结果、REFACTOR 后结果和未覆盖风险。测试规范本身不替用户修改生产代码。

## Acceptance Criteria

- seam 在写测试前已明确，测试期望来自独立规范/示例而非实现复算。
- 每个切片遵循 RED → GREEN → REFACTOR，不预先批量编写未来测试。
- 测试覆盖关键行为、错误路径和回归边界。
- 失败测试和通过测试输出均可复现，未验证的行为标记为缺口。
