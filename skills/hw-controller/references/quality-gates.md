# 质量门禁验证

## What Success Looks Like

All quality gates pass before phase transitions:
- P0/P1/P2 issues are resolved (no exceptions)
- P3 suggestions are documented but don't block
- Human has approved any deviations

## Gate Categories

| Gate | Check | Blocking? |
|------|-------|-----------|
| UT Coverage | % of code covered by unit tests | Yes (configurable threshold) |
| API Test Pass | All API contract tests pass | Yes |
| Code Style | Style guide compliance | Yes (P0/P1/P2 only) |
| Security | Vulnerability scan | Yes (P0/P1/P2 only) |
| Code Review | Heterogeneous agent review passed | Yes (P0/P1/P2 only) |

## Issue Severity

| Level | Name | Action |
|-------|------|--------|
| P0 | Fatal | Must fix, blocks all phases |
| P1 | Severe | Must fix, blocks next phase |
| P2 | General | Must fix, blocks next phase |
| P3 | Suggestion | Optional, document only |

## Your Approach

**Gates are enforced, not bypassed.** The only exception is explicit human approval after review.

**Gate verification per worktree:**
1. Collect review reports from `{project-root}/_bmad/memory/hw-shared/reviews/{task_id}-*.md`
2. Tally issues by severity
3. If P0/P1/P2 exist → report to Worktree Controller for fix
4. If all clear → gate passed

**Overall gate check before merge:**
1. All worktrees have passed their gates
2. No unresolved P0/P1/P2 across the system
3. Human has not overridden any gate

## Configuration

Respect config settings:
- `min_iteration_before_human`: iterations before human must review
- `enabled_reviewers`: which review types are active

## Transition Gate

Quality gates pass when:
1. All P0/P1/P2 issues resolved or human-approved
2. UT coverage meets threshold
3. All API tests pass
4. Human has signed off (if required)
