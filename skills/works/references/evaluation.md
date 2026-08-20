# Works evaluation

在固定 Maven 仓库上用 OpenCode + MiniMax M2.7 从 `/works` 开始运行完整任务，保存 transcript、diff、状态和证据。

最低案例：

1. 单模块、一个 Req。
2. 多模块、三个 Req、需要 `-pl ... -am`。
3. 首次 test 为 fixture/编译错误，模型必须修正后重新建立有效测试证据。
4. 多个行为共享测试类，后半段仍完成全部 Req。
5. Controller 需求必须通过既有 Service API 实现。

自动断言：

- requirement-contract 中的 Req 覆盖 requirement 的全部独立行为。
- 每个 Req 都有独立 implementation、test 和最终 replay。
- 每条验收标准至少被一条 acceptance command 覆盖。
- `COMPLETE` 前全部契约命令真实退出 0。
- 全程没有用户问题或人工确认；主 Agent编写契约，只有状态机声明的风险审查可使用 fresh 只读 reviewer，subagent 不得控制状态。
- 每轮遵循唯一 `next_action`，后 50% 不缩小测试或遗漏 Req。

比较候选版本时记录完成率、错误完成率、遗漏 Req 数、工具调用数、token、耗时和后半段失败率。只有 held-out 仓库不退化时才替换稳定版本。
