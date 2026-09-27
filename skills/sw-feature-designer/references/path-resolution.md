# 特性设计语义路径解析

`sw-feature-designer` 使用语义路径作为输入契约，不要求调用方依赖本
Skill 的物理目录。字段按以下优先级合并：

1. Skill 内置 `path-defaults.yaml`
2. 项目配置 `paths.config_file` 中的 `sw.feature_design.paths`
3. 调用方传入的 `paths`

后者覆盖前者。字段独立合并；数组字段一旦在高优先级声明则整体替换，
不隐式拼接。相对路径均相对于 `project_root`，使用 `/` 作为分隔符。

## 路径边界

- `definition_roots` 只用于解析 `feature-design/{variant}` 的模板、门禁和验证器。
- `evidence` 是只读输入；缺失文件或目录记录 `NOT_FOUND`，不自动创建。
- `artifact_targets` 是本 Skill 的写入目标；本流程在 `design_dir` 下创建
  `feature-design.md`、`feature-design-gate.md`、`manifest.yaml`，以及成功执行
  知识库预查询时创建 `pre-query.md`。Stage 2/3 分别使用同一目录下的
  `services/` 和 `e2e/` 子目录。
- `tracker` 是跨阶段共享状态，只有通过设计门禁后才更新 `phases.design`。
- `pre_query` 只有在 `sw-knowledge-agent` 成功返回时写入；失败时记录 `SKIPPED`，不创建伪造的报告。
- `adr_root` 只表示允许的 ADR 目标位置；没有用户确认和显式写入授权时不创建 ADR。
- 外部 Skill 的内部路径不属于本 Skill 的 `paths`，外部能力不可用时按降级协议继续。

## 设计产物目录

每个需求拥有独立目录，目录内的 `manifest.yaml` 是下游 Agent 的发现入口：

```text
knowledge/designs/{requirement_id}/
├── manifest.yaml
├── feature-design.md
├── feature-design-gate.md
├── pre-query.md
├── services/
└── e2e/
    └── design.md
```

## 定义资源解析

模板、gate、validator 三类资源分别解析：先查当前层的精确 variant，
再查当前层的 `default`，然后进入下一层。manifest 显式声明但资源文件
缺失时是配置错误，必须返回 `BLOCKED`，不能静默回退。
