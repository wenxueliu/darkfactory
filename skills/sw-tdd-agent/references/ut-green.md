# UT-GREEN: 最小代码通过测试

## What Success Looks Like

The simplest code that makes the test pass. Nothing more.

## Your Approach

### Write Minimal Code

```python
# The simplest thing that could work
def create_user(email: str):
    if '@' not in email:
        raise ValidationError("Invalid email")
    return User(email=email)
```

### What NOT to Do

- Don't add features beyond the test
- Don't "improve" other code
- Don't refactor yet
- Don't add code you think you'll need later

### Run Tests

After writing code:
1. Run the failing test — should pass now
2. Run all tests — must all pass

### If Test Still Fails

Fix the code, not the test. The test is correct.

### If Other Tests Fail

Fix the other code now. Don't let debt accumulate.

## Verification

Before leaving GREEN:
- [ ] Failing test now passes
- [ ] All existing tests still pass
- [ ] Output clean (no errors, warnings)

## Next

After GREEN → UT-REFACTOR: Clean up while keeping tests green
