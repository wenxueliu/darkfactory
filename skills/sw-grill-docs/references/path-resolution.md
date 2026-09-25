# 语义路径解析规则

`sw-grill-docs` 只依赖资源角色，不把某个项目的物理目录当成固定契约。

## 来源优先级

按以下顺序读取路径配置，后加载的配置只覆盖已声明的同名字段：

1. Skill 内置的 `path-defaults.yaml`
2. `{project-root}/_context/config.yaml` 中的 `sw.workspace.paths`
3. `{project-root}/_context/workspace.yaml`
4. 本次调用显式传入的路径参数

每个字段独立合并；调用方没有覆盖的字段继续使用更低优先级的值。相对路径统一相对于 `{project-root}` 解析，路径分隔符使用 `/`。

## 资源角色

- `context_files`：领域术语和上下文定义。
- `context_maps`：上下文之间的关系地图；地图中的相对链接相对于地图文件解析。
- `decision_roots`：ADR 或其他架构决策记录目录；多个目录合并读取，并在报告中标明来源。
- `source_roots`：代码交叉验证的源码根目录；只有执行 Phase 4 时读取。
- `config_file`：通信语言等运行配置，可缺省。

## 读写边界

- `context_files`、`context_maps`、`decision_roots`、`source_roots` 和 `config_file` 是读取路径。
- `write_targets.context_file` 和 `write_targets.adr_root` 是写入目标，必须显式配置。
- 没有 `write_targets` 时，质询只输出报告和变更提议，不创建目录、不修改 CONTEXT、不创建 ADR。
- 用户确认只授权已确认的具体变更；不能因为存在写入目标就批量改写文档。
- `report_root` 为空时报告只输出到对话；它不是工作流状态目录。

## 缺失和冲突

- 缺少可选路径只跳过对应检查，不生成“路径缺失”问题。
- 必需角色缺失时，在报告中说明未执行的检查范围，不把它伪装成目标文档冲突。
- 同一语义角色由多个来源映射到不同路径时，保留全部来源并报告冲突；不要静默选择一个。
- 不把 `workflow_root`、调用方私有状态或某个 Skill 的内部目录作为本 Skill 的隐式依赖。
