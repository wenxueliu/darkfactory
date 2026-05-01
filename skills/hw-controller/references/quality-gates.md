# 质量门禁验证 (Quality Gates)

## 核心理念

质量门禁是不可妥协的自动化检查点。每个任务必须通过三层门禁才能标记 DONE:
1. **TDD 门禁** — UT + API 测试 PASS
2. **审查门禁** — 安全/逻辑/性能审查通过
3. **回归门禁** — 不破坏其他 worktree 的测试

门禁是串行的——UT PASS 后才有意义跑 API，API PASS 后才有意义请审查。跳过门禁的唯一途径是人工显式批准。

## 门禁执行顺序 (Per Task)

```
Worktree Controller 执行:

  ┌──────────┐
  │ 接收任务  │
  └────┬─────┘
       │
  ┌────▼──────────────────────────────────────────┐
  │ GATE 1: TDD 循环                               │
  │ ┌──────────────────────────────────────────┐   │
  │ │ 对每个 UT 用例:                           │   │
  │ │   RED   → 写 UT, 运行, 确认 FAIL          │   │
  │ │   GREEN → 写最少代码, 运行, 确认 PASS      │   │
  │ │   REFACTOR → 重构, 运行, 确认仍 PASS       │   │
  │ │                                          │   │
  │ │ 所有 UT PASS → 进入 API 验证              │   │
  │ │ newman run api-{id}.json → 所有 API PASS │   │
  │ └──────────────────────────────────────────┘   │
  │ PASS: 所有 UT + API PASS → 进入审查          │
  │ FAIL: 回到 TDD, 最多 {min_iteration} 轮      │
  └────┬──────────────────────────────────────────┘
       │
  ┌────▼──────────────────────────────────────────┐
  │ GATE 2: 异质审查                               │
  │ ┌────────────┐ ┌──────────┐ ┌──────────────┐  │
  │ │  安全审查   │ │ 逻辑审查  │ │  性能审查     │  │
  │ └─────┬──────┘ └────┬─────┘ └──────┬───────┘  │
  │       └──────────────┼─────────────┘          │
  │               ┌──────▼──────┐                  │
  │               │  问题汇总    │                  │
  │               └──────┬──────┘                  │
  │                      │                         │
  │   PASS: 0 P0, 0 P1, 0 P2 → DONE               │
  │   FAIL: 有 P0/P1/P2 → 修复后重审               │
  └────┬──────────────────────────────────────────┘
       │
  ┌────▼──────────────────────────────────────────┐
  │ GATE 3: 回归检查                               │
  │ ┌──────────────────────────────────────────┐   │
  │ │ 从 worktree 内部:                         │   │
  │ │ 1. git merge {base_branch} (获取最新代码)  │   │
  │ │ 2. 运行本 worktree 全量 UT + API          │   │
  │ │ 3. 检查 PASS 率是否下降                   │   │
  │ │                                          │   │
  │ │ 跨 worktree (总控执行):                    │   │
  │ │ 1. 所有 worktree DONE 后                  │   │
  │ │ 2. 合并到 staging 分支                    │   │
  │ │ 3. 运行全量 UT + API + E2E                │   │
  │ │ 4. 通过 → 合并到主分支                    │   │
  │ └──────────────────────────────────────────┘   │
  │ PASS: 无回归 → 合并就绪                        │
  │ FAIL: 定位破坏者 → 修复或回滚                   │
  └────────────────────────────────────────────────┘
```

## GATE 1: TDD 门禁 (三层反馈验证)

### 1A. UT 层验证

TDD Agent 按设计文档 Section 10.3 的 UT 用例执行 RED → GREEN → REFACTOR:

**验证规则:**

| 检查项 | 阈值 | 失败动作 |
|--------|------|---------|
| UT PASS 率 | 100% | 回到 TDD 循环 |
| UT 覆盖率 (新增代码) | ≥ 90% 业务逻辑, ≥ 80% 工具类 | 补充测试 |
| 每个 public 方法 | ≥ 2 个 UT (1 happy + 1 error/boundary) | 补充用例 |
| 每个组件 | ≥ 1 个 edge 用例 | 补充用例 |
| 测试数据 | 所有输入/输出为具体值, 无占位符 | 修正数据 |

