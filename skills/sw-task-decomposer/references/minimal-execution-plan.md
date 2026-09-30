# 最小执行计划生成规范

`sw-task-decomposer` 在没有收到已通过门禁的战略计划时，生成一份最小执行
计划，作为 `sw-plan-executor` 的标准 `plan_path` 输入。它不是设计文档，
不得新增业务行为、服务边界、API 契约或架构决策。

## 必须包含的九个章节

按以下 section id 生成顶层 Markdown 标题：

1. `tldr` → `## TL;DR`
2. `context` → `## Context`
3. `work_objectives` → `## Work Objectives`
4. `verification_strategy` → `## Verification Strategy (MANDATORY)`
5. `execution_strategy` → `## Execution Strategy`
6. `todos` → `## TODOs`
7. `final_verification` → `## Final Verification Wave`
8. `commit_strategy` → `## Commit Strategy`
9. `success_criteria` → `## Success Criteria`

## 最小内容要求

- `TL;DR` 引用 requirement ID、设计范围、任务数、wave 数和 critical path。
- `Context` 只引用需求、设计、gate、服务注册表和 ADR 的路径；不得复制或
  改写设计决策。
- `Work Objectives` 列出来自需求 AC 和设计交付件的可验证目标。
- `Verification Strategy` 为每个任务绑定已有的 UT/API/E2E 测试设计，并
  声明执行工具和证据位置。
- `Execution Strategy` 按 `tasks.yaml` 的 wave 和依赖输出执行顺序；不重新
  计算或修改 DAG。
- `TODOs` 为每个任务生成一个顶层复选框，任务 ID、服务、wave、依赖、目标
  范围、AC、测试绑定和 QA 场景必须与 `tasks.yaml` 一致。禁止拆成独立的
  “写测试任务”。
- `Final Verification Wave` 引用执行器启用的 reviewer、lint、测试和完成前
  验证，不创建新的产品任务。
- `Commit Strategy` 说明按任务或服务保持可回滚的小提交；不在此 Skill
  执行提交。
- `Success Criteria` 必须是可由 Agent 验证的二元条件，并引用需求、设计
  gate、任务 gate 和测试证据。

## 一致性门禁

生成前后逐项检查：

```text
□ 九个 section id 全部存在
□ 没有未解析的占位符
□ 每个 tasks.yaml 任务在 TODOs 中出现且只出现一次
□ TODO 中的依赖、服务、wave、AC 和测试绑定与 tasks.yaml 一致
□ 单服务计划没有伪造 E2E 任务
□ 跨服务计划的 E2E 任务位于最终实现 wave
□ 计划只引用已通过 gate 的需求/设计制品
□ 计划路径、requirement_id 和任务图可以被 sw-plan-executor 同时解析
```

如果输入的战略计划存在，使用它作为最终计划并只做一致性校验；不要生成
第二份最小计划或覆盖战略计划。
