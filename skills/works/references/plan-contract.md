# Works plan contract

使用 planning-with-files 的隔离计划目录和 gated 模式。保留其原生模板字段，但将阶段统一为以下六个；正文和状态表不得另起一套编号。

## Run Contract

- Mode: gated + inject-smart
- Gate cap: 20
- Single writer: orchestrator
- Completion requires two independent gates: plan state and acceptance evidence
- Worker protocol: per-agent ledger + handoff; workers never edit `task_plan.md`

## Goal

用一句话描述基于 `requirement.md` 可观察、可验证的最终状态。

## Next Step

始终只有一个可执行动作，精确到当前 Req ID、测试或诊断命令。

## Current Phase

只能是 Phase 1–6 之一。

## Phases

### Phase 1: Preconditions
- [ ] requirement、仓库、构建入口和用户工作区基线已确认
- [ ] planning 会话、日志目录和追踪矩阵已初始化
- **Status:** in_progress

### Phase 2: Baseline
- [ ] 原有可信测试已运行并分类失败
- [ ] 修改前已有失败与构建环境问题已记录
- **Status:** pending
- **DependsOn:** Phase 1

### Phase 3: Impact analysis
- [ ] 每个 Req ID 均映射到行为、seam、候选符号、风险和测试
- [ ] IN/OUT scope 与动态依赖风险已记录
- [ ] 必要的 characterization tests 已在生产代码修改前通过
- **Status:** pending
- **DependsOn:** Phase 2

### Phase 4: Vertical TDD
- [ ] 每个 Req ID 均有有效 Red、Green 和局部回归证据
- [ ] 所有切片均通过 diff 边界检查
- **Status:** pending
- **DependsOn:** Phase 3

### Phase 5: Acceptance
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
