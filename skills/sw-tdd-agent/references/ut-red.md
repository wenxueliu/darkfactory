# UT-RED: 编写失败的单元测试

## What Success Looks Like

A failing test that describes the expected behavior. The test fails because the feature is missing, not because of typos or wrong assertions.

## Your Approach

### Write One Test

Start with the simplest behavior from acceptance criteria:
- One behavior per test
- If the test name has "and" — split it
- Describe behavior, not implementation

### Test Structure

```python
def test_{behavior_description}():
    # Arrange - set up test data
    # Act - call the function
    # Assert - check expected result
```

### Run to Confirm Failure

MANDATORY — Never skip this step.

Confirm:
- Test fails (not errors)
- Failure message is what you expected
- Fails because feature is missing (not typo)

### If Test Passes Immediately

You're testing existing behavior. Fix the test to describe new behavior.

### If Test Errors

Fix the error, re-run until it fails correctly.

## Verification

Before leaving RED:
- [ ] Test fails
- [ ] Fails for expected reason
- [ ] Test describes desired behavior, not implementation

## Examples

**Good:**
```python
def test_user_email_must_contain_at_symbol():
    with pytest.raises(ValidationError):
        create_user(email="invalid-email")
```

**Bad:**
```python
def test_email_validation():  # Too vague
    result = validate_email("test@example.com")  # Will pass immediately
```

## Next

After RED is verified → UT-GREEN: Write minimal code to pass
