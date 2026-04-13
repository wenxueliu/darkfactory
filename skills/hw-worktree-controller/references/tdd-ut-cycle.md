# TDD-UT循环

## What Success Looks Like

Unit tests fail initially (RED), then pass after minimal implementation (GREEN), then code is refactored while keeping tests green (REFACTOR).

**Iron Law:** "NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST"

## Your Approach

### RED Phase: Write Failing UT

1. **Identify what to test** — Start with the simplest behavior from acceptance criteria
2. **Write the test** — Describe expected behavior, not implementation
3. **Run to confirm failure** — Test must fail for the right reason (feature missing, not typo)

**Test requirements:**
- One behavior per test
- Clear, descriptive name
- Real code (no mocks unless unavoidable)

### GREEN Phase: Minimal Code

1. **Write the simplest code** that makes the test pass
2. **No features beyond the test** — Resist the urge to "improve"
3. **Run tests** — Confirm all pass, including existing tests

### REFACTOR Phase

1. **Remove duplication**
2. **Improve names**
3. **Extract helpers if needed**

**Rules during refactor:**
- Keep tests green
- Don't add behavior
- Change only what's necessary

## TDD Loop

```
RED → GREEN → REFACTOR → RED (next test) → ...
```

Repeat until all acceptance criteria have corresponding passing tests.

## Verification Checklist

Before marking UT layer complete:

- [ ] Every function/method has a test
- [ ] Watched each test fail before implementing
- [ ] Each test failed for expected reason
- [ ] Wrote minimal code to pass each test
- [ ] All tests pass
- [ ] Output clean (no errors, warnings)

## Common Issues

| Problem | Solution |
|---------|----------|
| Test passes immediately | You're testing existing behavior, not new |
| Test errors | Fix error, re-run until it fails correctly |
| Other tests fail | Fix now, don't let debt accumulate |

## Transition

UT cycle is complete when:
1. All acceptance criteria have passing UT
2. No P0/P1/P2 issues from static analysis
3. Ready to proceed to API test cycle
