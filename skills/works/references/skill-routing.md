# Skill routing

Works 是唯一 orchestrator。普通阶段使用内置 reference；只有风险审查加载 `impl-validator` 并启动 fresh 只读 subagent。

| 阶段 | 方法 |
|---|---|
| `SETUP_REQUIRED` | `preflight`：发现环境、冻结 baseline，不修改 Git 历史 |
| `CONTRACT_REQUIRED` | 主 Agent 读取 `exploration.md`、`requirement-contract.md` 和仓库，填写包含实现决策的契约 |
| `CONTRACT_REVIEW_REQUIRED` | 仅高风险：fresh `impl-validator` 审查契约 |
| implementation/test | 读取 `code-first.md` |
| acceptance | 读取 `verification.md` |
| `IMPLEMENTATION_REVIEW_REQUIRED` | 仅高风险：fresh `impl-validator` 审查最终实现 |

完成一个动作后立即返回 `status`。reference 或 reviewer 的文字结论不能替代 CLI、JUnit 和 final verification 证据。
