# ADR-0003: CAS 原子写入作为并发控制策略

**状态:** `accepted`
**日期:** `2026-05-04`
**决策者:** `hw-controller`
**Scope:** enterprise

## 背景

多个 Agent 同时竞争同一个 PENDING 任务时，需要保证只有一个 Agent 能成功抢占。除此之外，Watchdog 在回滚任务时可能与 Agent 同时操作同一个任务的状态，MessageBus 的 claim 操作也需要保证多个消费者不会同时处理同一条消息。因此需要一个可靠的并发控制机制。

## 决策

**我们决定:** 使用 Consul KV 的 Check-And-Set (CAS) 机制作为所有竞争敏感操作的唯一并发控制手段，不引入分布式锁或数据库事务。

## 理由

1. CAS 是 Consul KV 原生支持的原子操作，当且仅当 ModifyIndex 匹配时才写入成功，天然适合"先检查再写入"的竞争场景
2. Agent 抢占任务的流程：读取任务状态（获取 index）→ 检查是否 PENDING → 写入 IN_PROGRESS（带 CAS index），CAS 失败说明已有其他 Agent 抢占，自动回退
3. MessageBus.claim() 使用 CAS 保证同一条消息不会被多个消费者重复处理
4. 不需要引入 Redis 分布式锁或 ZooKeeper 临时节点等额外基础设施
5. CAS 失败时调用方可以优雅地重试或放弃，不会产生死锁

## 考虑的替代方案

| 方案 | 优点 | 缺点 | 为什么不选 |
|------|------|------|-----------|
| Redis 分布式锁 (SETNX) | 锁语义清晰，支持 TTL 自动释放 | 需要额外部署 Redis，需要安装 Python Redis 客户端库 | 引入额外基础设施与零外部依赖原则冲突 |
| ZooKeeper 临时节点 | 强一致性，Session 超时自动释放锁 | 需要部署 ZK 集群，API 比 Consul CAS 复杂 | Consul 已在系统中存在，CAS 足够满足需求 |
| 数据库行锁 (SELECT FOR UPDATE) | 成熟的锁机制，文档丰富 | 需要关系型数据库，连接管理复杂 | 系统中没有数据库，为并发控制引入数据库成本太高 |

## 后果

### 正面
- 并发安全天然嵌入在状态存储层，不需要单独设计锁服务
- Agent 抢占是"尽力而为"的乐观争抢，CAS 失败后自动寻找下一个 PENDING 任务
- 无死锁风险（CAS 是单次原子操作，不是多步锁协议）
- 调用方代码简洁：`kv_put(key, value, cas=index)` 一行完成原子写入

### 负面
- CAS 不能解决长事务场景（多步操作的原子性需要调用方自行处理）
- 如果 Agent 在写入 IN_PROGRESS 后崩溃但没有及时释放状态，需要 Watchdog 超时回滚
- CAS 要求调用方持有最新的 ModifyIndex，需要先读取再写入（两轮 HTTP 请求）
- 高竞争场景下 CAS 频繁失败导致性能下降（但 Agent 抢占本身是低频操作）
