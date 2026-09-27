# 战略规划语义路径解析

字段按以下优先级合并：

1. Skill 内置 `path-defaults.yaml`
2. 项目配置 `paths.config_file` 中的 `sw.strategic_planner.paths`
3. 调用方传入的 `paths`

相对路径相对于 `project_root`。计划定义的 template、gate、validator 分别
解析；显式声明但缺失的资源是配置错误，不得静默回退。`{plan_name}` 仅在
计划名通过 kebab-case 和冲突检查后展开。

## 路径边界

- `evidence` 只读，研究结论必须保留来源路径。
- `artifact_targets.plan` 是唯一最终交付物；`draft` 是临时 Markdown 工作记忆。
- 计划生成并交接后删除 draft；不创建 `planning-state.yaml` 或其他 YAML 状态。
- 不写入 `tasks.yaml`、requirements tracker、源代码、测试、配置或分支。
- 依赖 Skill 的内部路径不属于本 Skill 的路径契约。
