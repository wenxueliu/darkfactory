# Independent reviews

两次审查都必须由全新上下文的只读 subagent 执行，并加载 `impl-validator`。它不能修改生产代码、测试、契约或 works 状态，只能把判断写入已初始化的 review JSON。Works 仍是唯一 orchestrator。

## Contract review

只提供 `requirement.md` 和 `requirement-contract.json`。逐项检查：原始行为是否遗漏或多出、描述是否歧义、验收标准是否可观察、验收命令是否覆盖全部 Req。所有 Req 为 `PASS` 且 `missing`、`extra`、`ambiguous`、`invalid_acceptance` 为空时，顶层 `result` 才能为 `PASS`。

若失败，works 根据 finding 修订契约，重新运行 `contract-check`，删除旧审查并启动新的 verifier。不得由原实现上下文自我批准。

## Implementation review

只提供 `requirement.md`、`requirement-contract.json`、`impact-map.json`、最终 git diff、Red/Green/replay 和 `final-verification.json`。逐 Req 判断行为是否实现且有测试证据，在 `implementation` 和 `tests` 中写入具体文件或证据路径。发现额外行为写入 `extra`。

若失败，works 对失败 Req 执行 `reopen`，完成新的 Red→Green 和 finalize 后，再启动新的 verifier。只有该审查通过，状态才能进入 `COMPLETE`。
