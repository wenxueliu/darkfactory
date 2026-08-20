# Independent reviews

两次审查都必须由全新上下文的只读 subagent 执行，并加载 `impl-validator`。它不能修改任何文件，只在响应中返回审查报告和机器可读的 `review_payload`。Works 主 agent 是唯一落盘者：它只能把 payload 原样写入已初始化的 review JSON，不得自行补全、改写或将 FAIL 提升为 PASS。Works 仍是唯一 orchestrator。

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

只提供 `requirement.md` 和 `requirement-contract.json`。逐项检查：原始行为是否遗漏或多出、描述是否歧义、验收标准是否可观察、验收命令是否覆盖全部 Req。`review_payload` 必须与 `contract-review-init` 生成的 schema 一致。所有 Req 为 `PASS` 且 `missing`、`extra`、`ambiguous`、`invalid_acceptance` 为空时，顶层 `result` 才能为 `PASS`。

若失败，works 根据 finding 修订契约，重新运行 `contract-check`，删除旧审查并启动新的 verifier。不得由原实现上下文自我批准。

## Implementation review

只提供 `requirement.md`、`requirement-contract.json`、`impact-map.json`、最终 git diff、implementation/test/replay 证据和 `final-verification.json`。逐 Req 判断行为是否实现且有测试证据，在 `review_payload` 的 `implementation` 和 `tests` 中返回结构化位置证据：项目相对 `path`、有效 `line`、非空 `symbol` 和解释 Req 关联的 `reason`。CLI 会验证路径边界、文件存在性和行号。发现额外行为写入 `extra`。

每个 Req 还必须检查复用顺序：对 diff 中每个新增 Mapper/Repository 调用，先阅读所在类的已有方法，再查同层 Service API。若已有方法能以相同输入输出、过滤条件和副作用满足需求，直接调用持久层必须将该 Req 标为 `FAIL`，finding 指出应复用的类和方法。只有本类和同层 Service 都没有等价能力时，新增 Mapper/Repository 调用才可通过此项审查。

同时检查测试隔离：每个 Req 的测试只能断言本次实现或修改的行为，必须使用 Mockito，禁止 `@SpringBootTest`；第三方 SDK、HTTP/RPC client、数据库、消息、缓存、文件、时钟及其他外部协作者必须直接 mock。发现真实外部调用、Spring context、模块级/全量命令或无关存量行为断言时，将对应 Req 标为 `FAIL`。

若失败，works 对失败 Req 执行 `reopen`，完成新的 implementation→test 和 finalize 后，再启动新的 verifier。只有该审查通过，状态才能进入 `COMPLETE`。
