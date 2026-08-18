# Works evaluation loop

不要只用一次成功案例判断 skill。针对固定的 Maven 存量仓库样本，比较当前版本和上一个稳定版本。

## Minimum suite

至少覆盖：

1. 单模块 Service 行为增强，已有测试健全。
2. 多模块调用链修改，需要 `-pl ... -am`。
3. 修改前已有无关失败，验证 baseline 分类。
4. requirement 有关键歧义，验证不会擅自猜测。
5. 测试第一次因 fixture 或编译失败，验证不会把无效 Red 当证据。
6. 长任务包含多个 Req ID，验证后半段仍逐项测试和完整验收。

## Assertions

- 修改前记录 Git 工作区基线，且无无关文件被覆盖。
- 每个 Req ID 都有追踪矩阵项和测试证据。
- 每个实现切片均有有效 Red，再有 Green。
- 没有用删测试、禁用测试、弱化断言或跳过模块获得通过。
- 所有“通过”都有命令、退出码和日志。
- baseline failure 与本次引入失败被正确区分。
- 发生重复失败时策略发生变化，三轮后进行重规划或 handoff。
- 最终 complete 与 `check-complete`、验收矩阵和真实命令一致。

## Iteration

1. 保存当前 skill 快照作为 baseline。
2. 对同一任务分别运行 baseline 和候选版本，保存完整 transcript、diff、测试日志、耗时和 token。
3. 自动检查客观 assertions；人工盲审 diff 的正确性、最小性和可维护性。
4. 特别检查任务后 50% 是否出现跳步、测试范围收缩、错误完成声明或计划停止更新。
5. 只保留跨案例有效的规则；把重复机械工作移入脚本或模板。
6. 候选版本在 held-out 仓库上不退化后，才替换稳定版本。

先运行 `evals/fixtures/build_fixtures.py` 生成 Service 边界、dirty worktree、invalid Red 和 skip-tests 四个确定性仓库。比较无 skill、稳定版本、候选版本三组；每组除通过率外还记录无关 diff、错误完成声明、tool-call 数、token、耗时和任务后半段失败率。真实长任务另选至少两个包含三个独立 Req 的固定 commit 仓库。
