# OpenCode + MiniMax M2.7 profile

## Runtime

- 使用 OpenCode 原生 `skill` 工具加载 `works`；由 works 按 `skill-routing.md` 加载 `impl-validator`（审查门）或读内置 reference。
- 使用 OpenCode 原生 read/edit/write/patch/bash 能力执行本 Skill。
- 辅助 Skill 只提供当前阶段的方法；`state.json`、CLI 门禁和完成判定始终由 works 控制。
- 主 Agent直接编写 requirement contract。只有状态机判定为高风险时，才使用全新上下文的只读 reviewer。始终不使用人工确认。
- 推荐模型配置为 `opencode-go/minimax-m2.7`；也可通过 `/connect` 连接 MiniMax 后用 `/models` 选择 M2.7。

## M2.7 discipline

- 每次只关注 `status.next_action`、`current_req` 和该 Req 的相关 diff。
- 不在对话中维护第二份计划；磁盘状态是唯一进度。
- 一个 Req 的 test checkpoint 后立即重新运行 `status`，不要总结或询问是否继续。
- 工具调用失败必须依据真实输出改变策略；不要把拟执行命令当成执行结果。
- 长日志保存在 plan 中，只把失败摘要保留在当前上下文。

OpenCode 会按需加载 Skill，并向模型提供 Skill 基目录及 supporting files。所有脚本路径必须相对该基目录解析。

## Platform entry

- Windows 使用 `py -3 <skill-dir>/scripts/works.py`；如果 Python Launcher 不存在，使用 `python`。
- Linux 使用 `python3 <skill-dir>/scripts/works.py`；如果不存在，使用 `python`。
- Windows Maven wrapper 使用 `mvnw.cmd`，Linux 使用 `./mvnw`；没有 wrapper 时使用 `mvn`。
- 始终把 Maven 命令保存为 argv 数组，不依赖 shell 语法。
