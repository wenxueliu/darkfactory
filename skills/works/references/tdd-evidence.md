# TDD evidence contract

`tdd_slice.py` 是底层证据引擎，只处理文件指纹、Maven/JUnit 和 Red→Green 链；它不修改 `state.json`、不推进阶段、不调用其他控制模块。应用层通过 `works.py` 编排它。

## Baseline and preflight

`tdd-init` 在 `<plan>/evidence/` 保存当前 dirty worktree 的生产、测试和 Git 状态。用户已有修改因此成为受保护起点。baseline 不可覆盖。

`probe` 必须用一个已有稳定 testcase 证明 Maven 真正执行测试：

```text
<python> <works>/scripts/works.py --project <project> probe -- --testcase ExistingTest#behavior -- <maven-command> -DskipTests=false -Dmaven.test.skip=false -Dtest=ExistingTest#behavior test
```

`<python>` 在 Windows 为 `py -3`、在 Linux 为 `python3`；`<maven-command>` 在 Windows 优先为 `mvnw.cmd`、在 Linux 优先为 `./mvnw`，没有 wrapper 时为 `mvn`。

POM 中每个 true-valued `skip*test*` 属性都必须对应 `-D<name>=false`。只有新鲜 Surefire/Failsafe XML 证明目标 testcase 执行并通过，preflight 才有效。

## Red

有效 Red 同时要求：

- 当前生产指纹等于 baseline 或上一 Green checkpoint；
- 目标测试文件相对 baseline 已变化；
- 命令非零退出；
- 新鲜 XML 中目标 testcase 自身有 assertion failure；
- 目标 testcase 没有 test error；
- 编译、fixture、依赖和环境错误不算 Red。

Red 保存 testcase、测试哈希、完整命令、日志、JUnit 报告和当前 checkpoint 哈希。

## Green

Green 必须使用与 Red 完全相同的命令。Red 测试哈希不能变化，生产指纹必须变化，目标 testcase 必须真实执行并通过。应用层在签发 Green 前执行 Service boundary 检查。

成功 Green 保存生产指纹并推进 checkpoint。下一 Req 的 Red 必须基于该 checkpoint。

## Verify

最终 `finalize` 先按固定 Req 顺序调用底层 verify：

- 校验 baseline、Red、Green、日志和报告哈希；
- 校验 checkpoint 前驱链；
- 校验每个已建立 testcase 的方法正文未变化；
- 重跑每个精确测试命令并要求目标 testcase 通过；
- 确认当前生产指纹等于最后 Green。

随后执行 `requirement-contract.json` 中全部验收命令。任何缺链、旧报告、测试弱化、选择器变化、Green 后生产修改、禁用测试或验收命令失败都会使 finalize 失败。

Evidence 不能单独表示流程完成；只有 `tdd-verify.json` 与 `final-verification.json` 都通过时，状态才是 `COMPLETE`。
