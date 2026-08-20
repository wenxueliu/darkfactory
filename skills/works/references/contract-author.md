# Contract author handoff

`contract-init` 后必须通过 OpenCode Task 工具启动已注册的 `contract-author` subagent（项目定义：`.opencode/agents/contract-author.md`）。作者负责把 requirement 和仓库事实转换为完整契约，但不写文件、不调用 Works CLI、不推进状态。

## 输入

只向作者提供：

- `requirement.md` 的绝对路径；
- 项目根目录；
- `requirement-contract.json` 空模板；
- discovery 返回的 Maven 入口；
- 本文件以及 [Requirement contract](requirement-contract.md) 和 [Exploration](exploration.md) 的规则。

作者自行读取完整 requirement 和所需仓库文件，定位模块、入口、调用链、现有测试与 Maven 配置。不要提供主 Agent 的预判或预先拆好的 Req。

## 输出

作者响应必须只包含一个 JSON 代码块，内容是完整 `contract_payload`：

```json
{
  "version": 1,
  "requirement": "/absolute/path/to/requirement.md",
  "requirements": [],
  "acceptance_commands": []
}
```

禁止返回 patch、文件写入命令、状态结论或省略字段。每个 requirement 行为必须映射为有序 Req，每个 Req 必须有可观察验收标准并由真实 Maven test/verify/package 命令覆盖。

## Works 主 Agent职责

1. 调用 Task 时将 subagent type 明确设为 `contract-author`，prompt 列出上述输入的绝对路径，并要求读取这些文件后返回 payload。
2. 同步等待 Task 完成，从 Task result 获取作者响应；在收到非空结果前禁止写契约、运行 `contract-check` 或推进状态。启动 child session 不等于收到结果。
3. 若 Task 失败、返回为空、被中断或响应没有且仅有一个 JSON 对象，废弃该 child session，启动新的 fresh `contract-author`；不得由主 Agent代写 payload。
4. 校验响应只有一个 JSON 对象，且顶层字段严格为 `version`、`requirement`、`requirements`、`acceptance_commands`。
5. 确认 `version == 1`，`requirement` 与空模板完全一致；不得自行补全缺失行为或修改作者语义。
6. 校验通过后，用该对象整体覆盖已初始化的 `requirement-contract.json`。
7. 立即运行 `contract-check`。失败时保留 CLI 证据，启动新的 fresh author，并提供 requirement、仓库和失败 violations；不要让原作者在旧上下文中自我修补。
8. `contract-check` 通过后，仍须启动另一个全新上下文的 contract reviewer。作者不得充当 reviewer。

Task prompt 最少包含：

```text
Read and follow <works-skill>/references/contract-author.md,
<works-skill>/references/requirement-contract.md, and
<works-skill>/references/exploration.md.
Project root: <absolute-project-root>
Requirement: <absolute-requirement.md>
Empty contract template: <absolute-requirement-contract.json>
Maven command: <discovery.maven_command>
Return exactly one fenced contract_payload JSON object to the parent task result.
```
