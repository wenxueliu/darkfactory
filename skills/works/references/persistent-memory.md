# Persistent memory

Works 借鉴 file-based planning 的磁盘记忆，但不创建第二套计划状态。

```text
state.json       唯一流程权威，含 attempts 和结构化 next_action
activity.jsonl   每个动作的 passed / failed / blocked 记录
findings.jsonl   代码探索事实
decisions.jsonl  关键实现选择
summaries/       contract、implementation、test、finalize 等阶段小摘要
evidence/        测试和验收事实
```

## 恢复

```text
<python> <skill-dir>/scripts/works.py --project <project> recover
```

返回当前状态、唯一 next action、最后活动、最后失败和记忆文件路径。恢复后直接执行 next action，不重新规划全部任务。

## 记录

```text
<python> <skill-dir>/scripts/works.py --project <project> note -- --kind finding --text "UserController delegates to UserService"
<python> <skill-dir>/scripts/works.py --project <project> note -- --kind decision --text "Extend UserService instead of injecting UserMapper" --req REQ-1
```

只记录会影响后续执行的事实和选择。普通工具输出留在日志中，不复制成长篇笔记。

## 失败策略

失败会写入 `activity.jsonl` 和 `state.json.attempts`。如果命令及工作区与上次失败完全相同，CLI 返回 `E901_REPEAT_FAILURE`。修改测试、实现、fixture、命令或诊断策略后再重试。
