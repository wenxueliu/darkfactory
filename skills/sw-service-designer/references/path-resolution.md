# 服务设计语义路径解析

`sw-service-designer` 使用语义路径作为输入契约，不要求调用方依赖本
Skill 的物理目录。字段按以下优先级合并：

1. Skill 内置 `path-defaults.yaml`
2. 项目配置 `paths.config_file` 中的 `sw.service_design.paths`
3. 调用方传入的 `paths`

后者覆盖前者。字段独立合并；数组字段一旦在高优先级声明则整体替换，
不隐式拼接。相对路径均相对于 `project_root`，使用 `/` 作为分隔符。

## 路径边界

- `definition_roots` 只用于解析 `service-design/{service_type}` 的模板、门禁和验证器。
- `evidence` 是只读输入；缺失文件或目录记录 `NOT_FOUND`，不自动创建。
- `artifact_targets` 是本 Skill 的写入目标；API 测试 JSON、环境文件、服务设计和门禁报告必须使用解析后的目标。
- `requirement_document` 和 `requirements_gate_report` 是
  `single_service` 的只读上游证据。
- `bundle_manifest` 是 `cross_service_detail` 的 Stage 1 产物共享索引；只有本服务通过 Gate 后才更新本服务条目。`single_service` 不要求该索引，也不创建它。
- `tracker` 只读；全局 `phases.design` 由 `sw-controller` 在所有服务和 E2E 阶段完成后更新。
- 外部 Skill 的内部路径不属于本 Skill 的 `paths`，外部能力不可用时按降级协议继续。

## 定义资源解析

模板、gate、validator 三类资源分别解析：先查当前服务类型，再查当前
层的 `default`，然后进入下一层。manifest 显式声明但资源文件缺失时是
配置错误，必须返回 `BLOCKED`，不能静默回退。
