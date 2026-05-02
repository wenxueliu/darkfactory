# TestCaseTemplate: 测试用例模板

## What This Is

A reusable structural template for every test case written in the TDD cycle. Fill this out in RED phase before writing the actual test code. The template enforces consistency, completeness, and the "one behavior per test" rule.

## When to Use

Every time you enter UT-RED or API-RED. Load this template, fill in the sections, then write the test code from the filled template.

---

## Test Case Structure

### 1. Metadata

| Field | Value |
|-------|-------|
| **Test ID** | `{layer}-{module}-{seq}` (e.g., `UT-user-001`, `API-auth-003`) |
| **Priority** | P0 / P1 / P2 / P3 (see priority definitions below) |
| **Status** | RED / GREEN / REFACTORED |
| **Related Requirement** | Task ID or acceptance criteria reference |
| **Layer** | `UT` (unit) or `API` (integration/contract) |

### 2. Behavior Under Test

**Single sentence** describing the expected behavior, NOT the implementation:

```
WHEN {condition}
THEN {expected outcome}
```

**Examples:**

| Good (behavior) | Bad (implementation) |
|-----------------|---------------------|
| WHEN user email has no @ symbol THEN validation fails | Test the email validator function |
| WHEN order total is negative THEN checkout returns error | Test checkout with amount=-5 |
| WHEN token is expired THEN API returns 401 | Test the token expiry check |

### 3. Arrange (Test Data)

What must exist before the test runs:

- **Preconditions:** State of the system before the test
- **Test Data:** Specific values, edge values, boundary values
- **Fixtures:** Database rows, files, configuration needed
- **Mocks/Stubs:** External dependencies to isolate (only if unavoidable — prefer real code)

```
GIVEN {precondition}
AND {additional context}
```

### 4. Act (Execution)

The single action being tested. One action per test case.

```
WHEN {single action or function call}
```

### 5. Assert (Verification)

What must be true after the action. Use concrete values, not vague descriptions.

- **Primary assertion:** The main expected outcome
- **Side effects:** State changes, logs, events triggered
- **Error conditions:** Expected exceptions, error codes, messages

```
THEN {expected result}
AND {additional verification}
```

### 6. Edge Cases Checklist

Mark which edge cases this test covers (one test may cover 1-2 edge cases, not all):

- [ ] **Null / None input** — What happens with missing data?
- [ ] **Empty input** — Empty string, empty list, zero value
- [ ] **Boundary values** — Max, min, off-by-one
- [ ] **Invalid format** — Wrong type, malformed data
- [ ] **Duplicate** — Same operation repeated
- [ ] **Concurrent** — Race conditions, parallel access
- [ ] **Large volume** — Many items, large payloads
- [ ] **Timeout** — Slow dependencies, deadline exceeded
- [ ] **Authorization** — Missing permissions, wrong role
- [ ] **State dependency** — Wrong state for the operation

If none of the above apply, state why. Every test should cover at least one edge condition.

---

## Priority Definitions

| Priority | Criteria | Gate Impact |
|----------|----------|-------------|
| **P0** | Core path, security boundary, data integrity | Blocks all phases |
| **P1** | Important feature, common workflow, error handling | Blocks next phase |
| **P2** | Secondary feature, edge case, non-critical validation | Must fix, blocks next phase |
| **P3** | Nice-to-have, cosmetic, exploratory | Document only |

---

## Test Code Skeleton

### Python (pytest)

```python
import pytest

def test_{behavior_snake_case}():
    """WHEN {condition} THEN {expected outcome}"""
    # Arrange
    # TODO: set up preconditions and test data

    # Act
    # TODO: call the function/method under test

    # Assert
    # TODO: verify the expected outcome
```

### JavaScript/TypeScript (Jest / Vitest)

```typescript
describe('{module_name}', () => {
  it('should {expected behavior}', () => {
    // Arrange
    // TODO: set up preconditions and test data

    // Act
    // TODO: call the function/method under test

    // Assert
    // TODO: verify the expected outcome
  });
});
```

### Go (testing)

