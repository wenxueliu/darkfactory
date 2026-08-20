# 失败诊断（无人化）

`implement`/`test`/`finalize` 失败时，从真实命令输出定位根因、改策略重试。这是内置 reference，不加载外部 `sw-systematic-debugging` Skill。

## 方法

1. **读真实输出**：CLI 返回的 `exit` + `output` + `evidence`，不凭猜测、不把拟执行的命令当成结果。
2. **分类失败**：先看错误码，定位失败类型。

| 错误码 | 含义 | 修正方向 |
|---|---|---|
| `E203_TESTS_SKIPPED` | 测试被跳过 | 补 `-DskipTests=false -Dmaven.test.skip=false` 等覆盖 |
| `E314_INVALID_IMPLEMENTATION` | 实现 checkpoint 无有效生产变更 | 完成当前 Req 的最小生产修改后重试 |
| `E315_INVALID_TEST` | 目标测试未真实执行并通过 | 修正实现、测试、fixture 或命令后重试 |
| `E316_PRODUCTION_AFTER_IMPLEMENTATION` | 实现 checkpoint 后生产代码又变化 | 重新建立 repair Req 的实现与测试证据链 |
| `E510_BOUNDARY_VIOLATION` | 入口直连持久层 | 复用/扩展 Service API |

3. **单变量假设**：一次只改一个东西，验证一个假设（编译？fixture？断言？环境？）。
4. **改策略后重试**：根据真实错误调整实现、测试或环境；同一 Req 第三次连续定向测试失败后由状态机保存证据并标记 `SKIPPED`。

## 无人化硬约束

- 不升级到人工、不向用户提问、没有「human partner」概念。
- 穷尽假设仍无进展：用 `note -- --kind finding` 记录事实，回到 works 状态机，让 `next_action` 指引下一步；不得停止等待外部输入。
- 根因未定不写修复；先用最小可执行假设验证，再实现。
