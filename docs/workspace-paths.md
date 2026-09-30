# 工作区语义路径契约

语义路径把 Skill 需要的“资源角色”和项目实际目录解耦。Skill 只依赖语义名称，不在流程正文中写死 `services/`、`docs/adr/` 等物理路径。

## 默认值与覆盖

默认安装不创建额外的工作区路径配置。所有共享知识和流程产物默认位于
`{project-root}/knowledge/`，配置文件仅位于 `_context/`。Skill 使用自身的
`path-defaults.yaml`；调用方如有必要，可通过输入参数显式覆盖语义路径：

```text
调用参数
  ↓
Skill 自身的 path-defaults.yaml
```

不需要创建 `_context/workspace.yaml`，也不需要在 `_context/config.yaml` 中添加
`sw.workspace.paths`。只有明确传入 `paths` 时，当前调用才使用临时覆盖值。

## 语义路径结构

```yaml
version: 1

paths:
  context_files:
    - knowledge/CONTEXT.md
  context_maps:
    - knowledge/CONTEXT-MAP.md
  decision_roots:
    - knowledge/decisions
  source_roots:
    - services
  config_file: _context/config.yaml
  write_targets:
    context_file: knowledge/CONTEXT.md
    adr_root: knowledge/decisions
  report_root: null
```

| 语义路径 | 必选 | 用途 |
|---|---:|---|
| `context_files` | 核心 | 领域术语和上下文定义，可配置多个文件或 glob |
| `context_maps` | 否 | 多上下文之间的关系地图 |
| `decision_roots` | 核心 | ADR 或其他架构决策记录目录，可配置多个 |
| `source_roots` | 否 | 代码交叉验证时扫描的源码根目录 |
| `config_file` | 否 | 读取语言等运行配置 |
| `write_targets.context_file` | 否 | 用户确认后允许更新的上下文文件 |
| `write_targets.adr_root` | 否 | 用户确认后允许创建 ADR 的目录 |
| `report_root` | 否 | 报告持久化目录；为空时只输出到对话 |

## 解析规则

- 所有相对路径都相对于 `{project-root}` 解析。
- 路径值统一使用数组；单个文件也写成单元素数组。高优先级配置声明数组时整体替换低优先级数组，不隐式拼接。
- `decision_roots` 多个目录合并读取，并在报告中标记来源。
- `source_roots` 只有执行代码交叉验证时才读取。
- 读取路径和写入路径分离；没有 `write_targets` 时只读，不创建文件。
- `report_root` 不影响质询结果，也不作为工作流状态目录；核心证据缺失时报告不得伪装为完整 PASS。
- 不把 `workflow_root` 作为 `sw-grill-docs` 的依赖；需求、计划和任务状态由调用方自行管理。

## sw-grill-docs 的最小依赖

```text
核心证据角色：context_files + decision_roots（实际文件缺失时仍可运行，对应检查标记为未发现）
可选：context_maps + source_roots + config_file
写入：仅使用显式 write_targets
报告：默认对话输出
```
