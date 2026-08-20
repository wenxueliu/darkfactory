# Skill routing

Works 是唯一 orchestrator。审查门需要一个辅助 Skill（`impl-validator`，全新只读 subagent）；其余阶段的方法论由内置 references 提供，不加载外部 Skill。

`status.next_action` 给出三个提示字段：

- `skill`：仅审查门非空，值为 `impl-validator`，用 OpenCode 原生 `skill` 工具加载。
- `subagent`：需要 fresh 独立上下文时非空；契约编写使用内置 `general` 并加载 `references/contract-author.md`，两类审查分别为对应 reviewer。
- `reference`：其余阶段非空，值为内置 reference 路径，直接读取该文件后照做。

| Works 阶段 | `skill` / `reference` | 用途 |
|---|---|---|
| `CONTRACT_REQUIRED`（模板不存在） | CLI `contract-init` | 创建空契约模板 |
| `CONTRACT_REQUIRED`（模板已存在） | fresh `general` + `references/contract-author.md` | 按 reference 充当只读 contract-author 并返回完整 payload，由 Works 写入后执行 `contract-check` |
| `IMPACT_REQUIRED` | `references/exploration.md` | 定位入口、调用链、Service API、持久层、测试 seam |
| `CONTRACT_REVIEW_REQUIRED` | `impl-validator` + fresh read-only subagent | 独立检查需求拆分，返回 payload，由 Works 写 review JSON |
| `READY_FOR_IMPLEMENTATION` / `READY_FOR_TEST` | `references/code-first.md` | 最小实现、冻结 checkpoint、运行目标行为测试 |
| 任意失败重试 | `references/diagnosis.md` | 从真实命令输出定位根因、改策略重试 |
| `READY_FOR_ACCEPTANCE` | `references/verification.md` | 完成声明必须有新鲜完整证据 |
| `IMPLEMENTATION_REVIEW_REQUIRED` | `impl-validator` + fresh read-only subagent | 独立对照实现、diff 和测试证据，返回 payload，由 Works 写 review JSON |

## 规则

- `skill` 非空 → 加载 `impl-validator`，行为见 [Independent reviews](reviews.md)；只读 reviewer 只返回 report + `review_payload`，Works 主 agent 校验后落盘 review JSON，两者都不改代码/契约/状态。
- `subagent == general` 且 `reference == references/contract-author.md` → 先读取该 reference，再把其完整规则和动态路径放进 Task prompt，调用 fresh `general` 并同步等待结果；它只向 Task result 返回 `contract_payload`，Works 主 agent 是唯一契约写入者。没有收到非空 payload 时禁止继续。
- `reference` 非空 → 读该内置文件，按其方法论完成当前 `next_action`，然后立即重新运行 `works status`。
- 全程无人：不向用户提问、不请求确认、不 commit、不发布、不等批准。
- 辅助方法的文字结论不是证据；只有 works CLI 记录的退出码、JUnit 和 final verification 能推进状态。
- 每次只关注一个 `next_action`；完成后回到 works 状态机，不建立第二套计划。
