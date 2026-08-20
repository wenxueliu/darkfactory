# Code-first evidence

`baseline-init` 先冻结初始生产指纹并建立 sequence 0 checkpoint；它不记录测试指纹，也不运行测试。后续证据链从该生产基线开始。

每个 Req 先实现、后测试，不建立 Red 证据：

1. 完成当前 Req 的最小生产代码修改。
2. 运行 `implement -- --req <REQ>`，冻结生产代码 checkpoint。
3. 添加或确认对应的 Maven 行为测试。
4. 运行 `test -- --req <REQ> --test-file <file> --testcase <case> -- <maven-command>`。

`test` 必须满足：

- 实现 checkpoint 后生产代码没有继续变化；
- 命令显式覆盖 Maven 的测试跳过配置；
- 指定 testcase 确实执行且通过；
- 生成新鲜的 Surefire/Failsafe JUnit XML 证据。

若测试失败，先诊断并改变实现或测试策略后重试；不能修改 `.planning/` 中的证据文件。
