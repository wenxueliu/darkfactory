# ADR-0004: Agent 主动认领任务而非框架推送

**状态:** `accepted`
**日期:** `2026-05-04`
**决策者:** `hw-controller`
**Scope:** enterprise

## 背景

在 DAG 驱动的多 Agent 工作流中，当 Aggregator 将某个下游任务激活为 PENDING 后，需要决定哪个 Agent 来执行这个任务。有两种设计思路：框架端主动将任务分配给特定 Agent（推送模式），或者让 Agent 自行发现和抢占 PENDING 任务（拉取模式）。

## 决策

**我们决定:** 框架不负责分配任务给特定 Agent。任务被 Aggregator 激活为 PENDING 后，Agent 通过 CAS 原子写入自行抢占。抢占成功（CAS 返回 true）的 Agent 获得任务执行权。

## 理由

1. 基于 CAS 的抢占机制天然匹配"多个 Agent 竞争任务"的场景——第一个 CAS 写入 IN_PROGRESS 成功的 Agent 获得任务，不需要框架做调度决策
2. Agent 可以自行判断自己的能力和当前负载来选择任务，框架不需要维护 Agent 能力表
3. Agent 是瞬时运行的（Launched on demand），框架不知道哪些 Agent 在线，不适合做分配
4. Agent 可以按需选择自己擅长的任务类型（如 test Agent 只抢占 test 类型的任务），框架不需要知道 agent 的能力元数据
5. 框架职责边界清晰：框架只管"什么可以做"（PENDING），Agent 管"谁来做"（抢占）

## 考虑的替代方案

| 方案 | 优点 | 缺点 | 为什么不选 |
|------|------|------|-----------|
| 框架轮询分配 (Push) | 负载均衡可控，可以按 Agent 能力分配 | 需要框架维护 Agent 列表和能力元数据，Agent 离线时需要重分配 | 框架需要维护 Agent 状态表，增加了"Agent 管理"这个额外复杂度域 |
| 消息队列 (RabbitMQ/Kafka) | 成熟的消费者竞争模式，支持 ACK 和重试 | 需要引入消息队列基础设施，Agent 离线时消息可能丢失 | 与零外部依赖原则冲突，且 Consul KV + CAS 已经够用 |
| Leader 选举 + 分配 | 集中管理，避免竞争冲突 | 引入选举复杂度，单点故障风险 | 过度设计——Agent 抢占本身是轻量级操作，不需要 Leader |

## 后果

### 正面
- Agent 实现自治：Agent 只需要扫描 PENDING 任务并 CAS 抢占，不依赖框架调度
- 框架实现简单：Aggregator 不需要管理 Agent 注册表或分配逻辑
- 弹性伸缩：新 Agent 启动后自动加入任务竞争，不需要通知框架
- 容错性好：Agent 崩溃后任务自动回滚为 PENDING，其他 Agent 可以重新抢占

### 负面
- 可能出现"饿死"现象（某些任务类型被 Agent 忽略，长期处于 PENDING）
- 无法保证任务优先级被遵守（Agent 可能跳过高优先级任务选择简单的任务）
- 需要 Watchdog 辅助：Agent 抢占后崩溃，任务卡在 IN_PROGRESS，需要 Watchdog 超时回滚
- 任务分配不可预测，难以做执行计划预估
