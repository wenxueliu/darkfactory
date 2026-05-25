# API-GREEN: API实现通过测试

## Prerequisites

API-RED must be complete with failing test.

## What Success Looks Like

The minimal API implementation that satisfies the contract. Reuses Layer 1 code where possible.

## Your Approach

### Wire In Existing Code

Don't reimplement what UT already covers:
```python
# Use code from Layer 1 UT-passed implementation
@router.post("/users")
def create_user(request: UserRequest):
    user = create_user(email=request.email)  # From Layer 1
    return UserResponse(id=user.id, email=user.email)
```

### Write Minimal API

- Implement the endpoint
- Wire in existing business logic
- Handle request/response format

### Don't Duplicate

- If Layer 1 code handles logic, call it
- Don't copy-paste business rules into API layer

## Run Tests

- API test should pass
- Layer 1 UT should still pass (no regression)

## Verification

Before leaving GREEN:
- [ ] API test passes
- [ ] Layer 1 UT still passes
- [ ] API contract documented

## Next

After GREEN → API-REFACTOR: Clean up API surface
