# Verification Protocol: 4-Phase 验证协议

## 核心原则

**你是 QA 关卡。子 Agent 会说谎。自动化检查不够。必须亲自验证。**

在每次委托完成后，必须按顺序完成全部 4 个 Phase 的验证。不跳步，不减配。

**如果不能解释每一行改动的代码做了什么，就没有真正完成审查。**

## 4-Phase 验证流程

```
Phase A: Automated Verification (自动化验证)
  → lsp_diagnostics → build → test → lint
Phase B: Manual Code Review (人工代码审查)
  → Read EVERY changed file → line-by-line review → cross-reference claims
Phase C: Hands-On QA (手工质量验证)
  → Run the actual thing → curl / browser / CLI
Phase D: Plan File Check (计划文件检查)
  → Read plan → confirm checkbox → count remaining
```

## Phase A: Automated Verification (自动化验证)

### 目标

确认代码在自动化层面没有明显问题：无诊断错误、编译通过、测试全部通过、lint 无警告。

### 执行步骤

**步骤 A1: 运行 LSP 诊断**

```bash
# 检查所有修改文件目录的诊断信息
lsp_diagnostics 工具，针对修改的文件目录
```

检查标准:
- ZERO errors (0 个诊断错误)
- 如果项目配置了 strict 模式，warnings 也应该为零
- 注意: 目录扫描有文件数上限 (通常 50 个文件)，不代表全项目保证

**步骤 A2: 构建/编译**

根据项目类型选择构建命令:

| 语言 | 命令 | 期望 |
|------|------|------|
| Go | `go build ./...` | exit code 0 |
| Python | `python -m compileall .` | 无错误输出 |
| TypeScript | `npm run build` 或 `tsc --noEmit` | exit code 0 |
| Rust | `cargo build` | exit code 0 |
| Java | `./gradlew build` 或 `mvn compile` | exit code 0 |

检查标准:
- exit code 必须为 0
- 无编译错误或类型错误输出

**步骤 A3: 运行测试**

```bash
# 运行项目测试套件
# Go:      go test ./... -v
# Python:  python -m pytest -v
# Node:    npm test
# Rust:    cargo test
```

检查标准:
- ALL tests pass (0 failures, 0 errors)
- 确认测试有意义的断言 (不是空测试或 always-pass)
- 如果只有部分测试与修改相关，至少运行相关测试

**步骤 A4: 运行 Linter**

```bash
# Go:      golangci-lint run ./...
# Python:  ruff check . 或 pylint
# Node:    npm run lint
```

检查标准:
- 零新增 lint 警告（如果全项目已有历史警告，只关注新增的）

### Phase A 判定

```
[ ] A1: LSP diagnostics -- ZERO errors in modified directories
[ ] A2: Build -- exit code 0, no compile errors
[ ] A3: Tests -- ALL tests pass, assertions are meaningful
[ ] A4: Linter -- ZERO new warnings
```

如果有任何一项未通过 → Phase A FAIL → 不复用子 agent，直接执行 Phase C 和 Phase D → 记录失败原因 → 委托修复。

## Phase B: Manual Code Review (人工代码审查) -- 不可协商

### 目标

用人类的眼睛逐行检查所有修改。自动化工具能发现语法错误，但不能发现逻辑错误、stub 代码、或范围蔓延。

### 执行步骤

**步骤 B1: 列出所有修改的文件**

从委托结果或 git diff 中获取修改/创建的文件列表。

**步骤 B2: 逐文件、逐行审查**

对每个修改/创建的文件，使用 Read 工具完整读取并进行以下检查：

#### 正确性检查 (Correctness)
- [ ] 逻辑是否正确实现了任务需求？
- [ ] 是否有 stub、TODO、placeholder 或硬编码值？
- [ ] 是否有逻辑错误或遗漏的边界情况？
- [ ] 错误处理是否完整？（空输入、异常、超时、并发）

#### 模式合规检查 (Pattern Compliance)
- [ ] 是否遵循项目已有的代码模式？
- [ ] 导入是否完整且正确？（检查每个 import）
- [ ] 命名是否与项目约定一致？
- [ ] 是否使用了项目已有的工具函数和组件？

#### 质量检查 (Quality)
- [ ] 是否有重复代码可以提取？
- [ ] 函数是否过长或过于复杂？
- [ ] 是否有不必要的副作用或全局状态？

#### 测试检查 (Test Quality)
- [ ] 测试是否覆盖了主要路径和边界情况？
- [ ] 测试断言是否具体而不空洞？（没有 `assert true == true`）
- [ ] 测试是否独立（不依赖其他测试的执行顺序）？

**步骤 B3: 交叉验证子 Agent 声明**

对比子 Agent 报告的"已完成"与代码实际内容：

