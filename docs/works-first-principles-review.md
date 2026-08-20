# Works 第一性原理审视

## 目标

`works` 的核心目标只有四个：

1. 正确理解需求。
2. 以最小、安全的方式修改代码。
3. 用真实执行证明需求成立。
4. 在长任务中断后可靠恢复。

任何不能显著服务这四点的状态、文件和重复执行，都应被视为待删除或待合并的复杂度。

## 最小不可约流程

```text
discover + baseline
→ contract
→ implement + focused test
→ verify
→ risk-based final review
→ complete
```

## 仍可删除或合并的冗余

### 1. Doctor 与 init 重复发现项目

`doctor` 和 `init` 都会发现项目根目录、requirement、POM、Maven wrapper 和 Git 状态。`doctor` 更适合作为可选排障命令，不应是正常状态机步骤。

建议正常流程直接从 `init` 开始，由 `init` 完成环境检查；保留 `doctor` 供人工诊断。

### 2. Contract-init 空模板动作

当前先创建空 JSON，再由 Agent 填写并运行 `contract-check`。空模板不形成有价值的业务状态，可以作为内部实现细节合并进 contract 生成动作。

### 3. 每个动作后重新执行 status

大多数 CLI 动作已返回刷新后的 `state`、`current_req` 和 `next_action`，成功后再次运行 `status` 是重复读取。

建议直接使用动作响应中的 `next_action`；只在恢复、响应丢失或人工检查时运行 `status`。

### 4. Summaries 与状态、活动日志重复

`summaries/*.json` 通常重复记录 `state.json` 和 `activity.jsonl` 已有的动作、状态、Req 和结果。

建议只保留：

```text
state.json
activity.jsonl
evidence/
```

`findings.jsonl` 和 `decisions.jsonl` 按需追加，不为每个阶段强制生成 summary。

### 5. Finalize 重复运行相同测试

同一条定向测试可能经历：

1. Req 开发阶段的 `test`；
2. `code-first verify` 重放；
3. `finalize` 再执行 contract acceptance command。

如果后两者执行的是同一个 `Class#method`，属于重复验收。

建议开发阶段运行一次形成快速反馈；finalize 统一重放 contract commands 一次，并同时校验 checkpoint、evidence hash 和 Service boundary。

### 6. Implementation reviewer 的位置证据过重

Reviewer 当前返回 `path + line + symbol + reason`，但实际位置已经存在于 Git diff、implementation evidence 和 test evidence。重复提交位置会产生行号漂移和 JSON 格式负担。

建议 reviewer 只返回每个 Req 的 `PASS/FAIL + finding`，由 CLI 自动关联已有 evidence。

### 7. Service boundary 与 reuse enforcement 可以统一呈现

两者分别阻止入口直连持久层和绕过已有方法或 Service API。内部实现可以保持独立，但状态机只需暴露一个统一的 architecture gate。

## 当前关键缺失

### 1. 测试失败后的生产代码返工路径

这是最高优先级问题。

当前流程在 `implement` 后冻结 implementation checkpoint，并进入 `READY_FOR_TEST`。如果测试暴露生产代码错误，模型需要修改生产代码，但 checkpoint 已存在、生产编辑被禁止，且 `implement` 不允许覆盖 evidence，容易形成状态机死角。

建议增加：

```text
READY_FOR_TEST
  ├── test passed → next Req
  └── production fix required
        → rework
        → archive old implementation evidence
        → READY_FOR_IMPLEMENTATION
```

示例命令：

```text
rework -- --req REQ-1 --reason production-fix
```

它应保留失败日志、归档旧 checkpoint、重新允许生产修改，但不创建 repair Req。Repair Req 只用于已经完成后被 finalize 或 reviewer 重新打开的行为。

### 2. Requirement 来源追踪

删除 contract reviewer 后，主要风险是 contract 本身漏掉需求。每个 Req 应保存轻量来源，例如：

```json
{
  "source": {
    "heading": "用户查询",
    "item": "返回展示名称"
  }
}
```

不要保存易漂移行号或长篇原文。Contract-check 应验证每个 Req 有来源、来源项不重复，并尽可能检查 requirement 中明确列表项的覆盖。

### 3. 无人值守下的矛盾与阻塞政策

需要明确处理 requirement 内部矛盾、与仓库事实冲突、验收不可观察、互斥方案和缺少外部凭据等情况：

```text
可安全推断 → 采用最小、可逆解释并记录 decision
可降级实现 → 采用不破坏现有行为的保守方案并记录 limitation
无法正确实现 → BLOCKED，记录矛盾和已穷尽证据
```

无人值守不应等同于在信息不足时编造答案。

### 4. Baseline build/compile 归因

Preflight 完全不编译，会导致后续无法区分既有构建故障与本次回归。

建议执行低成本 baseline：

```text
mvn -DskipTests compile
```

或针对受影响模块执行 `test-compile`。只记录命令、退出码和失败摘要，不运行全量存量测试。

### 5. 结构化风险模型

仅依赖关键词容易漏判，例如“只有管理员可以”属于 authorization，“旧客户端继续可用”属于 compatibility。

建议 contract 使用有限风险类型：

```text
authorization
security
transaction
migration
compatibility
cross_module
external_side_effect
persistence
```

关键词只作为兜底，不作为主要判断方式。

### 6. 精确 testcase 冻结时机

Contract 阶段过早冻结 `Class#method`，可能迫使模型在探索不完整时选择错误测试 seam。

更合理的设计是 contract 先冻结测试边界和行为，在 implementation checkpoint 时再冻结测试文件与 selector。该优化会增加少量状态复杂度，优先级低于返工闭环。

### 7. 非生产代码变化的合法 Req

当前 `implement` 要求必须产生 production diff，无法表达：

- test-only；
- config change；
- already satisfied；
- 只修测试 fixture。

可以给 Req 增加变更类型：

```text
production_change
test_only
config_change
already_satisfied
```

`already_satisfied` 必须有现有源码位置、新增验收测试和真实执行证据，防止空完成。

## 实施优先级

### 第一优先级：补齐正确性闭环

1. 增加 `implement → test failed → rework → implement` 路径。
2. 增加 requirement 来源追踪。
3. 定义保守推断、降级实现和 `BLOCKED` 政策。

### 第二优先级：继续减重

1. 合并正常路径中的 `doctor/init/preflight`。
2. 删除自动 summaries。
3. 合并 finalize 的重复测试重放。
4. 简化 implementation reviewer payload。

### 第三优先级：根据评测决定

1. 使用结构化风险替代关键词。
2. 延迟冻结精确 testcase。
3. 支持 test-only、config-change 和 already-satisfied Req。

## 结论

当前主要问题已经不再是成功路径阶段过多，而是失败后的正常返工路径不足。下一步最有价值的工作不是继续删除门禁，而是补齐：

```text
implement → test failed → rework → implement
```

在此基础上，再删除重复状态、日志和测试重放，才能同时提高 MiniMax M2.7 的完成率与执行效率。
