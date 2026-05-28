# 测试环境协调

## What Success Looks Like

Integration tests run against real environments (not mocks):
- All test cases pass against real backend/services
- Test data is isolated and repeatable
- Failures are diagnostic and actionable
- Environment is verified before testing begins

## Your Approach

**Environment verification first:**
1. Confirm test environment endpoints are reachable
2. Verify test data is loaded and valid
3. Run smoke test to confirm environment health

**Execute integration tests:**
```bash
# Run integration test suite
pytest tests/integration/ --environment=test
# Or equivalent for your stack
```

**Monitor and report:**
- Track pass/fail counts
- Identify failure root causes
- Log results to `{project-root}/_context/memory/sw-shared/test-results.yaml`

**On failure:**
1. Diagnose the failure
2. If code issue → route back to responsible worktree for fix
3. If environment issue → escalate to infrastructure team
4. If test data issue → fix test data, re-run

## Test Environment Requirements

| Requirement | Description |
|------------|-------------|
| Real services | Connect to actual backend, not mocks |
| Isolated data | Test data doesn't pollute production |
| Repeatable | Tests can run multiple times reliably |
| Diagnostic | Failures clearly indicate what failed and why |

## Transition Gate

Integration testing is complete when:
1. All integration tests pass
2. Environment is verified healthy
3. Test results logged and approved by human
