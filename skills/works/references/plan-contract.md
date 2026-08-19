# Works state contract

`.planning/works-*/state.json` 是唯一流程进度。OpenCode 每完成一个 `next_action` 后重新读取它，不从聊天摘要推导阶段。

```text
SETUP_REQUIRED
  -> baseline + successful baseline-only probe
CONTRACT_REQUIRED
  -> validated requirement-contract.json
CONTRACT_REVIEW_REQUIRED
  -> fresh verifier confirms contract matches requirement.md
IMPACT_REQUIRED
  -> validated impact-map.json
READY_FOR_RED
  -> current Req target assertion fails
READY_FOR_IMPLEMENTATION
  -> same target passes after implementation
READY_FOR_ACCEPTANCE
  -> finalize replays every Req and every contract acceptance command
  -> failure: append a repair Req for the affected behavior and establish a new Red/Green
IMPLEMENTATION_REVIEW_REQUIRED
  -> fresh verifier confirms each Req has matching implementation and tests
  -> failure: append a repair Req and repeat Red/Green/finalize/review
COMPLETE
```

`next_action` 始终只有一个。复合动作如 `establish-red-for-current-requirement` 表示模型先新增或复用当前行为测试，再立刻调用对应 CLI 门禁，不在两步之间重新规划或停止。

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
evidence/slices/<REQ>/red.json      failing behavior evidence
evidence/slices/<REQ>/green.json    passing implementation evidence
evidence/tdd-verify.json            replay of every Req test
evidence/final-verification.json    all contract commands and exits
implementation-review.json         independent requirement/implementation review
```

状态只能由 works CLI 推进。命令失败保持当前阶段并增加 attempt；相同失败不能在相同工作区原样重放。`recover` 只读取和汇总状态，不推进阶段。
