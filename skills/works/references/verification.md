# 完成前验证（无人化）

`finalize` 前，完成声明必须有新鲜完整证据。这是内置 reference，不加载外部 `sw-verification-before-completion` Skill。

## 证据优先

- 完成声明只由 works CLI 记录的事实推进：`tdd-verify.json`（重放每个 Req 测试）+ `final-verification.json`（契约里每条验收命令真实退出 0）。
- 文字结论不是证据；只有退出码、JUnit 和证据文件算数。

## finalize 做什么

`finalize` 命令会：

1. 重放全部 Req 的精确测试命令，要求目标 testcase 执行并通过。
2. 检查 Service 边界（无新增入口→持久层依赖）。
3. 跑契约里每条验收命令，写入 `acceptance-*.log`。

模型在 finalize 前只需确认：每个 Req 都有 Red + Green，且当前生产指纹等于最后 Green（见 [TDD evidence](tdd-evidence.md)）。

## 无人化硬约束

- **不做** commit、不创建 PR、不写 Consul KV、不跑 `complete_task.py`、不标记任务 DONE。
- 验证命令由 `finalize` 执行，模型不自行替换或精简契约命令。
- 验证失败 → 走 `reopen` 修复受影响的 Req，不把失败当成成功。
