# E2E 设计语义路径解析

`sw-e2e-designer` 使用语义路径作为输入契约，不要求调用方依赖本 Skill
的物理目录。字段按以下优先级合并：

1. Skill 内置 `path-defaults.yaml`
2. 项目配置 `paths.config_file` 中的 `sw.e2e_design.paths`
3. 调用方传入的 `paths`

后者覆盖前者。字段独立合并；数组字段由高优先级整体替换，不隐式拼接。
相对路径均相对于 `project_root`，使用 `/` 作为分隔符。

## 路径边界

- `definition_roots` 只用于解析 `e2e/{variant}` 的模板、门禁和验证器。
- `evidence` 是只读输入；缺失文件或目录记录 `NOT_FOUND`，不自动创建。
- `artifact_targets` 是本 Skill 的写入目标；设计、门禁报告和预查询必须使用解析后的目标。
- `bundle_manifest` 是 Stage 1 产物的共享索引；只有 E2E Gate 通过后才更新 E2E 条目和 bundle 状态。
- `tracker` 由 `sw-controller` 独占写入；本 Skill 不得更新全局 `phases.design`。
- 外部 Skill 的内部路径不属于本 Skill 的 `paths`，外部能力不可用时按降级协议继续。

## 设计产物目录

```text
knowledge/designs/{requirement_id}/
├── manifest.yaml
├── feature-design.md
├── feature-design-gate.md
├── services/{service_id}/design.md
└── e2e/
    ├── design.md
    ├── gate.md
    └── pre-query.md
```

## 定义资源解析

模板、gate、validator 三类资源分别解析：先查当前 variant，再查当前层
的 `default`，然后进入下一层。manifest 显式声明但资源文件缺失时是配置
错误，必须返回 `BLOCKED`，不能静默回退。
