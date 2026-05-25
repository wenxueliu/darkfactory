# TestVerification: 测试验证

## What Success Looks Like

Tests genuinely verify the right behavior — they fail for the right reasons and pass for the right reasons.

## Verification Checklist

### For Each RED Phase

- [ ] Test fails
- [ ] Fails for expected reason
- [ ] Test describes behavior, not implementation
- [ ] If test passes immediately, it's wrong

### For Each GREEN Phase

- [ ] Test passes
- [ ] All other tests still pass
- [ ] Output clean (no errors, warnings)
- [ ] If test fails, fix code not test

### For Each REFACTOR Phase

- [ ] All tests still pass
- [ ] Code is cleaner
- [ ] No new behavior

## Anti-Patterns

| Pattern | Problem |
|---------|--------|
| Test passes immediately | Testing existing behavior, not new |
| Test errors | Test is wrong, not code |
| Other tests fail | Regression, fix immediately |
| Test tests implementation | Should test behavior |

## When Stuck

| Problem | Solution |
|---------|----------|
| Don't know how to test | Write wished-for API, assertion first |
| Test too complicated | Design too complicated, simplify |
| Must mock everything | Code too coupled, use dependency injection |
| Test setup huge | Extract helpers, or simplify design |

## Summary

- Watch tests fail before coding
- Fix code, not tests when tests fail
- Keep all tests green during refactor
