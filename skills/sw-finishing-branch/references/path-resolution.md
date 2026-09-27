# 分支收尾语义路径解析

`sw-finishing-branch` 的路径优先级为：

1. Skill 内置 `path-defaults.yaml`
2. 项目配置 `paths.config_file` 中的 `sw.finishing_branch.paths`
3. 调用方传入的 `paths`

相对路径相对于 `project_root`；`{plan_name}` 和 `{requirement_id}` 必须从
输入或已验证的计划/tracker 中解析，不能用模糊 glob 代替。

## 路径边界

- execution、plan、task 和 registry 是只读证据。
- `merge_report` 是本 Skill 唯一的默认文档写入目标。
- git 的 branch/worktree 操作必须先解析到明确目标；禁止对 workspace 根目录
  或未确认的 glob 执行删除。
- tracker 的 merge 状态更新应在实际操作完成后进行，并保留命令结果。
