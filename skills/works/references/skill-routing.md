# Skill routing

Works 是唯一 orchestrator。各阶段只使用内置 reference 和确定性 CLI 门禁，不加载独立 reviewer。

| 阶段 | 方法 |
|---|---|
| `SETUP_REQUIRED` | `preflight`：发现环境、冻结 baseline，不修改 Git 历史 |
| `CONTRACT_REQUIRED` | 主 Agent 读取 `exploration.md`、`requirement-contract.md` 和仓库，填写包含实现决策的契约 |
| implementation/test | 读取 `code-first.md` |
| acceptance | 读取 `verification.md` |

完成一个动作后直接使用该响应中的刷新状态和 `next_action`；仅在恢复、响应丢失或人工检查时调用 `status`。reference 的文字结论不能替代 CLI、JUnit 和 final verification 证据。
