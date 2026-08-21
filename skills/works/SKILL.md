---
name: works
description: 按可定制的多步骤流程持续执行开发、测试、审查或修复任务。用户要求使用 /works、选择不同流程、为步骤配置 do/check 提示、失败重试或成功/失败跳转时使用。运行时只维护一个 state.json。
---

# Works

选择流程并初始化：

```text
python <skill-dir>/scripts/works.py --project <project> init
python <skill-dir>/scripts/works.py --project <project> init --workflow <workflow.json>
```

不传 `--workflow` 时使用 `assets/workflows/development.json`。初始化后，完整流程定义会写入 `.works/state.json`；它是唯一运行时状态，不创建第二套计划、日志或证据文件。

## 执行

1. 读取响应的 `next_action.do` 并完成工作。
2. 按 `next_action.check` 执行校验。
3. 优先用真实命令提交校验：

```text
python <skill-dir>/scripts/works.py --project . check -- <command> <args...>
```

无法用命令表达的审查，必须附具体证据：

```text
python <skill-dir>/scripts/works.py --project . check --result passed --evidence "检查内容和结论"
python <skill-dir>/scripts/works.py --project . check --result failed --evidence "失败原因"
```

校验成功进入 `on_success`；值为 `null` 时完成。校验失败先留在当前步骤重试；失败次数超过 `on_failure.retries` 后跳到 `on_failure.goto`。动作响应已经包含刷新后的下一步；仅在中断恢复时运行 `status`。

## 流程格式

```json
{
  "name": "development-test-fix",
  "initial_step": "development",
  "steps": [
    {
      "id": "development",
      "do": "完成最小代码修改",
      "check": "检查实现是否满足需求",
      "on_success": "test",
      "on_failure": {"retries": 1, "goto": "development"}
    },
    {
      "id": "test",
      "do": "运行真实测试",
      "check": "根据测试退出码判断",
      "on_success": null,
      "on_failure": {"retries": 0, "goto": "development"}
    }
  ]
}
```

每个步骤必须有唯一 `id`、非空 `do/check`。所有跳转目标必须存在。`retries: 0` 表示第一次失败立即跳转；回退可以指向前序步骤、自身或任意其他步骤。