**TDD 循环限制:**
- 单个 UT 用例最多 `min_iteration_before_human` 轮 RED→GREEN→REFACTOR（默认 3 轮）
- 如果 3 轮后 UT 仍未 PASS → 暂停，报告给 Worktree Controller
- Worktree Controller 分析: 测试写错了？设计有问题？环境不对？
- 再试 2 轮 → 仍未 PASS → 升级人工

**UT 执行报告:**

```yaml
# worktree-registry.yaml — test_status.ut
ut_results:
  total: {n}
  passed: {n}
  failed: {n}
  skipped: {n}
  coverage_pct: {n}
  iterations_used: {n}
  max_iterations: {min_iteration_before_human}
```

### 1B. API 层验证

UT 全部 PASS 后，验证 API 层。使用 Newman 执行 Postman Collection:

```bash
newman run _bmad/memory/hw-shared/tests/api-{requirement_id}.json \
  -e _bmad/memory/hw-shared/tests/api-{requirement_id}-env.json \
  --reporters cli,junit \
  --reporter-junit-export _bmad/memory/hw-shared/tests/api-{requirement_id}-report.xml
```

**验证规则:**

| 检查项 | 阈值 | 失败动作 |
|--------|------|---------|
| API 用例 PASS 率 | 100% | 修复 API 实现或修正测试 |
| 状态码正确性 | 所有断言 PASS | 检查 API 实现 |
| 响应体结构 | 所有断言 PASS | 检查序列化/反序列化 |
| 副作用验证 | 所有 `pm.sendRequest` 断言 PASS | 检查持久化逻辑 |
| 响应时间 | ≤ SLA 阈值 (默认 200ms p95) | 性能审查标记 |

**Newman 退出码处理:**

| 退出码 | 含义 | 响应 |
|--------|------|------|
| 0 | 全部 PASS | ✅ 进入审查门禁 |
| 1 | 有 FAIL | ❌ 修复后重跑 |
| 2 | 脚本错误 | ❌ 检查 Postman test script 语法 |
| 3 | 网络错误 | ⚠️ 重试 2 次 → 仍失败 → blocked |

### 1C. E2E 层验证 (合并后)

E2E 测试在所有 worktree 合并后执行（见 GATE 3 跨任务回归）。不在单个 worktree 内执行 E2E——E2E 需要完整系统。

## GATE 2: 审查门禁 (Heterogeneous Review)

UT + API PASS 后，触发三个审查者并行审查代码。

### 审查触发条件

| 审查者 | 默认启用? | 何时跳过 |
|--------|----------|---------|
| Security | `enabled_reviewers` 含 security | 纯文档/配置变更 |
| Logic | `enabled_reviewers` 含 logic | 仅修改注释/格式 |
| Performance | `enabled_reviewers` 含 performance | 纯工具类/脚本 |

### 问题严重度定义

| 级别 | 定义 | 示例 | 阻塞 |
|------|------|------|------|
| **P0** | 致命 — 系统不可用、数据丢失、安全漏洞 | SQL 注入、未加密的支付数据、可导致服务的 NPE | 阻塞所有阶段 |
| **P1** | 严重 — 功能缺陷、性能严重下降、不安全的默认配置 | 缺少认证检查、N+1 查询、错误处理吞掉异常 | 阻塞下一阶段 |
| **P2** | 一般 — 代码质量问题、轻微性能问题、可维护性 | 未使用的 import、方法过长、缺少日志 | 阻塞下一阶段 |
| **P3** | 建议 — 锦上添花 | 变量命名建议、可选的性能优化 | 不阻塞 |

### 审查流程

```
1. Worktree Controller 标记 status: "reviewing"
2. 总控触发三个审查者 (并行):
   - Security Reviewer 审查 diff → 输出 review-security-{task_id}.md
   - Logic Reviewer 审查 diff → 输出 review-logic-{task_id}.md
   - Performance Reviewer 审查 diff → 输出 review-performance-{task_id}.md
3. Worktree Controller 读取审查报告 → 汇总问题清单
4. 修复 P0/P1/P2 问题 → 重新审查（仅重新审查修复的维度）
5. 全部通过 → 标记 DONE
```

**审查结果汇总:**

```yaml
# worktree-registry.yaml — review_status
review_status:
  security:
    result: "PASS|FAIL"
    p0_count: {n}
    p1_count: {n}
    p2_count: {n}
    p3_count: {n}
    report_path: "reviews/{task_id}-review-security.md"
  logic:
    result: "PASS|FAIL"
    ...
  performance:
    result: "PASS|FAIL"
    ...
```

