# 价值判断语义路径解析

`sw-value-judgment` 不把项目物理目录写死为调用契约。调用方可以通过 `paths`
覆盖任意默认路径；未覆盖字段从项目配置或本 Skill 的 `path-defaults.yaml`
获取。所有相对路径都相对于 `project_root` 解析，路径分隔符使用 `/`。

## 优先级

同一字段按以下顺序覆盖，后者优先：

1. Skill 内置 `path-defaults.yaml`
2. 项目配置（`_context/config.yaml` 中的 `sw.value_judgment.paths`）
3. 调用方输入的 `paths`

路径字段独立合并；数组字段在高优先级声明时整体替换，不隐式拼接。

## 读写边界

- `evidence` 和 `requirement_document` 是只读输入；缺失时记录 `NOT_FOUND`，不创建文件。
- `artifact_targets` 是写入目标；只有评估达到对应结果并通过用户/阶段门禁后才写入。
- 需求级评估和 ROI 必须默认写入 `knowledge/requirements/{requirement_id}/`，与需求文档共享同一需求目录。
- `priority_ranking` 面向多个需求，默认写入 `knowledge/value-assessment/`，不与单个需求混淆。
- `tracker` 是共享状态；写入时必须保留其他需求条目和派生状态规则。

## 默认目标

```yaml
artifact_targets:
  requirement_document: knowledge/requirements/{requirement_id}/requirement.md
  value_assessment: knowledge/requirements/{requirement_id}/value-assessment.md
  roi: knowledge/requirements/{requirement_id}/roi.md
  priority_ranking: knowledge/value-assessment/priority-ranking-{date}.md
  tracker: knowledge/requirements-tracker.yaml
```
