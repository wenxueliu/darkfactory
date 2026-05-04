# 框架不管 Agent 内存——分离编排与记忆职责

**Type:** Lesson
**Created:** 2026-05-04
**Scope:** enterprise
**Author:** hw-controller

## Summary

设计初期曾考虑在框架层集成 Agent 记忆管理（持久化 Agent 上下文、共享记忆库等），但最终决定框架完全不管理 Agent 记忆。Agent 的记忆属于 Agent 的内部实现细节，框架只负责任务调度和状态管理。

## Details

框架最初的设计方案包含 Agent 记忆管理模块，计划在 Consul KV 中持久化 Agent 的会话上下文和执行历史。但在实现过程中发现以下问题：

**1. 框架与 Agent 的生命周期不匹配**
框架是长期运行的后台进程（daemon），而 Agent 是按需启动的瞬时进程。框架如果管理 Agent 的记忆，需要管理 Agent 生命周期事件（启动、执行、完成、销毁），这超出了框架的职责范围。框架并不知道 Agent 何时启动、何时结束。

**2. 记忆的存储方式与框架无关**
不同 Agent 有不同的记忆需求：有的需要向量数据库做语义搜索，有的只需要文件系统的上下文缓存，有的需要完整的对话历史。框架无法统一满足所有记忆需求——强制使用一种存储方式会限制 Agent 的灵活性。

**3. 框架职责边界膨胀**
如果框架管理 Agent 记忆，那框架也需要管理 Agent 之间的记忆共享策略、权限控制、一致性协议。这些是分布式系统设计的核心复杂度，不应该由编排框架承担。

**最终方案**：
- 框架不管理任何 Agent 记忆（task-level / global 都不管）
- 任务间需要传递数据时，通过 Message Bus（`message_bus.py`）异步通信
- Agent 自行决定记忆存储方式（本地文件、向量数据库等）
- Agent 需要共享的上下文通过 `_bmad/memory/hw-shared/` 目录由 Agent 自行读写
- 需要在启动 Agent 时注入的全局上下文，由顶层规划（hw-controller）在 Agent 启动前配置

这个决策在 memory-model.md 中被明确记录为框架职责边界。

## Context

设计框架与 Agent 的职责边界时，需要明确回答"框架应该管什么、不管什么"。本教训适用于一切编排系统设计中框架职责范围的界定——不要因为"方便"而把 Agent 内部细节塞进框架。

## Usage

_No content provided._

## Related

- ADR-0005: 框架不做 LLM 调用（纯规则引擎）（本教训的 "框架职责边界" 思路与 ADR-0005 一脉相承）
- 任务间消息通信模式（Message Bus）（框架提供的唯一任务间通信机制）
- `services/harness_framework/docs/memory-model.md`（决策文档）
