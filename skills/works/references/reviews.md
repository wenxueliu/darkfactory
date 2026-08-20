# Independent reviews

审查是风险门，不是固定仪式。Req ≥ 4，或涉及安全、权限、事务、迁移、兼容、跨模块/跨服务、持久层新增或架构例外时，由全新上下文的只读 subagent 加载 `impl-validator`。普通需求依赖确定性门禁后直接推进。Reviewer 不能修改文件，只返回 review payload；Works 负责落盘。

## Subagent 调用契约

调用 prompt 必须使用 `impl-validator` 的结构化输入：

```text
impl-validator check:
  goal: "独立验证审查目标是否与 requirement 一致"
  artifacts: [<只读文件的绝对路径>]
  checks:
    - "按 Req ID 逐项验证指定审查项"
    - "返回标准 impl-validator Report"
    - "报告末尾附加一个 JSON 代码块，内容是完整 review_payload，不得写文件"
```

Works 主 agent 必须校验 payload 是单一 JSON 对象，`version`、`type` 和 Req ID/顺序与已初始化模板一致，且没有额外字段；随后用该对象整体覆盖 review JSON。若 payload 缺失、无法解析或 schema 不匹配，不要猜测修复，废弃该响应并启动新的 verifier。

## Contract review

只提供 `requirement.md` 和 `requirement-contract.json`。逐项检查：原始行为是否遗漏或多出、描述是否歧义、验收标准是否可观察、计划中的验收命令是否具备合法结构、可测试性并覆盖全部 Req。此时验收命令是前瞻性测试契约，不检查目标测试文件或方法是否已存在，不执行命令；不得仅因计划中的测试尚未创建而标记 `invalid_acceptance`。`review_payload` 必须与 `contract-review-init` 生成的 schema 一致。所有 Req 为 `PASS` 且 `missing`、`extra`、`ambiguous`、`invalid_acceptance` 为空时，顶层 `result` 才能为 `PASS`。

若失败，works 根据 finding 修订契约，重新运行 `contract-check`，删除旧审查并启动新的 verifier。不得由原实现上下文自我批准。

## Implementation review

只提供 `requirement.md`、`requirement-contract.json`、最终 git diff、implementation/test/replay 证据和 `final-verification.json`。逐 Req 判断行为是否实现且有测试证据，在 `review_payload` 的 `implementation` 和 `tests` 中返回结构化位置证据。发现额外行为写入 `extra`。

每个 Req 还必须检查复用顺序，并核对 implementation evidence 绑定的 contract `implementation.reuse` 与最终 diff 一致。只有 contract 选择 `persistence`、包含本类与同层 Service 的缺失证据，并且 reviewer 独立确认两处确无等价能力时，新增 Mapper/Repository 调用才可通过。

同时检查测试隔离：每个 Req 的测试只能断言本次行为；存在外部协作者时使用 Mockito 或项目已有 fake，纯逻辑允许普通 JUnit。禁止无必要的 Spring context、真实外部调用、模块级/全量命令或无关存量断言。

若失败，works 对失败 Req 执行 `reopen`，完成新的 implementation→test 和 finalize 后，再启动新的 verifier。只有该审查通过，状态才能进入 `COMPLETE`。
