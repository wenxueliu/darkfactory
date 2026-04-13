# API-REFACTOR: API层重构

## Prerequisites

API-GREEN must be complete with passing tests.

## What Success Looks Like

Clean API surface, documented contracts, all tests green.

## Your Approach

### Clean Up API Surface

- Improve endpoint names
- Clean up request/response formats
- Improve error messages
- Add API documentation

### Document Contracts

- What does this endpoint do?
- What are the request/response formats?
- What are the error codes?

### Don't Break Contracts

If the API is being used:
- Don't change signatures
- Don't change behavior
- Add new endpoints for new behavior

## Run Tests

All tests must pass after refactor.

## Verification

Before leaving API cycle:
- [ ] API surface is clean
- [ ] Contracts documented
- [ ] All tests pass
- [ ] Ready for code review

## TDD Cycle Complete

Both layers done:
- Layer 1: UT all passing
- Layer 2: API tests all passing

Report to Worktree Controller: TDD cycle complete