### 自动修复 vs 人工介入

| 严重度 | 自动修复? | 最大自动尝试次数 |
|--------|----------|----------------|
| P0 | 是（如果是明确的代码问题） | 3 次 |
| P1 | 是 | 3 次 |
| P2 | 是 | 2 次 |
| P3 | 否（仅在重构阶段顺便处理） | — |

超过自动修复次数 → 升级人工。

## GATE 3: 回归门禁 (Regression Check)

### 3A. 任务内回归 (Worktree 内部)

在每个 worktree 标记 DONE 之前:

```bash
# 1. 拉取主分支最新代码
git fetch origin {base_branch}
git merge origin/{base_branch} --no-ff -m "merge: sync with {base_branch}"

# 2. 解决冲突 (如有)

# 3. 重跑本 worktree 的全量 UT
mvn test -pl {module}

# 4. 如果 PASS → 标记 DONE
# 5. 如果 FAIL → 分析失败原因
#    - 是否是 merge 冲突导致的？→ 修复
#    - 是否是其他 worktree 破坏了共享接口？→ 报告总控
```

### 3B. 跨任务回归 (合并后)

所有 worktree DONE 后，合并到 staging 分支并运行全量回归:

```bash
# 1. 创建 staging 分支
git checkout -b staging-{requirement_id} {base_branch}

# 2. 按 wave 顺序合并所有 worktree
git merge hw-task-001 --no-ff
git merge hw-task-002 --no-ff
...

# 3. 全量 UT + API 测试
mvn test
newman run api-{requirement_id}.json -e api-{requirement_id}-env.json

# 4. E2E 测试 (如有)
npx playwright test e2e-{requirement_id}.spec.ts

# 5. 全部 PASS → 合并到主分支
# 6. 有 FAIL → 定位问题 worktree → 修复或回滚
```

**回归定位流程:**

```
如果全量测试失败:
  1. git bisect 定位引入失败的 merge
  2. 或者: 逐个回滚 worktree merge (从最后一个开始)
  3. 找到破坏者 → 标记该 worktree 为 blocked
  4. 重新运行该 worktree 的 TDD 循环
  5. 修复后重新 merge
```

## 门禁配置对照表

| business_domain | 审查者 | UT 覆盖率 | P0 定义 | 自动修复次数 |
|-----------------|--------|----------|--------|------------|
| `fintech` | security + logic + performance | ≥ 90% | 资金安全 + 合规违规 | 3 |
| `ecommerce` | security + logic + performance | ≥ 85% | 支付失败 + 数据丢失 | 3 |
| `general` | security + logic + performance | ≥ 80% | 功能不可用 | 2 |
| `internal-tools` | logic | ≥ 70% | 生产数据破坏 | 1 |

## 门禁输出

| 产物 | 路径 | 内容 |
|------|------|------|
| UT 执行报告 | `worktree-registry.yaml` → `test_status.ut` | PASS/FAIL + 覆盖率 |
| API 测试报告 | `tests/api-{id}-report.xml` | Newman JUnit 报告 |
| 安全审查报告 | `reviews/{task_id}-review-security.md` | P0-P3 列表 |
| 逻辑审查报告 | `reviews/{task_id}-review-logic.md` | P0-P3 列表 |
| 性能审查报告 | `reviews/{task_id}-review-performance.md` | P0-P3 列表 |
| 回归测试报告 | staging 分支 CI 输出 | 全量测试结果 |

## 过渡门禁

质量门禁全部通过，任务可以标记 DONE 的条件:

- [ ] GATE 1: 100% UT PASS + 100% API PASS (Newman exit 0)
- [ ] GATE 2: 安全/逻辑/性能审查 0 P0, 0 P1, 0 P2
- [ ] GATE 3: worktree 内回归 PASS（merge 主分支后 UT 仍然 PASS）
- [ ] 代码覆盖率 ≥ domain 阈值
- [ ] 无 `{占位符}` 残留的测试用例

**完成确认语:** "任务 {task_id} 三层门禁全部通过。UT {n}/{m} PASS，API {k}/{l} PASS，审查 by security/logic/performance 无 P0/P1/P2。回归检查通过。"
