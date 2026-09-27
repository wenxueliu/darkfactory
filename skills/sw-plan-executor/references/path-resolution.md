# 计划执行语义路径解析

`sw-plan-executor` 使用语义路径作为执行上下文。字段按以下优先级合并：

1. Skill 内置 `path-defaults.yaml`
2. 项目配置 `paths.config_file` 中的 `sw.plan_execution.paths`
3. 调用方传入的 `paths`

后者覆盖前者；相对路径相对于 `project_root`。`{plan_name}` 从
`plan_path` 解析并校验，`{requirement_id}` 必须与计划、tasks 和 tracker
一致。

## 路径边界

- `evidence` 只读，尤其是计划、任务图和设计决策；不因缺失而猜测任务。
- `artifact_targets.plan` 只允许更新既有计划的复选框；不得改写任务意图。
- `notepad_root` 和 `review_root` 是本 Skill 的运行产物目录。
- 服务源代码、测试和 git 操作必须由委托 Agent 完成。
- tracker 只更新 execution 进度；design、merge、test、delivery 的最终状态由
  `sw-controller` 按阶段门禁决定。
