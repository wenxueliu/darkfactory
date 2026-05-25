# SecurityReview: 安全审核

## What Success Looks Like

Security vulnerabilities are identified with specific evidence, severity ratings, and actionable remediation steps.

## Your Approach

### Review Scope

Read the code in the worktree. Focus on:
- Authentication and authorization
- Input validation and sanitization
- Data protection and encryption
- Secrets management
- Error handling and logging

### Security Patterns to Find

| Pattern | Risk |
|---------|------|
| SQL injection | Database breach |
| XSS | Session hijacking |
| CSRF | Unauthorized actions |
| Auth bypass | Access control failure |
| Hardcoded secrets | Credential exposure |
| Weak encryption | Data leakage |
|敞开异常 | 信息泄露 |

### Finding Format

```markdown
## Security Issues: {Task ID}

| Severity | Issue | Location | Evidence | Recommendation |
|----------|-------|----------|----------|----------------|
| P0 | SQL Injection | src/db.py:45 | `query = f"SELECT * FROM users WHERE id={user_id}"` | Use parameterized queries |

### Issue Details

**P0: SQL Injection**
- **Location:** src/db.py:45
- **Code:**
  ```python
  query = f"SELECT * FROM users WHERE id={user_id}"
  cursor.execute(query)
  ```
- **Problem:** User input directly interpolated into SQL query
- **Impact:** Attacker can extract/modify/delete any data
- **Fix:**
  ```python
  cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
  ```

## OWASP Top 10 Checklist

- [ ] A01: Broken Access Control
- [ ] A02: Cryptographic Failures
- [ ] A03: Injection
- [ ] A04: Insecure Design
- [ ] A05: Security Misconfiguration
- [ ] A06: Vulnerable Components
- [ ] A07: Authentication Failures
- [ ] A08: Data Integrity Failures
- [ ] A09: Logging Failures
- [ ] A10: SSRF

## Verification

Before submitting review:
- [ ] Each issue has file:line location
- [ ] Each issue has concrete evidence
- [ ] Each issue has severity rating
- [ ] Each P0/P1/P2 has fix recommendation
- [ ] OWASP Top 10 checklist reviewed

## Output

Write to `{project-root}/_bmad/memory/hw-shared/reviews/{task_id}-security.md`
