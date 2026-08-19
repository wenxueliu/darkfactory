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
      "command": ["mvn", "-pl", "user-service", "-Dtest=UserServiceWorksTest#createsUser", "-DskipTests=false", "-Dmaven.test.skip=false", "test"]
    }
  ]
}
```

规则：

- 把 requirement 的每个独立行为完整映射为一个有序 Req；不要合并后遗漏边界条件。
- Req ID 按自然顺序排列，例如 `REQ-2` 必须位于 `REQ-10` 之前。
- 验收标准必须是可观察行为，不写“代码已修改”“实现合理”等内部描述。
- `acceptance_commands` 使用 argv 数组，不使用 shell 字符串。
- Maven argv 的首项使用 discovery 返回的平台入口：Windows 为 `mvnw.cmd`，Linux 为 `./mvnw`，没有 wrapper 时为 `mvn`。
- 每个 Req 至少由一条精确命令覆盖；命令必须包含 `-pl <module>` 和 `-Dtest=<Class#method>`，只能运行 `test`，禁止 `verify`、`package` 和无 selector 的全量测试。
- 每个模块任务返回的 `test_command` 必须精确匹配一条覆盖该 Req 的契约命令。
- 契约通过后继续按模块 DAG/Wave 执行；`finalize` 重放全部契约命令并确认精确 testcase 实际执行，最终只声明修改代码的定向测试覆盖，不声明完整回归。
