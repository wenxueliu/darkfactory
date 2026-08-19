# Skill routing

Works 是唯一 orchestrator。审查门需要一个辅助 Skill（`impl-validator`，全新只读 subagent）；其余阶段的方法论由内置 references 提供，不加载外部 Skill。

`status.next_action` 给出两个提示字段：

- `skill`：仅审查门非空，值为 `impl-validator`，用 OpenCode 原生 `skill` 工具加载。
- `reference`：其余阶段非空，值为内置 reference 路径，直接读取该文件后照做。

| Works 阶段 | `skill` / `reference` | 用途 |
|---|---|---|
| `CONTRACT_REQUIRED` / `IMPACT_REQUIRED` | `references/exploration.md` | 定位入口、调用链、Service API、持久层、测试 seam |
| `CONTRACT_REVIEW_REQUIRED` | `impl-validator` + fresh read-only subagent | 独立检查需求拆分，填 review JSON |
| `READY_FOR_RED` / `READY_FOR_IMPLEMENTATION` | `references/tdd-seams.md` | 选 seam、查测试质量、单纵向 Red→Green |
| 任意失败重试 | `references/diagnosis.md` | 从真实命令输出定位根因、改策略重试 |
| `READY_FOR_ACCEPTANCE` | `references/verification.md` | 完成声明必须有新鲜完整证据 |
| `IMPLEMENTATION_REVIEW_REQUIRED` | `impl-validator` + fresh read-only subagent | 独立对照实现、diff 和测试证据，填 review JSON |

## 规则

- `skill` 非空 → 加载 `impl-validator`，行为见 [Independent reviews](reviews.md)；只填 review JSON，不改代码/契约/状态。
- `reference` 非空 → 读该内置文件，按其方法论完成当前 `next_action`，然后立即重新运行 `works status`。
- 全程无人：不向用户提问、不请求确认、不 commit、不发布、不等批准。
- 辅助方法的文字结论不是证据；只有 works CLI 记录的退出码、JUnit 和 final verification 能推进状态。
- 每次只关注一个 `next_action`；完成后回到 works 状态机，不建立第二套计划。
