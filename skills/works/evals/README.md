# Eval fixture contract

这些 eval 描述的是固定 Maven 仓库场景，不能在空目录直接执行。先用 `fixtures/build_fixtures.py` 生成四个可重置仓库；需要私有真实仓库的场景仍可通过外部 fixture 扩展。

运行评测前，harness 必须为每个 eval 提供并记录：

- 一个独立、可重置到固定 commit 的 Maven 仓库副本；
- 仓库根目录的 `requirement.md`；
- 预置的 Git 工作区改动或 baseline failure（场景要求时）；
- 已知正确的验收命令和隐藏行为断言；
- baseline 与候选 skill 使用完全相同的仓库快照。

把仓库路径加入对应 eval 的 `files`，或在生成的 `eval_metadata.json` 中记录 `fixture_repo`、`fixture_commit` 和 setup script。缺少这些字段时，只能把当前 JSON 当作场景设计，不能宣称已完成可复现 benchmark。
