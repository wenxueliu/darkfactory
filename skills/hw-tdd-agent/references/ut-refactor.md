# UT-REFACTOR: 重构优化

## What Success Looks Like

Code is cleaner while all tests remain green. No new behavior added.

## When to Refactor

After GREEN — when tests pass and you're still in the TDD loop.

## Your Approach

### What to Clean Up

- Remove duplication
- Improve names
- Extract helpers
- Simplify complex logic

### What NOT to Do

- Don't add new behavior
- Don't change APIs
- Don't ignore failing tests

### Run Tests Frequently

After each refactor:
```
run tests → all pass → next refactor
run tests → fail → undo and try differently
```

## Rules During REFACTOR

1. Keep tests green
2. Change only what's necessary
3. If stuck, leave it for later

## Verification

Before leaving REFACTOR:
- [ ] All tests still pass
- [ ] Code is cleaner
- [ ] No new behavior added

## Next

Next failing test → RED for next behavior
