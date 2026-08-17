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

公开反馈并不一致，但反复出现 harness 依赖、忽略明确规划指令、长任务后段偏航、误删或引入无关错误等现象。OpenCode 用户报告模型即使收到“先计划并等待”仍直接编码且错误较多，并建议使用项目化 standards skill 与对抗审查；Hermes 用户报告后段绕圈和代码质量下降；另有用户报告重构时删除既有代码。相反，正面反馈通常将其定位为快速、便宜的 routine coding 工具，并强调 prompt 足够具体、输出格式明确时更可靠。

Sources:

- https://www.reddit.com/r/opencodeCLI/comments/1soxkx6/minimax_m27_is_not_so_good_or_skill_issue/
- https://www.reddit.com/r/hermesagent/comments/1tgihiq/hermes_with_minimax_m27_is_insufferable/
- https://www.reddit.com/r/MiniMax_AI/comments/1sp4v1z/minimax_token_plan_stater_10_review_heavily/
- https://www.reddit.com/r/MiniMax_AI/comments/1v28etg/minimax_m27_has_become_my_goto_model_for_routine/

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
| Green 后停下询问是否继续 | 完整 Req 队列持久化；Green 自动选择下一未完成 Req；禁止阶段性确认 |
| 忽略项目分层、走最短 Mapper 路径 | dirty-baseline 架构扫描；Green/Phase 4 机械拒绝新增入口→持久层依赖；要求先找相邻 Service 模式 |

公开资料没有证明“直接调用 Mapper”是 M2.7 的普遍 Spring 特定缺陷；这是本项目的实际运行观察。它与公开反馈中的约束漂移、浅层最短路径和后段失稳相符，因此采用可执行 harness 门禁，而不是继续增加软提示词。

本 profile 应通过 [evaluation.md](evaluation.md) 的真实仓库对照测试持续修订，而不是继续堆叠未经验证的提示词。
