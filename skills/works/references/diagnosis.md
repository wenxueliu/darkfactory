# 失败诊断（无人化）

`red`/`green`/`finalize` 失败时，从真实命令输出定位根因、改策略重试。这是内置 reference，不加载外部 `sw-systematic-debugging` Skill。

## 方法

1. **读真实输出**：CLI 返回的 `exit` + `output` + `evidence`，不凭猜测、不把拟执行的命令当成结果。
2. **分类失败**：先看错误码，定位失败类型。

| 错误码 | 含义 | 修正方向 |
|---|---|---|
| `E203_TESTS_SKIPPED` | 测试被跳过 | 补 `-DskipTests=false -Dmaven.test.skip=false` 等覆盖 |
| `E312_PRODUCTION_BEFORE_RED` | Red 前生产已变 | 回退生产改动，先立 Red |
| `E510_BOUNDARY_VIOLATION` | 入口直连持久层 | 复用/扩展 Service API |
| `E311`/`E313` | Red/Green 无效 | 修正断言、fixture 或编译错后重试 |
| `E901_REPEAT_FAILURE` | 完全相同失败重放 | 必须改变工作区或策略 |

3. **单变量假设**：一次只改一个东西，验证一个假设（编译？fixture？断言？环境？）。
4. **改策略后重试**：CLI 会拒绝完全相同失败的重放，所以每次重试前都要有真实变化。

## 无人化硬约束

- 不升级到人工、不向用户提问、没有「human partner」概念。
- 穷尽假设仍无进展：用 `note -- --kind finding` 记录事实，回到 works 状态机，让 `next_action` 指引下一步；不得停止等待外部输入。
- 根因未定不写修复；先用最小可执行假设验证，再实现。
