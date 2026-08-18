# Works state contract

## Authority

`.planning/works-*/state.json` 是唯一流程状态。不得从 Markdown、对话记忆或单个日志推导阶段并手工覆盖它。

```text
state.json                 mutable, atomic, authoritative workflow state
impact-map.json            validated analysis artifact
logs/                      raw acceptance logs
evidence/baseline.json     immutable initial worktree evidence
evidence/checkpoint.json   latest successful Green production fingerprint
evidence/preflight.json    Maven test-execution proof
evidence/slices/<REQ>/      immutable Red/Green/JUnit/log evidence
evidence/tdd-verify.json    final replay result
```

## State transitions

```text
SETUP_REQUIRED
  └─ baseline + passed preflight
       → IMPACT_REQUIRED
          └─ ordered Req list + validated impact map
               → READY_FOR_RED
                  └─ valid Red
                       → READY_FOR_IMPLEMENTATION
                          └─ valid Green
                               ├─ next uncovered Req → READY_FOR_RED
                               └─ all Green → READY_FOR_ACCEPTANCE
                                    └─ verify + latest named checks pass → COMPLETE
```

`BLOCKED` 只用于保留无法安全推进的证据，不是绕过失败的完成状态。

## Invariants

- CLI 是唯一流程写入者；底层 evidence、impact 和 boundary 模块不修改 `state.json`。
- 状态只从已存在的证据文件和显式配置推导。
- `state.json` 使用临时文件和原子替换写入。
- requirements 顺序固定后决定 checkpoint 链和最终 verify 顺序。
- 人类可读报告只能由状态和证据单向生成，不能反向推进状态。
- 失败的 acceptance 会覆盖同名检查的最新结果；必须同名重跑成功才能完成。
