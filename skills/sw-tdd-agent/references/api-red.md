# API-RED: 编写失败的API测试

## Prerequisites

Layer 1 (UT) must be complete and passing before starting API-RED.

## What Success Looks Like

A failing API test that describes the contract between modules. The test fails because the API isn't implemented yet.

## Your Approach

### Identify API Contracts

What are the boundaries between modules?
- Request/response formats
- Error handling at boundaries
- Data transformation
- Authentication/authorization

### Write API Test

```python
def test_api_user_create_returns_201():
    response = api_client.post("/users", {
        "email": "test@example.com"
    })
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"
```

### Test Scope

- API surface, not implementation
- Integration points
- Error responses
- Edge cases at boundaries

### Run to Confirm Failure

MANDATORY — Confirm test fails because API not implemented.

## Verification

Before leaving RED:
- [ ] API test fails
- [ ] Fails for expected reason (not implemented)

## Layer 1 vs Layer 2

| Layer | Tests | Scope |
|-------|-------|-------|
| Layer 1 (UT) | Unit tests | Single function/class |
| Layer 2 (API) | API tests | Module boundaries |

## Next

After RED → API-GREEN: Implement minimal API
