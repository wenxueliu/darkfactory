# TDD-API循环

## What Success Looks Like

API contract tests fail initially (RED), then pass after API implementation (GREEN), then code is refactored while keeping tests green (REFACTOR).

**Prerequisite:** UT layer must be complete and passing before starting API test cycle.

## Your Approach

### RED Phase: Write Failing API Test

1. **Identify API contracts** — Interfaces between modules/components
2. **Write API test** — Test the contract, not the implementation
3. **Run to confirm failure** — API not yet implemented

**API test scope:**
- Request/response contracts
- Error handling at boundaries
- Data transformation at interfaces
- Authentication/authorization at API level

### GREEN Phase: Implement API

1. **Implement the minimal API** to satisfy the contract
2. **Wire in existing UT-passed code** — Don't reimplement what UT covered
3. **Run API tests** — Confirm all pass

### REFACTOR Phase

1. **Clean up API surface** — Names, parameter order
2. **Improve error messages**
3. **Document API contracts** if not already done

## Two-Layer Integration

```
Layer 1 (UT):     Tests individual functions/methods
Layer 2 (API):     Tests module/component interfaces

Layer 2 uses outputs from Layer 1, doesn't replace it.
```

## Verification Checklist

Before marking API layer complete:

- [ ] All API contracts have tests
- [ ] Each API test failed before implementation
- [ ] All API tests pass
- [ ] API contracts are documented
- [ ] No regression in UT

## Transition

API test cycle is complete when:
1. All API contracts have passing tests
2. API documentation is updated
3. Ready to proceed to code review
