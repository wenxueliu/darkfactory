# 完成前验证（无人化）

`finalize` 前，完成声明必须有新鲜完整证据。这是内置 reference，不加载外部 `sw-verification-before-completion` Skill。

## 证据优先

- 完成声明只由 works CLI 记录的事实推进：`code-first-verify.json`（校验 checkpoint 与 evidence hash）+ `final-verification.json`（契约里每条验收命令真实退出 0）。
- 文字结论不是证据；只有退出码、JUnit 和证据文件算数。

## finalize 做什么

`finalize` 命令会：

1. 校验全部 Req 的 checkpoint、生产指纹和 implementation/test evidence hash；`SKIPPED` Req 改为校验 implementation hash、连续三次失败证据和 checkpoint 转换。
2. 检查统一 architecture gate（Service boundary 与 reuse enforcement）。
3. 统一跑契约里每条精确 `-Dtest=Class#method` 验收命令一次，要求目标 testcase 执行并通过，写入 `acceptance-*.log`；不在 code-first verify 中重复重放同一 selector，也不运行模块级或全量存量测试。

模型在 finalize 前只需确认：每个 Req 都有 implementation + test 证据，且当前生产指纹等于最后 test checkpoint（见 [Code-first evidence](code-first.md)）。

## 无人化硬约束

- **不做** commit、不创建 PR、不写 Consul KV、不跑 `complete_task.py`、不标记任务 DONE。
- 验证命令由 `finalize` 执行，模型不自行替换或精简契约命令。
- 验证失败 → 走 `reopen` 修复受影响的 Req，不把失败当成成功。
