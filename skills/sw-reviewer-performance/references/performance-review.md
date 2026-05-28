# PerformanceReview: 性能审核

## What Success Looks Like

Performance issues are identified with bottleneck location, impact analysis, and optimization recommendations.

## Your Approach

### Review Scope

Read the code in the worktree. Focus on:
- Database queries
- Loops and iterations
- Memory allocation
- Concurrency patterns
- Caching opportunities

### Performance Patterns to Find

| Pattern | Impact |
|---------|--------|
| N+1 queries | Database round trips |
| O(n²) algorithm | CPU at scale |
| Loading all data | Memory exhaustion |
| No caching | Repeated expensive ops |
| Blocking I/O | Latency |
| Connection leak | Resource exhaustion |

### Finding Format

```markdown
## Performance Issues: {Task ID}

| Severity | Issue | Location | Impact | Recommendation |
|----------|-------|----------|--------|----------------|
| P1 | N+1 query | src/orders.py:35 | 100 queries for 100 orders | Use JOIN or eager loading |

### Issue Details

**P1: N+1 Query**
- **Location:** src/orders.py:35
- **Code:**
  ```python
  for order in orders:
      customer = db.get(order.customer_id)  # Query per order
  ```
- **Impact:** N+1 queries — 100 orders = 101 queries
- **Fix:**
  ```python
  customer_ids = [o.customer_id for o in orders]
  customers = db.get_many(customer_ids)  # Single query
  ```
```

## Verification

Before submitting review:
- [ ] Each issue has file:line location
- [ ] Each issue has quantified impact
- [ ] Each issue has severity rating
- [ ] Each P0/P1/P2 has optimization recommendation

## Output

Write to `{project-root}/_context/memory/sw-shared/reviews/{task_id}-performance.md`
