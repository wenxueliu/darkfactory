# Requirement contract

`<plan>/requirement-contract.json` 是 requirement 到实现与验收的追踪契约。`contract-init` 创建空模板；fresh `contract-author` subagent 读取明确的 requirement 和代码库后返回完整 payload，由 Works 主 agent 一次性写入；`contract-check` 校验结构与覆盖率。

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
      "command": ["mvn", "-DskipTests=false", "-Dmaven.test.skip=false", "-Dtest=ServiceTest#newBehavior", "test"]
    }
  ]
}
```

规则：

- 把 requirement 的每个独立行为完整映射为一个有序 Req；不要合并后遗漏边界条件。
- 验收标准必须是可观察行为，不写“代码已修改”“实现合理”等内部描述。
- `acceptance_commands` 使用 argv 数组，不使用 shell 字符串。
- Maven argv 的首项使用 discovery 返回的平台入口：Windows 为 `mvnw.cmd`，Linux 为 `./mvnw`，没有 wrapper 时为 `mvn`。
- 每个 Req 至少由一条精确定向验收命令覆盖；每条 Maven 命令必须包含唯一 `-Dtest=Class#method`，只执行当前 Req 的新实现行为，禁止模块级、依赖模块或全量存量测试。
- Contract review 阶段的 `acceptance_commands` 是前瞻性测试契约：目标测试类和方法允许尚不存在。此阶段只验证命令结构、行为可测试性和 Req 覆盖，不检查文件/方法存在性，也不执行命令。
- 当前 Req 进入 test checkpoint 后，实际 `--testcase` 和 Maven `-Dtest` 必须匹配该 Req 契约中声明的 selector；repair Req 回溯匹配其原始 Req。测试文件和方法此时必须真实存在并执行通过。
- 测试使用 Mockito 单元测试，禁止 `@SpringBootTest`；第三方与外部依赖直接 mock。
- 契约通过后，严格按固定 Req 顺序执行。失败由模型自主诊断、修改并重试。
