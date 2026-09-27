# 集成测试语义路径解析

字段按以下优先级合并：

1. Skill 内置 `path-defaults.yaml`
2. 项目配置 `paths.config_file` 中的 `sw.integration_test.paths`
3. 调用方传入的 `paths`

相对路径相对于 `project_root`。`{requirement_id}` 先经过 manifest 校验后
再展开；不得使用其他需求的 API 产物或测试结果。

## 路径边界

- `manifest`、设计测试产物、集成计划和环境配置是只读输入。
- `test_results`、JUnit 报告和允许的 runner 产物是写入目标；不得写入生产
  环境或修改 API collection 以掩盖失败。
- runner 必须从 manifest 发现所有 Stage 2 服务；不能用固定服务名列表替代。
- tracker 只写 integration 子状态和证据，不直接关闭全局 test phase。