```go
func Test{FunctionName}{Behavior}(t *testing.T) {
    // Arrange
    // TODO: set up preconditions and test data

    // Act
    // TODO: call the function under test

    // Assert
    // TODO: verify the expected outcome
}
```

### Java (JUnit 5)

```java
@Test
@DisplayName("{expected behavior}")
void {methodName}() {
    // Arrange
    // TODO: set up preconditions and test data

    // Act
    // TODO: call the method under test

    // Assert
    // TODO: verify the expected outcome
}
```

**Language-specific patterns** live in `references/patterns-{language}.md`. If a pattern file doesn't exist for your target language, use the skeleton above and follow the language's standard test conventions.

---

## Pre-RED Verification (Must Complete Before Writing Test Code)

- [ ] Behavior is a single sentence in WHEN/THEN format
- [ ] Behavior describes WHAT, not HOW
- [ ] Test name does not contain "and" (if it does, split into two tests)
- [ ] Priority assigned (P0-P3)
- [ ] At least one edge case identified and checked
- [ ] Test data values are concrete, not abstract
- [ ] Assertion expectations are concrete, not vague

---

## Post-RED Verification (After Writing Test Code)

- [ ] Test runs and fails
- [ ] Failure is for the expected reason (feature missing, not typo)
- [ ] Test does NOT pass immediately (if it does, you're testing existing behavior)
- [ ] Test does NOT error (if it does, fix the test code first)
- [ ] One behavior per test confirmed

## Post-GREEN Verification (After Writing Production Code)

- [ ] Test now passes
- [ ] All other tests still pass (no regression)
- [ ] Output clean (no warnings, no errors)
- [ ] Minimal code written (no features beyond what the test demands)

---

## Complete Example

### Filled Template

| Field | Value |
|-------|-------|
| **Test ID** | `UT-user-001` |
| **Priority** | P0 |
| **Status** | RED |
| **Related Requirement** | AC-3: User email must contain @ |
| **Layer** | UT |

**Behavior:** WHEN user email has no @ symbol THEN validation raises ValidationError

**Arrange:**
- GIVEN the user creation function is available
- AND no users exist in the system

**Act:** Call `create_user(email="invalid-email")`

**Assert:**
- THEN `ValidationError` is raised
- AND the error message contains "Invalid email"

**Edge Cases:** [x] Invalid format

### Generated Test Code (Python)

```python
import pytest

def test_user_email_must_contain_at_symbol():
    """WHEN user email has no @ symbol THEN validation raises ValidationError"""
    # Arrange — no setup needed for pure validation

    # Act & Assert
    with pytest.raises(ValidationError, match="Invalid email"):
        create_user(email="invalid-email")
```

---

## Integration with TDD Cycle

```
Task received from Worktree Controller
  │
  ▼
Load test-case-template.md (this file)
  │
  ├─→ Fill metadata + behavior section
  ├─→ Identify edge cases
  ├─→ Choose language skeleton
  ├─→ Complete Pre-RED checklist
  │
  ▼
Write actual test code → UT-RED
  │
  ├─→ Run test → confirm failure
  ├─→ Complete Post-RED checklist
  │
  ▼
Write minimal production code → UT-GREEN
  │
  ├─→ Run test → confirm pass
  ├─→ Run all tests → confirm no regression
  ├─→ Complete Post-GREEN checklist
  │
  ▼
Refactor if needed → UT-REFACTOR
  │
  ▼
Next behavior (repeat from top)
```

---

## Reference Files

| File | Purpose |
|------|---------|
| `references/ut-red.md` | UT RED phase detailed instructions |
| `references/ut-green.md` | UT GREEN phase detailed instructions |
| `references/ut-refactor.md` | UT REFACTOR phase detailed instructions |
| `references/api-red.md` | API RED phase detailed instructions |
| `references/api-green.md` | API GREEN phase detailed instructions |
| `references/api-refactor.md` | API REFACTOR phase detailed instructions |
| `references/test-verification.md` | Verification checklists and anti-patterns |
| `references/patterns-{language}.md` | Language-specific test patterns (optional, create as needed) |
