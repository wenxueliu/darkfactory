# Works handoff protocol

用于子代理返回、上下文压缩前、跨会话恢复、连续两次同类失败或重要切片完成后的独立审查。交接包写入 `.planning/<run-id>/handoffs/<slice-id>-attempt-<n>.md`，保持简短，只引用持久制品，不复制大段源码和日志。

```markdown
# Handoff: <scope>

## Objective
<一个可验证目标或 Req ID>

## State
- Plan: <活动 plan ID/path>
- Phase: <Phase N>
- Status: <ready|blocked|needs-review>
- Next action: <唯一动作>

## Scope
- Read: <files/symbols>
- Changed: <files or none>
- Do not touch: <用户改动/范围外文件>

## Findings
- <结论 + file:line 或日志路径>

## Verification
- <command> → <exit/result>, log: <path>

## Open risks
- <未知项；没有则写 none>

## Acceptance for receiver
- [ ] <接手方必须验证的客观条件>

## Suggested skills
- works
- planning-with-files
- tdd（进入实现或测试诊断时）
```

## Worker rules

- worker 不修改 `task_plan.md` 或 `progress.md`，只追加自己的 planning ledger。
- 探索和审查 worker 默认只读；实现 worker 必须拥有互不重叠的文件范围和明确验收条件。
- orchestrator 不直接信任“已完成”，而是检查 diff、运行证据或复跑关键命令。
- handoff 中不得包含密钥、token、密码、PII 或大段第三方内容。
- 如果没有独立 handoff skill，直接使用本协议；不得因为缺少 skill 而中断工作。

## Verification loop

1. Implementer 完成一个切片并写 handoff。
2. Fresh verifier 不继承实现对话，只读取 handoff 引用的 requirement、矩阵、diff 和日志，返回 `PASS | CHANGES_REQUIRED | BLOCKED` 及 finding IDs。
3. `CHANGES_REQUIRED` 进入下一 attempt，并把 findings 作为路径引用传给 fresh implementer；最多三轮。
4. Verifier PASS 后，orchestrator 独立检查 diff 并复跑目标测试和必要回归，之后才能推进计划。
