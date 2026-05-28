# Agent-Executable QA / Acceptance Criteria Specification

## ZERO USER INTERVENTION PRINCIPLE

所有验收标准 (Acceptance Criteria) MUST be executable by agents (测试命令, curl, 脚本, lint 工具, CI checks, static analysis) — 不能要求任何形式的人工手动验证。

**被禁止的验收标准模式**:
- "用户手动测试..." (要求 human action)
- "用户目视确认..." (要求 human visual inspection)
- "在浏览器中检查..." (除非有自动化截图对比工具)
- "确认感觉合理..." (主观，不可自动化)
- "手动验证..." (任何以 "manual" 开头的)

**核心理由**: 规划器 (sw-strategic-planner) 和执行器 (sw-worktree-controller) 需要确认一个任务是否完成。如果验收标准需要人类介入，他们就无法自动验证，从而导致流程卡住或给出不准确的完成信号。

## 各类别验收标准格式

### 1. API 测试 (Test Command / Curl)

**Good Examples** (agent-executable):

```markdown
- [Test Command] 登录端点返回 200 + token:
  curl -s -X POST http://localhost:3000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"testuser","password":"testpass"}' \
    | jq -e '.token' > /dev/null

- [Test Command] Rate limiting 返回 429 after exceeding limit:
  for i in $(seq 1 101); do
    curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/auth/login -X POST -d '...'
  done | tail -1 | grep 429

- [Test Command] 运行 API 测试套件:
  pytest tests/api/ -v --tb=short
  预期: 0 failed, 0 errors
```

**Bad Examples** (需要人工):

```markdown
- 用户在 Postman 中测试登录端点              ← 人工操作
- 确认返回的 token 格式正确                   ← 可写自动化验证但未写
- 在浏览器中检查登录后跳转                     ← 人工操作
```

### 2. UI 验证 (Automated Screenshot / DOM Assertion)

**Good Examples** (agent-executable):

```markdown
- [Screenshot] 登录页面渲染对比:
  使用 headless 浏览器截取 /login 页面
  与 baseline screenshot 对比，差异率 < 0.5%

- [DOM Assertion] 登录表单元素存在:
  ``js
  document.querySelector('input[name="username"]') !== null
  document.querySelector('input[name="password"]') !== null
  document.querySelector('button[type="submit"]') !== null
  ``

- [DOM Assertion] Error message displayed on invalid login:
  ``js
  // After submitting invalid credentials
  document.querySelector('.error-message')?.textContent?.length > 0
  ``
```

**Bad Examples** (需要人工):

```markdown
- 用户目视确认登录按钮在正确位置              ← 视觉判断
- 确认页面看起来不错                           ← 主观
- 手动测试表单验证提示                         ← 人工操作
```

### 3. 性能验证 (Benchmark Script)

**Good Examples** (agent-executable):

```markdown
- [Benchmark] API response time:
  ``bash
  ab -n 1000 -c 10 http://localhost:3000/api/users | grep "Requests per second"
  预期: > 100 req/s
  ``

- [Benchmark] Query performance:
  ``bash
  time psql -c "SELECT * FROM users WHERE email = 'test@test.com'"
  预期: < 50ms
  ``

- [Benchmark] Bundle size:
  ``bash
  du -sh dist/main.js
  预期: < 500KB (gzipped)
  ``
```

**Bad Examples** (需要人工):

```markdown
- 用户体验流畅，无明显延迟                   ← 主观
- 页面加载速度快                               ← 主观
```

### 4. 安全检查 (Automated Tool)

**Good Examples** (agent-executable):

```markdown
- [Security Scan] 依赖漏洞扫描:
  ``bash
  npm audit --audit-level=high
  预期: 0 high/critical vulnerabilities
  ``

- [Security Check] SQL injection check:
  ``bash
  curl -s "http://localhost:3000/api/users?id=1' OR '1'='1" | grep -c "error"
  预期: 不返回数据 (参数化查询生效)
  ``

- [Security Check] No secrets committed:
  ``bash
  git diff --cached | grep -iE "(password|secret|api_key|token)" | grep -v "import\|test\|mock\|example"
  预期: 0 matches
  ``
```

**Bad Examples** (需要人工):

```markdown
- 安全团队审查代码                            ← 人工
- 手动进行渗透测试                             ← 人工
```

### 5. 集成测试 (Integration Test Suite)

**Good Examples** (agent-executable):

```markdown
- [Test Command] Integration test suite:
  ``bash
  pytest tests/integration/ -v --tb=short
  预期: All tests pass
  ``

- [Test Command] Contract tests:
  ``bash
  npm run test:contract
  预期: 所有消费者契约测试通过
  ``

- [Test Command] End-to-end workflow:
  ``bash
  bash scripts/e2e-test.sh
  预期: Exit code 0
  ``
```

**Bad Examples** (需要人工):

```markdown
- 手动执行集成测试流程                        ← 人工操作
- 与其他团队联调确认                           ← 依赖外部人工
```

