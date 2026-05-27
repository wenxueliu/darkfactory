# FAQ — 黑灯工厂常见问题

## Q1: `requirements-tracker.yaml` 什么时候更新？如何保证顺序执行和迭代循环？

### 更新时机

每个阶段由专门的 Agent 写入自己的 `phase.status`：

| 阶段 | 写入 Agent | 更新内容 |
|------|-----------|---------|
| ideation | `sw-requirements-clarifier` | 创建条目，设 `ideation.status = done` |
| value_assessment | `sw-value-judgment` | 设 `value_assessment.status = done` |
| design | `sw-feature-designer` | 设 `design.status = done` |
| decomposition | `sw-task-decomposer` | 设 `decomposition.status = done`，初始化 `execution.progress` |
| execution | `sw-plan-executor` | 开始→`in_progress`，每 wave 更新 progress，完成→`done` |
| merge | `sw-controller` / `sw-finishing-branch` | `merge.status = done` |
| test | `sw-integration-tester` / `sw-browser-tester` | `test.status = done` |
| delivery | `sw-delivery-manager` | `delivery.status = done` |

`sw-controller` 以 tracker 为权威数据源做阶段转换决策。

### 顺序执行的三层保障

1. **ideation-gate.py 硬门禁（PreToolUse Hook）**：任何 Agent/Write/Edit 调用前检查 `ideation.status == done`，未完成直接 DENY。
2. **Phase Transition Rules**：sw-controller 的 SKILL.md 定义了每阶段转换的前置条件清单，全部 PASS 才能推进。
3. **Gate 质量门禁**：每阶段有独立门禁文档（requirements-gate / design-gate / quality-gates / delivery-acceptance-gate），全 PASS 才能过渡。

完整 pipeline：`ideation → design → decomposition → execution → merge → test → delivery`

### 迭代循环（需求澄清验证失败 → 回到需求澄清）

```
PASS → 进入下一阶段
FAIL → 标记阻塞原因 → 回到当前阶段重新执行 → 最大重试 3 轮
       3 轮后仍未 PASS → 升级到人工决策
```

- 需求门禁 `requirements-gate.md` 有 G1-G4 四项检查（完整性 / 可测量性 / 价值对齐 / 风险就绪）
- `FAIL` 时 tracker 中标记 `ideation.status = blocked` + `block_reason` + `retry_count`
- 统一模式适用所有阶段门禁，重试上限为 `min_iteration_before_human`（默认 3）

---

## Q2: 需求澄清之后，value_assessment 被跳过了，为什么？

### 根因

1. **`current_phase` 管道不包含 value_assessment**：tracker 模板定义的 pipeline 是 `ideation → design → ...`，value_assessment 只是 YAML 的 phase 跟踪字段，不是管道的一站。
2. **ideation-gate.py 只检查 ideation**：hook 只验证 `ideation.status == done`，不检查 `value_assessment.status`。
3. **没有独立的阶段转换规则**：Phase Transition Rules 只有 `ideation → design`，没有 `ideation → value_assessment` 或 `value_assessment → design`。
4. **value_assessment 依赖 controller "记得" 委派**：Controller SKILL.md 的 Ideation 步骤写了要委派 sw-value-judgment，但这是自然语言指令，没有硬性强制。

### 结论

value_assessment 在 YAML 里是一个 phase，但在管道执行逻辑中只是 ideation 阶段内的"建议执行"子步骤，没有被提升为不可跳过的门禁阶段。

---

## Q3: 设计阶段是否有验证器？

有。设计阶段采用 **3-Stage 分层设计 + 每层自有验证器 + 最终统一门禁**：

### 验证器结构

| 阶段 | 验证器 | 检查维 | 产出 |
|------|--------|--------|------|
| Stage 1 | `feature-design-validator.md` | V1 完整性 / V2 一致性 / V3 可过渡性 | designs/{id}-design.md |
| Stage 2 | `service-design-validator.md` × N | V1 完整性 / V2 UT设计质量 / V3 API测试设计质量 / V4 可执行性 | designs/{id}-service-{svc}-design.md |
| Stage 3 | `e2e-design-validator.md` | V1 功能E2E / V2 非功能E2E / V3 兼容性E2E / V4 数据自包含 / V5 自定义扩展 | designs/{id}-e2e-design.md |
| 最终 | `design-gate.md` | G1 完整性 / G2 可实施性 / G3 安全就绪 / G4 知识沉淀 | — |

### 可选：多模型交叉验证

`design-validator.md` 按 `business_domain` 驱动：fintech 强制开启（3 模型），ecommerce 默认开启（2 模型），internal-tools 默认关闭。2-4 个不同画像（分析型/直觉型/对抗型/系统型）的模型并行交叉审查，聚合共识分析。

---

## Q4: 设计任务规划时是否考虑 lint 检查？什么时候触发 lint？

### 设计/规划阶段不考虑 lint

lint 是代码级执行标准，不是设计级决策。设计阶段关注需求完整性、架构设计、API 契约、测试设计；任务拆分阶段关注 DAG 依赖、任务粒度、并行度。

### lint 在执行阶段的三个触发点

```
UT Cycle → API Test Cycle → sw-lint-checker → Code Review → Quality Gates → Report DONE
```

| 层面 | 时机 | 执行者 | 文件 |
|------|------|--------|------|
| Worktree Controller | TDD (UT+API) 完成后、Code Review 之前 | sw-lint-checker (`lint_runner.py`) | `quality-gates.md:13` |
| Plan Executor 验证协议 | Phase A 自动化验证第4步 | `lint_runner.py` | `verification-protocol.md:15` |
| Completion Gate | 任务声明 DONE 前的最终检查 | Controller 读 lint 输出 | `completion-gate.md:17` |

### sw-lint-checker 3 轮循环

```
Round 1: lint_runner.py --auto-fix → 工具自动修复 → re-check
Round 2: LLM 直接修复剩余非自动修复的错误 → re-check
Round 3: 委托 sw-tdd-agent 修复 → re-check

PASS at any point → LINT_PASS
BLOCKED after 3 rounds → LINT_BLOCKED → 升级人工
```

支持的语言：python / javascript / typescript / go / shell / markdown / css / dockerfile / yaml / toml / json。

---

## Q5: task decomposition 有 test_bindings 和 review_requirements，为什么不需要 lint？

`test_bindings` 和 `review_requirements` 是"变化的"——每个任务绑定不同的测试用例、需要不同的审查者，必须在 tasks.yaml 中 per-task 定义。

lint 是"不变的"——由服务语言决定，与任务内容无关：

| 任务所属服务语言 | lint 工具 | 来源 |
|----------------|----------|------|
| java-springboot | checkstyle / spotbugs | service-registry.yaml → language |
| nodejs-express | eslint + prettier | 同上 |
| golang | golangci-lint + gofmt + go vet | 同上 |
| python-fastapi | ruff | 同上 |

服务的 `language` 字段已在 tasks.yaml 中，worktree controller 执行时自动推导并运行对应的 lint 工具。每个任务都必须 lint，不存在"可选"的情况。因此在 tasks.yaml 中显式声明 `lint_requirements` 只会增加冗余。

### 三层对比

| 维度 | test_bindings | review_requirements | lint |
|------|-------------|-------------------|------|
| 变化性 | 每个任务不同 | 每个任务不同 | 每个语言固定 |
| 选择性 | 绑定特定用例 | 选择性启用 | 必执行 |
| 定义位置 | tasks.yaml (per-task) | tasks.yaml (per-task) | 执行层 (auto-detect) |
| 何时触发 | TDD 执行时 | Code Review 前 | TDD 完成后、Review 前 |
