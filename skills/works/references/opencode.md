# OpenCode + MiniMax M2.7 profile

## Runtime

- 使用 OpenCode 原生 `skill` 工具加载 `works`；由 works 按 `skill-routing.md` 按需加载辅助 Skill。
- 使用 OpenCode 原生 read/edit/write/patch/bash 能力执行本 Skill。
- 辅助 Skill 只提供当前阶段的方法；`state.json`、CLI 门禁和完成判定始终由 works 控制。
- 不使用 subagent、`@mention`、外部编排器或人工确认。
- 推荐模型配置为 `opencode-go/minimax-m2.7`；也可通过 `/connect` 连接 MiniMax 后用 `/models` 选择 M2.7。

## M2.7 discipline

- 每次只关注 `status.next_action`、`current_req` 和该 Req 的相关 diff。
- 不在对话中维护第二份计划；磁盘状态是唯一进度。
- 一个 Green 后立即重新运行 `status`，不要总结或询问是否继续。
- 工具调用失败必须依据真实输出改变策略；不要把拟执行命令当成执行结果。
- 长日志保存在 plan 中，只把失败摘要保留在当前上下文。

OpenCode 会按需加载 Skill，并向模型提供 Skill 基目录及 supporting files。所有脚本路径必须相对该基目录解析。
