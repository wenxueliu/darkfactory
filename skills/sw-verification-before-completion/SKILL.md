---
name: sw-verification-before-completion
description: 完成前验证。Use when about to claim work is complete, fixed, or passing — before committing, creating PRs, or marking tasks DONE. Requires running verification commands and confirming output before making any success claims. Evidence before assertions, always. [trigger: 验证, verification, 完成, complete, done, fixed, passing, 提交, commit, PR]
---

# 完成前验证 (sw-verification-before-completion)

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in THIS message, you cannot claim it passes.

## When to Use

**ALWAYS before:**
- Claiming a task is DONE (status transition to DONE in Consul KV)
- Marking a bug as fixed
- Saying tests pass
- Committing code
- Creating a PR
- Moving to the next task in a workflow
- Reporting a worktree-controller status as DONE to sw-controller
- Any positive statement about work state

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Common Claims and What Verifies Them

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | `pytest` output: 0 failed | Previous run, "should pass", code review |
| Linter clean | `ruff check .` (Python) / `eslint .` (JS) / `golangci-lint run ./...` (Go) — language-specific tool output: 0 errors. Delegate to sw-lint-checker for automatic language detection and multi-tool execution. | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, "logs look good" |
| Bug fixed | Test the original symptom: passes | Code changed, assumed fixed |
| TDD cycle done | RED→GREEN→REFACTOR trace: all three verified | "I wrote a test" without seeing RED |
| Task DONE | All gates passed, all reviewers approved, tests green | Agent reports "success" |
| Review complete | Review file written to `reviews/` directory | "I reviewed it in my head" |
| Delivery ready | Delivery checklist all ✅, acceptance gates passed | "Looks good" |
| Worktree clean | `git status --porcelain` empty | "I think I staged everything" |

## Harness-Specific Verification

### Task Completion (stage-bridge)

```bash
# Before claiming task DONE, verify:
python scripts/check_control.py           # No ABORT signal
python scripts/read_context.py            # Context is updated
python scripts/log_step.py --step verify  # Log the verification step
git diff --stat                           # Show what was changed
# THEN:
python scripts/complete_task.py           # Mark task DONE (only after verification)
```

### Worktree Controller Status Report

```
Before reporting DONE to sw-controller:
✅ All TDD cycles: RED→GREEN→REFACTOR verified for each cycle
✅ All reviews: output files written to reviews/ for logic, security, performance
✅ All P0/P1/P2 issues: resolved and verified
✅ Tests: pytest output shows 0 failures
✅ Git: all changes committed, feature branch clean
```

### Code Review Completion

```
Before claiming review complete:
✅ Review file written: _context/memory/sw-shared/reviews/{task_id}-{type}.md
✅ Review contains: specific file:line references, severity ratings, fix recommendations
✅ Review covers: full diff, not just changed files
```

### Bug Fix Verification

```
Before claiming "fixed":
1. Reproduce original bug with original steps → confirm it WAS happening
2. Apply fix
3. Reproduce original bug with original steps → confirm it NO LONGER happens
4. Run full test suite → confirm no regressions
5. Claim: "Bug fixed. Reproduction steps [X] now pass. Full suite: [N/N] tests pass."
```

## Red Flags — STOP

If you catch yourself:
- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Done!", "Perfect!")
- About to commit/push without running tests
- Trusting subagent reports without independent verification
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over
- **ANY wording implying success without having run verification**

STOP. Identify the verification command. Run it. THEN make the claim.

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Tests should pass" | RUN the tests. Should ≠ does. |
| "I'm confident" | Confidence ≠ evidence. RUN the command. |
| "Just this once" | No exceptions. The iron law is absolute. |
| "Linter passed" | Linter ≠ compiler ≠ tests. Each checks different things. |
| "Previous run was green" | Code may have changed. Fresh run always. |
| "Agent said success" | Verify independently. Subagents can be wrong. |
| "I'm tired" | Exhaustion ≠ excuse. Verification protects tired humans from bad code. |
| "Partial check is enough" | Partial proves nothing. Run the full command. |
| "Different words so rule doesn't apply" | Spirit over letter. Any success-implying language triggers this rule. |

## Key Patterns

**Tests:**
```
✅ [Run pytest] [See: 34/34 pass, 0 failed] "All 34 tests pass"
❌ "Should pass now" / "Looks correct" / "Added tests for it"
```

**Bug fix:**
```
✅ [Run reproduction steps] [Bug no longer reproduces] [Run full suite: 34/34 pass]
   "Bug fixed. Reproduction confirmed. No regressions."
❌ "Changed the code, should be fixed"
```

**TDD regression test (RED-GREEN):**
```
✅ Write test → Run (RED: test fails) → Implement fix → Run (GREEN: test passes)
   → Revert fix → Run (RED: test fails again) → Restore fix → Run (GREEN)
❌ "I've written a test for the bug" (without verifying RED-GREEN-RED-GREEN)
```

**Task DONE:**
```
✅ All 3 reviews written to disk and checked → pytest: 0 failures → git status: clean
   → complete_task.py executed → "Task build-api marked DONE in Consul KV"
❌ "Reviews done, tests passing" (without checking review files or running tests)
```

## Why This Matters

- "I don't believe you" — trust broken, and trust is the foundation of human-AI collaboration
- Undefined functions shipped — would crash in production
- Missing requirements shipped — incomplete features reach users
- Time wasted on false completion → redirect → rework → costs compound
- In Harness: a task falsely marked DONE cascades — Aggregator activates downstream tasks that depend on broken code, creating a chain reaction of failures

## Integration with Harness System

**With sw-systematic-debugging:**
- After applying a fix (Phase 4), run verification-before-completion BEFORE claiming the bug is fixed
- The debugging skill's Phase 4, Step 3 ("Verify Fix") is the trigger point

**With sw-tdd-agent:**
- After each RED→GREEN→REFACTOR cycle, verify before committing
- After all TDD cycles complete, verify full test suite before reporting DONE

**With sw-worktree-controller:**
- Before reporting DONE/DONE_WITH_CONCERNS to sw-controller, verify all gates
- Verify review files exist on disk, not just "review completed" claims

**With sw-controller:**
- Before advancing to the next phase, verify current phase gates
- Before declaring delivery ready, run the delivery acceptance checklist

**With stage-bridge:**
- Before calling `complete_task.py`, run verification commands
- Before calling `feedback_resolve.py`, verify the fix actually resolves the feedback

## On Activation

When invoked for verification:
1. Identify what claim is about to be made
2. Determine the verification command(s) for that claim
3. Run the command(s) — fresh, complete output
4. Read and analyze the output
5. State the verified result with evidence
6. Only then proceed with the claim/action

Never skip step 3. Never assume step 4's result before seeing it.
