# MiniMax M2.7 field profile

本文件用于解释 `works` 的防护设计，不把非官方评价当作确定事实。官方材料强调 M2.7 的工程、复杂 skill 和工具调用能力；公开用户反馈则呈现明显的 harness 依赖和长任务波动。

## Evidence levels

### Official capability claims

- MiniMax 称 M2.7 擅长真实工程、复杂 skills、agent teams 和动态工具搜索，并报告较高的 skill compliance。
- 官方部署文档给出接近 196K 的单序列上下文上限。长上下文容量不等于长任务中始终正确关注计划。

Sources:

- https://www.minimax.io/news/minimax-m27-en
- https://github.com/MiniMax-AI/MiniMax-M2.7
- https://platform.minimax.io/docs/guides/local-deploy

### Community reports: anecdotal but relevant

一个 OpenCode 社区讨论反复提到 shortcut、漏计划项、按自身实现编写容易通过的测试，以及计划越长后段漏项越多。同一讨论也有正向反例：给出可执行验证闭环时效果较好；发生 tunnel vision 时用 fresh session 和少量持久上下文恢复。

Source: https://www.reddit.com/r/opencodeCLI/comments/1soxkx6/minimax_m27_is_not_so_good_or_skill_issue/

这些是自报经验，不代表统计意义上的普遍结论；但它们与存量修改的高风险失效模式一致，适合用于防御性设计。

### Reproducible harness compatibility reports

- Hermes issue 报告部分配置下 XML tool-call markup 被作为文本输出。
- NVIDIA forum 报告函数名拼接造成 invalid tool call，并指向 agent-system compatibility。
- NemoClaw 的对照审计也展示了 M2.7 在若干简单 one-shot/multi-turn 工具场景成功，说明问题不能简单归因为“模型不会工具调用”。

Sources:

- https://github.com/NousResearch/hermes-agent/issues/27834
- https://forums.developer.nvidia.com/t/minimax-m2-7-error/366423
- https://github.com/NVIDIA/NemoClaw/issues/3123

## Design consequences

| Observed risk | Works control |
|---|---|
| 长计划后段漏项或急于完成 | 六阶段短状态机；每次只加载当前 slice；磁盘 Next Step；双完成门 |
| 为实现迎合测试 | expectation 先来自 requirement/characterization；有效 Red 必须是目标断言失败 |
| 跳过或缩小测试 | 每切片命名验证命令并记录 exit/log；最终独立验收矩阵 |
| tunnel vision | 同类失败两次后 fresh worker/verifier + handoff |
| 误改无关文件 | slice 前后 git status/scoped diff；保护修改前基线 |
| tool call 被当文本或 malformed | 视为 harness/infrastructure failure；不声称命令已执行；换通道一次后 handoff/blocked |
| 上下文越长越不稳定 | task_plan/findings/progress/log 分层；smart injection；压缩前 handoff |

本 profile 应通过 [evaluation.md](evaluation.md) 的真实仓库对照测试持续修订，而不是继续堆叠未经验证的提示词。
