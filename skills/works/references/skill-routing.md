# Skill routing

Works 是唯一 orchestrator。可以通过 OpenCode 原生 `skill` 工具加载下列 Skill，但辅助 Skill 不得修改 works 流程状态、替代 CLI 证据或结束任务。

| Works 阶段 | 可加载 Skill | 用途 | 返回 works 的条件 |
|---|---|---|---|
| `CONTRACT_REQUIRED` / `IMPACT_REQUIRED` | `sw-codebase-explorer` | 定位入口、调用链、Service API、持久层和测试 seam | 找到填写契约或影响图所需的文件证据后立即返回 |
| `CONTRACT_REVIEW_REQUIRED` | `impl-validator` + fresh read-only subagent | 独立检查需求拆分的完整性与可验收性 | 填写 review JSON 后由 works CLI 判定 |
| `READY_FOR_RED` / `READY_FOR_IMPLEMENTATION` | `tdd` | 选择公共行为 seam、检查测试质量、坚持单个纵向 Red→Green | 方法确定后由 works CLI 运行 `red`/`green` |
| 任意失败重试 | `sw-systematic-debugging` | 从真实命令输出定位根因并改变修复策略 | 得到一个可执行假设后返回并重试当前 `next_action` |
| `READY_FOR_ACCEPTANCE` | `sw-verification-before-completion` | 检查完成声明必须由新鲜完整证据支持 | 识别验证命令后仍由 `finalize` 执行契约命令 |
| `IMPLEMENTATION_REVIEW_REQUIRED` | `impl-validator` + fresh read-only subagent | 独立逐 Req 对照实现、diff 和测试证据 | 填写 review JSON 后由 works CLI 判定 |

## 覆盖规则

- Works 的 requirement contract 和 impact map 已经完成 seam 选择；辅助 `tdd` Skill 若要求用户再次确认 seam，视为已有契约确认，不询问用户。
- 辅助 Skill 若要求 commit、发布、等待批准或向用户提问，跳过该步骤并返回 works。开发 subagent 可用，但不能控制状态；审查 subagent 必须全新且只读。
- 辅助 Skill 的文字结论不是证据；只有 works CLI 记录的退出码、JUnit 和 final verification 能推进状态。
- 每次最多加载一个与当前 `next_action` 直接相关的 Skill。完成其方法性工作后重新运行 `works status`。
- 找不到某个辅助 Skill 时直接使用 works 内置 references 和脚本继续，不得停止。
