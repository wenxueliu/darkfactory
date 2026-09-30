# 任务拆分语义路径解析

`sw-task-decomposer` 接受语义路径，不要求调用方知道 Skill 的物理目录。
字段按以下优先级合并：

1. Skill 内置 `path-defaults.yaml`
2. 项目配置 `paths.config_file` 中的 `sw.task_decomposition.paths`
3. 调用方传入的 `paths`

后者覆盖前者；字段独立合并，数组字段由高优先级整体替换。相对路径均
相对于 `project_root`，占位符 `{requirement_id}` 在输入校验后解析。

## 路径边界

- `evidence` 只读；缺失的需求、设计、gate、registry 或 ADR 记录为
  `NOT_FOUND`，不得自动伪造。
- `manifest`、feature 和 E2E 路径只在 `cross_service` 下要求；
  `single_service` 使用 requirements gate 和唯一服务设计/gate。
- `artifact_targets` 是本 Skill 的写入目标；三个任务产物和 tracker
  必须使用同一个 `requirement_id`。
- 任务拆分可以更新 decomposition tracker，但不得更新全局
  `phases.design`，也不得修改任何设计文档。
- 服务根目录下的代码仓只用于 capability verification；本 Skill 不写入
  服务源代码或测试。
- 外部 Skill 的内部路径不属于本 Skill 的路径契约；能力不可用时按降级协议记录。
