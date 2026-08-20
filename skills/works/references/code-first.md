# Code-first evidence

`preflight` 冻结初始生产指纹并建立 sequence 0 checkpoint；它不记录测试指纹，也不运行测试。后续证据链从该生产基线开始。

每个 Req 先实现、后测试，不建立 Red 证据：

1. 完成当前 Req 的最小生产代码修改。
2. 运行 `implement -- --req <REQ>`，冻结生产代码 checkpoint。
3. 添加对应实现行为的快速测试；存在外部协作者时优先 Mockito，纯逻辑允许普通 JUnit。不要为存量行为补测或运行存量测试。
4. 运行 `test -- --req <REQ> --test-file <file> --testcase <case>`。不要在命令尾部重复拼接 Maven 命令；CLI 从 `requirement-contract.json` 读取已校验的 argv 数组，并在 Windows `.cmd`/`.bat` wrapper 上自动经 `cmd /c` 执行。

`test` 必须满足：

- 实现 checkpoint 后生产代码没有继续变化；
- 契约命令显式覆盖 Maven 的测试跳过配置；
- 命令必须且只能包含一个与 `--testcase` 完全一致的 `-Dtest=Class#method`，禁止模块级或全量测试；
- 禁止无必要的 `@SpringBootTest`；外部协作者必须隔离，纯逻辑测试无需为了形式引入 Mockito；
- 被测类的第三方依赖、远程客户端、数据库、消息、缓存、时钟及其他外部协作者直接 mock，不启动 Spring context，不访问真实基础设施；
- 断言只覆盖当前 Req 新实现或修改的行为，不借机验证无关存量功能；
- 指定 testcase 确实执行且通过；
- 生成新鲜的 Surefire/Failsafe JUnit XML 证据。

实现前必须读取 `status.next_action.reuse_decision`，并严格使用其中选定的复用目标。`contract-check` 冻结持久层调用基线；`implement` 重新读取 `requirement-contract.json`，校验目标文件和 symbol 仍有效，并把决策及 contract 哈希写入 implementation evidence。选择 `existing_method` 或 `service_api` 时，变更后的生产文件必须实际引用该目标，且相对基线不得新增 Mapper/DAO/Repository 或直接数据访问调用。repair Req 使用原始 Req 的复用决策。不得在实现后反向修改 contract 为已经写出的代码辩护。

若测试失败，先诊断并改变实现或测试策略后重试；不能修改 `.planning/` 中的证据文件。
