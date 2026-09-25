# 工作区语义路径契约

语义路径把 Skill 需要的“资源角色”和项目实际目录解耦。Skill 只依赖语义名称，不在流程正文中写死 `services/`、`docs/adr/` 等物理路径。

## 配置位置与优先级

项目可以在工作区根目录的 `_context/workspace.yaml` 中维护路径映射：

```text
调用参数
  ↓
{project-root}/_context/workspace.yaml
  ↓
{project-root}/_context/config.yaml → sw.workspace.paths
  ↓
Skill 自身的 path-defaults.yaml
```

项目级 `workspace.yaml` 是工作区结构契约，建议纳入项目版本控制；Skill 内置默认值只用于独立运行时兜底，不应覆盖项目配置。

## 语义路径结构

```yaml
version: 1

paths:
  context_files:
    - CONTEXT.md
  context_maps:
    - CONTEXT-MAP.md
  decision_roots:
    - knowledge/_enterprise/decisions
  source_roots:
    - services
  config_file: _context/config.yaml
  write_targets:
    context_file: CONTEXT.md
    adr_root: knowledge/_enterprise/decisions
  report_root: null
```

| 语义路径 | 必选 | 用途 |
|---|---:|---|
| `context_files` | 是 | 领域术语和上下文定义，可配置多个文件或 glob |
| `context_maps` | 否 | 多上下文之间的关系地图 |
| `decision_roots` | 是 | ADR 或其他架构决策记录目录，可配置多个 |
| `source_roots` | 否 | 代码交叉验证时扫描的源码根目录 |
| `config_file` | 否 | 读取语言等运行配置 |
| `write_targets.context_file` | 否 | 用户确认后允许更新的上下文文件 |
| `write_targets.adr_root` | 否 | 用户确认后允许创建 ADR 的目录 |
| `report_root` | 否 | 报告持久化目录；为空时只输出到对话 |

## 解析规则

- 所有相对路径都相对于 `{project-root}` 解析。
- 路径值统一使用数组；单个文件也写成单元素数组。
- `decision_roots` 多个目录合并读取，并在报告中标记来源。
- `source_roots` 只有执行代码交叉验证时才读取。
- 读取路径和写入路径分离；没有 `write_targets` 时只读，不创建文件。
- `report_root` 不影响质询结果，也不作为工作流状态目录。
- 不把 `workflow_root` 作为 `sw-grill-docs` 的依赖；需求、计划和任务状态由调用方自行管理。

## sw-grill-docs 的最小依赖

```text
必需：context_files + decision_roots
可选：context_maps + source_roots + config_file
写入：仅使用显式 write_targets
报告：默认对话输出
```
