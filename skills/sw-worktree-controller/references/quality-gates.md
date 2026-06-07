# 质量门禁检查

## What Success Looks Like

All quality gates pass — P0/P1/P2 issues resolved, no exceptions without human approval.

## Gate Categories

| Gate | Check | Threshold |
|------|-------|-----------|
| UT Coverage | % code covered by unit tests | Configurable |
| API Test Pass | All API contract tests (newman) | 100% (newman exit 0 + JUnit failures==0) |
| Code Style | Style guide compliance — delegate to sw-lint-checker | P0/P1/P2 only |
| Security Scan | Vulnerability scan | P0/P1/P2 only |
| Review Closure | All P0/P1/P2 resolved across 4 reviewers (logic, security, performance, context) | 100% |

## Reviewer Roster (4-way parallel, mandatory)

The worktree controller **must** fan out to all four reviewers after TDD Layer 1 + Layer 2 pass:

| Reviewer | Slot |
|----------|------|
| `sw-reviewer-logic` | correctness |
| `sw-reviewer-security` | vulnerabilities |
| `sw-reviewer-performance` | bottlenecks |
| `sw-reviewer-context` | missed requirements / hidden context |

**sw-reviewer-context is non-optional** — it mines git history, GitHub issues, and codebase cross-references for requirements that should have informed the implementation but didn't. Skipping it is what allowed context-blind code to merge.

## Issue Severity

| Level | Name | Must Fix? |
|-------|------|-----------|
| P0 | Fatal | Yes, blocks all phases |
| P1 | Severe | Yes, blocks next phase |
| P2 | General | Yes, blocks next phase |
| P3 | Suggestion | No, document only |

## Your Approach

1. **Collect gate results** — Run static analysis, coverage, security scan
2. **Aggregate issues** by severity
3. **If P0/P1/P2 exist:**
   - Attempt fix (iteration)
   - If max iterations reached → escalate
4. **If all clear** → gate passed

## Gate Execution

```bash
# Run gates
pytest --cov --cov-report=term tests/unit/

# Standards check (delegate to sw-lint-checker for all languages)
# Covers: ruff/eslint/golangci-lint/shellcheck/markdownlint/etc.
# See skills/sw-lint-checker/references/ for language-specific tool instructions

security-scan.sh

# Aggregate results
# If P0/P1/P2 → fix and re-run
# If all clear → proceed
```

## Configuration

Respect config:
- `min_iteration_before_human` — iterations before escalating
- `enabled_reviewers` — which review types ran

## Transition

Quality gates pass when:
1. UT coverage meets threshold
2. All API tests pass
3. No P0/P1/P2 issues remain
4. Human approved any exceptions
