# Works plan contract

使用 planning-with-files 的隔离计划目录和 gated 模式。保留其原生模板字段，但将阶段统一为以下六个；正文和状态表不得另起一套编号。

## Run Contract

- Mode: gated + inject-smart
- Gate cap: 20
- Single writer: orchestrator
- Completion requires two independent gates: plan state and acceptance evidence
- Worker protocol: per-agent ledger + handoff; workers never edit `task_plan.md`
- State authority: `works-state.json` + immutable TDD evidence; Phase 2–6 only advance through `works_plan_gate.py`

## Goal

用一句话描述基于 `requirement.md` 可观察、可验证的最终状态。

## Next Step

始终只有一个可执行动作，精确到当前 Req ID、测试或诊断命令。

## Current Phase

只能是 Phase 1–6 之一。

## Phases

### Phase 1: Preconditions
- [ ] 已自主发现并记录 requirement、项目根、构建入口和用户工作区基线，未请求用户确认
- [ ] planning 会话、日志目录和追踪矩阵已初始化
- **Status:** in_progress

### Phase 2: Baseline
- [ ] 原有可信测试已运行并分类失败
- [ ] 修改前已有失败与构建环境问题已记录
- [ ] `tdd_slice.py init` 已保存当前 dirty-worktree TDD 基线
- [ ] `tdd_slice.py probe` 已覆盖 POM/CLI skip 配置并证明现有目标 testcase 实际执行
- **Status:** pending
- **DependsOn:** Phase 1

### Phase 3: Impact analysis
- [ ] 每个 Req ID 均映射到行为、seam、Service API、Mapper/Repository、风险和测试
- [ ] 已通过 `set-reqs` 固化完整有序 Req 队列；后续切片自动续跑
- [ ] IN/OUT scope 与动态依赖风险已记录
- [ ] 必要的 characterization tests 已在生产代码修改前通过
- [ ] 上层入口均复用/扩展 Service，或存在有证据的架构例外
- **Status:** pending
- **DependsOn:** Phase 2

### Phase 4: Vertical TDD
- [ ] 每个 Req ID 均有脚本生成的 `red.json`、`green.json` 和局部回归证据
- [ ] 每个切片的生产修改都发生在有效 Red gate 之后
- [ ] 所有切片均通过 diff 边界检查
- [ ] `service_boundary.py verify` 未发现新增入口→Mapper/Repository/直接数据访问依赖
- **Status:** pending
- **DependsOn:** Phase 3

### Phase 5: Acceptance
- [ ] `tdd_slice.py verify` 覆盖全部 Req ID 并通过
- [ ] 相关模块、完整回归和项目规定的质量命令已验证
- [ ] requirement 追踪矩阵无缺口
- **Status:** pending
- **DependsOn:** Phase 4

### Phase 6: Delivery
- [ ] 最终 diff、用户原有改动和未决风险已审计
- [ ] 最终报告或 handoff 包已生成
- **Status:** pending
- **DependsOn:** Phase 5

## Evidence format

原始日志存放在活动计划目录的 `logs/`。`progress.md` 只保存固定形状摘要：

| Req ID | Stage | Command | Expected | Exit | Tests | Log | Result |
|---|---|---|---|---:|---:|---|---|

Red 的 Result 只有在失败为目标行为断言时才能记作 `valid-red`；基础设施或编译失败记为 `invalid-red`。

## Reopen rule

后续验证推翻已完成阶段时，将受影响阶段恢复为 `in_progress`，后续阶段恢复为 `pending`，刷新 `Current Phase` 和单一 `Next Step`，重新 attestation 后继续。禁止保留虚假的 complete 状态。

`check-complete.sh` 只统计阶段状态，不执行测试或 `AcceptanceCheck`。修改计划后立即重新运行 `attest-plan.sh`；不要把未重新 attestation 的计划留给无人值守循环。

## Executable phase transition

每个 TDD 命令成功后会自动同步计划。恢复会话或怀疑状态漂移时运行：

```bash
python3 <works>/scripts/works_plan_gate.py sync --state-dir <plan-dir>/tdd
```

Phase 2–6 禁止直接编辑状态或直接运行 `phase-status.sh`，统一使用：

```bash
python3 <works>/scripts/works_plan_gate.py complete-phase --state-dir <plan-dir>/tdd --phase 2
python3 <works>/scripts/works_plan_gate.py set-reqs --state-dir <plan-dir>/tdd --req REQ-1 --req REQ-2
python3 <works>/scripts/works_plan_gate.py complete-phase --state-dir <plan-dir>/tdd --phase 4 --req REQ-1 --req REQ-2
python3 <works>/scripts/works_plan_gate.py check --state-dir <plan-dir>/tdd --name module-regression -- <真实命令>
python3 <works>/scripts/works_plan_gate.py complete-phase --state-dir <plan-dir>/tdd --phase 5 --req REQ-1 --req REQ-2
```

门禁会重新执行最终 TDD verify，而不是信任旧 `tdd-verify.json`；Phase 5 还要求 `acceptance.json` 中至少有一个真实成功命令。每次转换都会更新 Next Step、ledger、`works-state.json` 并重新 attestation。
