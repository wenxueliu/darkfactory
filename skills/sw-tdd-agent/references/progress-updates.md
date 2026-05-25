# 进度报告规范 (Progress Updates)

## 核心原则

报告应**主动、简洁、有信息量**。1-2 句话，包含具体细节和 WHY（不只是 WHAT）。

用户不应该"拉取"状态——agent 应该主动"推送"状态。

## 何时报告

### 必须报告 (Must Report)

| 事件 | 格式 | 示例 |
|------|------|------|
| RED 阶段完成 | `RED: {test name}` | `RED: test_create_user_with_valid_email` |
| GREEN 阶段完成 | `GREEN: {test name}` | `GREEN: test_create_user_with_valid_email (添加 email 校验)` |
| REFACTOR 完成 | `REFACTOR complete` | `REFACTOR complete — 提取 validate_email 到独立函数` |
| 一个 Layer 完成 | 1-2句，含计数和下一步 | `Layer 1 UT 全部通过 (8/8 PASS)。开始 Layer 2 API 测试。` |
| 全部工作完成 | 完整报告 (见 Output 规范) | `全部完成。Layer 1: 8/8 PASS, Layer 2: 5/5 PASS。详情见报告。` |
| 遇到阻塞升级 | 升级消息 (见 failure-escalation.md) | `Layer 1 UT 实现中。test_update_user_role 需要了解 RBAC role hierarchy 定义，已搜索代码库未找到。正在启动探索 agent。` |

### 不需要报告 (Do NOT Report)

以下情况**不需要**独立报告，它们是大操作的预期子步骤：

- 读取文件以了解代码结构（EXPLORE 阶段的工具调用）
- 运行单个测试来确认 RED/GREEN 状态（TDD 循环内的正常步骤）
- TODO list 创建/更新（这是管理动作，不是进展）
- `grep` / `glob` 搜索结果（除非结果本身是关键发现）

### 可以报告 (Optional)

以下情况可以简短提及，但不是强制：

- 发现了一个值得注意的副作用（"重构时发现 User 模型缺少 `updated_at` 自动更新，已在本次修复"）
- 完成了一个较大步骤的中间里程碑（"Layer 2: 3/5 API 测试通过"）
- 发现并处理了意料之外的问题（"test_delete_user 触发了外键约束错误，原因是 cascade 配置缺失，已修复"）

## 格式规范

### 好的进度报告 (Good)

```
"Layer 1 UT 全部通过 (12/12 PASS)。开始 Layer 2 API 测试，从 POST /users 端点开始。"

为什么好: 告知具体进展(12/12)、当前状态、下一步是什么、为什么是这个下一步(从POST /users开始)
```

```
"GREEN: test_validate_email_format。最小实现：添加正则校验 `^[\\S]+@[\\S]+\\.[\\S]+$`。"

为什么好: 告知哪个测试、实现内容、具体细节
```

```
"REFACTOR 完成。提取 `normalize_email` 和 `validate_email_domain` 两个辅助函数，消除了重复的 email 处理逻辑。保留所有测试通过。"

为什么好: 告知重构内容、消除了什么坏味道、验证了测试仍然通过
```

### 坏的进度报告 (Bad)

```
"正在写测试。"          ← 没有具体信息：哪个测试？什么阶段？
"搞定了。"              ← 没有信息量：什么搞定了？怎么搞定的？
"代码写好了，测试也过了。" ← 没有细节：多少测试？什么层面？
"我做了一些修改。"       ← 最糟糕：模糊到毫无意义
```

## 语言和风格

- **中文为主** — 项目技术文档和 agent 通信默认使用中文
- **技术术语保留英文** — RED, GREEN, REFACTOR, UT, API, Layer, PASS, FAIL
- **具体优于抽象** — "12/12 PASS" 优于 "全部通过"
- **WHY 优于 WHAT** — "提取 email 校验为独立函数以消除重复" 优于 "修改了 user_service.py"
- **简洁** — 1-2 句。如果超过 3 句，考虑是否应该拆分成多个报告

## 完成报告

全部工作完成后的 Output 报告格式见 SKILL.md 的 Output 章节。

需要包含四个部分：
1. 实现了什么 (What was implemented)
2. 测试结果 (Test results)
3. 验证证据 (Verification evidence)
4. 任何假设或决策 (Assumptions/decisions)
