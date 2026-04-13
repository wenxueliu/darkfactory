# LogicReview: 逻辑审核

## What Success Looks Like

Logic bugs are identified with specific examples, severity ratings, and clear explanations of what's wrong.

## Your Approach

### Review Scope

Read the code in the worktree. Focus on:
- Business logic
- Conditional branches
- Error handling
- State transitions
- Edge cases

### Logic Patterns to Find

| Pattern | Risk |
|---------|------|
| Missing null check | NPE / type error |
| Off-by-one | Logic error at boundaries |
| Wrong operator | < instead of <= |
| Unhandled case | Switch without default |
| Swallowed exception | Silent failure |
| State race | Concurrent modification |

### Finding Format

```markdown
## Logic Issues: {Task ID}

| Severity | Issue | Location | Example | Recommendation |
|----------|-------|----------|---------|----------------|
| P1 | Missing null check | src/user.py:23 | `user.name` without null check | Add `if user is None` check |

### Issue Details

**P1: Missing Null Check**
- **Location:** src/user.py:23
- **Code:**
  ```python
  email = user.email  # user could be None here
  ```
- **Problem:** If `user` is None, this raises AttributeError
- **Fix:**
  ```python
  if user is None:
      raise UserNotFoundError()
  email = user.email
  ```
```

## Verification

Before submitting review:
- [ ] Each issue has file:line location
- [ ] Each issue has concrete example
- [ ] Each issue has severity rating
- [ ] Each P0/P1/P2 has fix recommendation

## Output

Write to `{project-root}/_bmad/memory/hw-shared/reviews/{task_id}-logic.md`
