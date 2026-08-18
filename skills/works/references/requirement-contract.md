# Requirement contract

`<plan>/requirement-contract.json` 是 requirement 到实现与验收的追踪契约。`contract-init` 创建空模板；模型读取明确的 requirement 和代码库后一次性补全，`contract-check` 校验结构与覆盖率。

```json
{
  "version": 1,
  "requirement": "/absolute/project/requirement.md",
  "requirements": [
    {
      "id": "REQ-1",
      "statement": "系统必须表现出的单一行为",
      "acceptance_criteria": ["可由自动测试或命令观察的结果"]
    }
  ],
  "acceptance_commands": [
    {
      "id": "module-tests",
      "covers": ["REQ-1"],
      "command": ["./mvnw", "-DskipTests=false", "-Dmaven.test.skip=false", "test"]
    }
  ]
}
```

规则：

- 把 requirement 的每个独立行为完整映射为一个有序 Req；不要合并后遗漏边界条件。
- 验收标准必须是可观察行为，不写“代码已修改”“实现合理”等内部描述。
- `acceptance_commands` 使用 argv 数组，不使用 shell 字符串。
- 每个 Req 至少由一条验收命令覆盖；命令集合应包含受影响模块及依赖模块的完整测试或 package 验证。
- 契约通过后，严格按固定 Req 顺序执行。失败由模型自主诊断、修改并重试。
