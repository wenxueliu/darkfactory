# 浏览器测试语义路径解析

字段按以下优先级合并：

1. Skill 内置 `path-defaults.yaml`
2. 项目配置 `paths.config_file` 中的 `sw.browser_test.paths`
3. 调用方传入的 `paths`

相对路径相对于 `project_root`；`{requirement_id}` 只在 E2E manifest 和 gate
校验通过后展开。

## 路径边界

- E2E 设计、gate、浏览器计划和 tracker 是只读输入。
- `test_root` 下的会话日志、报告、截图、网络和视觉证据是运行产物；失败
  证据不得被覆盖或省略。
- `result_file` 只记录浏览器子状态和证据，不直接关闭全局 test phase。
- auth、cookie、token 等敏感值不得写入任何报告或日志。