- 子 agent 声称创建了 `src/api/auth/register.go` → Read 确认文件存在且内容完整
- 子 agent 声称 "所有测试通过" → 检查测试输出，确认不是 "0 tests"
- 子 agent 声称 "实现了 X 功能" → 在代码中找到 X 功能的实现

**如果发现子 agent 的声明与实际代码不符 → 立即在同一 session 中修复。**

### Phase B 判定

```
[ ] B1: Listed all modified files
[ ] B2: Reviewed every file line-by-line
  [ ] B2a: Correctness -- logic, errors, edge cases
  [ ] B2b: Pattern compliance -- conventions, imports, naming
  [ ] B2c: Quality -- duplication, complexity, side effects
  [ ] B2d: Tests -- coverage, assertions, independence
[ ] B3: Cross-referenced subagent claims vs actual code
```

全部通过 → Phase B PASS。任何不通过 → Phase B FAIL → 记录具体问题 → 委托修复。

## Phase C: Hands-On QA (手工质量验证)

### 目标

在实际运行环境中验证修改。静态检查看不到视觉 bug 和交互流程问题。

### 按任务类型选择 QA 方法

#### CLI 命令 / 脚本

```bash
# 直接运行修改的命令/脚本
# 示例: 验证新增的 CLI flag
./bin/myapp --new-flag value
# 检查输出、exit code、行为正确性
```

验证点:
- 命令能正常启动和执行
- 输出格式符合预期
- exit code 正确
- 错误信息清晰（测试错误路径）

#### HTTP API / Backend

```bash
# 使用 curl 或类似工具发送实际请求
# 示例: 验证注册 API
curl -s -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@qa-test.com","password":"Test1234!"}' | jq .
```

验证点:
- 响应 status code 正确
- 响应 body 结构符合 API 契约
- 响应头正确 (Content-Type, CORS headers 等)
- 错误响应也正确 (测试边界输入)

#### 浏览器 / 前端 UI

```bash
# 使用浏览工具验证页面/UI 修改
# 访问修改的页面
browse http://localhost:3000/register
```

验证点:
- 页面正常渲染不崩溃
- 交互流程可用（填写表单、点击按钮）
- 视觉无严重问题
- 错误状态显示正确

#### 库函数 / 模块

如果任务不是直接可运行的终端产品（如新增一个工具函数），执行相关的代码路径：

```bash
# Python 示例: 交互式导入并调用
python -c "
from src.utils.validator import validate_password
print(validate_password('weak'))       # 期望 False
print(validate_password('Str0ng!Pass')) # 期望 True
"
```

### Phase C 判定

```
[ ] C1: Identified correct QA method for task type
[ ] C2: Ran the actual tool/command/browser test
[ ] C3: Verified behavior matches expected outcome
```

## Phase D: Plan File Check (计划文件状态检查)

### 目标

确认计划文件正确反映了任务完成状态。

### 执行步骤

**步骤 D1: 重新读取计划文件**

```bash
Read {project-root}/_context/memory/sw-shared/plans/{plan-name}.md
```

**步骤 D2: 确认复选框更新**

- 当前完成的任务复选框已从 `- [ ]` 变为 `- [x]`
- 剩余未完成的顶层任务复选框数量正确

**步骤 D3: 统计剩余任务**

```
统计:
- 顶层任务总数: N
- 已完成: M (复选框 [x])
- 未完成: N-M (复选框空格)
- 已放弃/BLOCKED: K
```

### Phase D 判定

```
[ ] D1: Re-read the plan file
[ ] D2: Confirmed checkbox for completed task is [x]
[ ] D3: Remaining task count is accurate
```

## 验证失败处理

### Phase A 失败

最常见也最容易修复。获取实际错误输出，使用相同 session (task_id) 委托修复:
```
"Verification Phase A failed: [具体错误]. Fix this specific issue."
```

### Phase B 失败

发现代码质量问题。根据严重程度决定:

| 严重程度 | 处理 |
|---------|------|
| 严重逻辑错误或 stub 代码 | 委托修复 (相同 session) |
| 模式不匹配或命名问题 | 委托修复 (相同 session) |
| 测试覆盖不足 | 委托补充测试 |
| 代码重复但功能正确 | 记录到 issues.md，不阻塞 |

### Phase C 失败

运行时行为不符合预期。委托修复:
```
"QA check failed: curl POST /api/auth/register with valid data returned 500 instead of 201. Error: [具体错误]. Fix."
```

### Phase D 失败

计划文件状态不匹配。更新复选框后继续。

## 最小化验证 (仅用于非关键/探索性任务)

对于非关键任务（如添加注释、格式化代码），可在 Phases A+C 通过后跳过 Phase B 的逐行审查。但必须至少执行 Phase A + Phase C + Phase D。
