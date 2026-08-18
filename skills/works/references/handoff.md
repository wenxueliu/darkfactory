# Works handoff

交接包只引用唯一状态和证据，不复制源码或长日志。保存到 `<plan>/handoffs/<req>-attempt-<n>.md`。

```markdown
# Handoff: <Req ID>

- State: <plan>/state.json
- Requirement: <path>
- Current state: <state>
- Current Req: <Req ID>
- Changed files: <paths or none>
- User-owned files: <paths>
- Evidence: <plan>/evidence/slices/<Req ID>/
- Last command: <command, exit, log path>
- Finding: <file:line or evidence path>
- Next action: <one allowed action from state.json>
- Risk: <unknown or none>
```

接收者先运行 `works.py --project <project> status`，确认交接中的状态仍然有效。实现者、审查者和接收者都不得直接编辑 `state.json` 或 evidence JSON。

Fresh verifier 只读取 requirement、state、当前 Req diff 和引用证据，返回 `PASS | CHANGES_REQUIRED | BLOCKED`。`PASS` 仍不能替代 CLI 的 Green/verify。
