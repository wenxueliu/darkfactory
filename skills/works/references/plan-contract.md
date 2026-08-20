# Works state contract

`.planning/works-*/state.json` 是唯一流程进度。OpenCode 每完成一个 `next_action` 后重新读取它，不从聊天摘要推导阶段。

```text
SETUP_REQUIRED
  -> baseline + successful probe (initialize Git when absent; run no tests)
CONTRACT_REQUIRED
  -> empty template
  -> fresh read-only contract-author payload
  -> validated requirement-contract.json
CONTRACT_REVIEW_REQUIRED
  -> fresh verifier confirms contract matches requirement.md
IMPACT_REQUIRED
  -> validated impact-map.json
READY_FOR_IMPLEMENTATION
  -> current Req production change is frozen as an implementation checkpoint
READY_FOR_TEST
  -> current Req target testcase executes and passes
READY_FOR_ACCEPTANCE
  -> finalize replays every Req and every contract acceptance command
  -> failure: append a repair Req for the affected behavior and repeat implementation/test
IMPLEMENTATION_REVIEW_REQUIRED
  -> fresh verifier confirms each Req has matching implementation and tests
  -> failure: append a repair Req and repeat implementation/test/finalize/review
COMPLETE
```

`next_action` 始终只有一个。实现和测试分别由 `implement` 与 `test` 门禁记录；完成一个动作后立即重新读取状态，不在中间建立第二套计划。

关键文件：

```text
state.json                         workflow state, attempts and next_action
requirement-contract.json          Req + acceptance contract
contract-review.json               independent requirement/contract review
impact-map.json                    repository-grounded implementation map
activity.jsonl                     action and failure journal
findings.jsonl                     reusable repository facts
decisions.jsonl                    implementation choices
summaries/                         small phase recovery summaries
evidence/baseline.json             initial worktree snapshot
evidence/preflight.json            baseline load/hash proof (no tests run)
evidence/slices/<REQ>/implementation.json  frozen production change
evidence/slices/<REQ>/test.json            passing testcase evidence
evidence/code-first-verify.json            replay of every Req test
evidence/final-verification.json    all contract commands and exits
implementation-review.json         independent requirement/implementation review
```

状态只能由 works CLI 推进。命令失败保持当前阶段并增加 attempt；相同失败不能在相同工作区原样重放。`recover` 只读取和汇总状态，不推进阶段。