### 6. 代码质量 (Lint / Static Analysis)

**Good Examples** (agent-executable):

```markdown
- [Lint] No new lint errors:
  ``bash
  eslint src/ --max-warnings=0
  预期: 0 errors, 0 warnings
  ``

- [Static Analysis] Type check:
  ``bash
  tsc --noEmit
  预期: 0 errors
  ``

- [Complexity] Function complexity:
  ``bash
  radon cc src/ -a | awk '$2 > 10 {print; exit 1}'
  预期: No function with cyclomatic complexity > 10
  ``
```

### 7. 文档 (Automated Check)

**Good Examples** (agent-executable):

```markdown
- [Doc Check] README includes run command:
  ``bash
  grep -c "npm run dev\|yarn dev\|pnpm dev" README.md
  预期: >= 1
  ``

- [Doc Check] API docs generated:
  ``bash
  ls docs/api/index.html
  预期: file exists
  ``
```

**Bad Examples** (需要人工):

```markdown
- 用户阅读文档确认内容正确                     ← 人工
- 文档是否清晰易读                             ← 主观
```

## 验收标准格式规范

### 基本格式

每个验收标准遵循:

```
[N].[Verification Method] [Description]:
  [Command / Check / Script]
  预期: [Expected Result]
```

### Verification Method 标签

| 标签 | 适用场景 | 示例工具 |
|------|---------|---------|
| `[Test Command]` | 运行测试套件 | pytest, jest, go test, cargo test |
| `[Curl]` | HTTP API 验证 | curl, httpie |
| `[Script]` | 自定义验证脚本 | bash, python scripts |
| `[Lint Rule]` | 代码规范检查 | eslint, pylint, shellcheck |
| `[CI Check]` | CI 集成验证 | GitHub Actions, GitLab CI |
| `[Static Analysis]` | 静态分析 | mypy, tsc, rust-analyzer |
| `[Check]` | 文件/内容存在性检查 | grep, ls, git diff |
| `[Benchmark]` | 性能指标验证 | ab, wrk, time |
| `[Security Scan]` | 安全扫描/检查 | npm audit, trivy, bandit |
| `[Screenshot]` | 自动化截图对比 | headless browser screenshot |
| `[DOM Assertion]` | 浏览器 DOM 验证 | document.querySelector |

### 验证标准的三层置信度

| 级别 | 含义 | 示例 |
|------|------|------|
| **Must Verify** | 必须严格满足 | "All tests pass" — 0 failures |
| **Should Verify** | 应满足但允许已知例外 | "Bundle size < 500KB (known exception: vendor chunk)" |
| **Informational** | 收集信息但不作通过/失败判断 | "Record and report the first-load JS parse time" |

## 从人工标准转换为自动化标准

### 转换规则

| 人工标准模式 | 自动化标准转换 |
|-------------|---------------|
| "用户手动测试 X" | 编写自动化测试脚本模拟 X 场景 |
| "用户目视确认 Y" | Screenshot 对比 或 DOM 断言 |
| "检查 Z 是否正确" | 具体的 assert/grep/diff 命令 |
| "确认性能可接受" | 具体的性能指标 + benchmark 命令 |
| "手动审查代码" | Lint 规则 + static analysis |

### 转换示例

**原始 (Bad)**:
```
- 用户手动测试各种登录失败场景
- 确认错误消息正确显示
- UI 在移动端看起来正常
```

**转换后 (Good)**:
```
1. [Test Command] 登录失败场景测试:
   pytest tests/test_login_failures.py -v
   预期: 所有 test_invalid_password, test_nonexistent_user, test_locked_account 通过

2. [DOM Assertion] 错误消息验证:
   // After submitting bad credentials on /login
   document.querySelector('.error-message').textContent === 'Invalid username or password'

3. [Screenshot] 移动端截图验证:
   使用 headless browser, viewport=375x812 (iPhone X), 截取登录页面
   与 baseline_screenshots/login_mobile.png 对比, 差异率 < 2%
```

## 特殊情况处理

### 视觉/设计相关验收

如果任务涉及 UI 变更，使用自动化截图对比而非人工目视:

```markdown
- [Screenshot] 设计一致性验证:
  ``bash
  # Capture screenshots of all affected pages
  bash scripts/capture-screenshots.sh pages.txt
  # Compare against approved baselines
  bash scripts/compare-screenshots.sh --threshold=0.02
  ``
  预期: 差异率 < 2%
```

### 无法自动化的验收

如果确实存在无法自动化的验收需求，将其标记为 `[Human Check]` 并作为**非阻塞性**的:

```markdown
- [Human Check] (非阻塞性) 用户体验审核:
  建议: 邀请 2-3 名团队成员体验新功能并收集反馈
  NOTE: 此验收标准不阻塞自动化流程
```

但尽量减少这种情况。如果发现大量无法自动化的标准，重新审视任务拆分是否合理。
