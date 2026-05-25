# ADR-0001: 选择 Consul KV 作为唯一状态存储

**状态:** `accepted`
**日期:** `2026-05-04`
**决策者:** `hw-controller`
**Scope:** enterprise

## 背景

harness-framework 需要为多 Agent 协作系统提供统一的状态存储，支持任务状态（BLOCKED/PENDING/IN_PROGRESS/DONE/FAILED）、DAG 依赖拓扑、控制信号（PAUSE/RESUME/ABORT）的读写，以及 Watchdog 容错恢复和 Message Bus 消息传递。状态存储需要支持并发安全写入（多个 Agent 同时竞争任务）、阻塞等待（Watch long-polling 变更）、以及 HTTP 协议访问（Agent 运行在不同环境中）。

## 决策

**我们决定:** 选择 Consul KV 作为框架唯一的持久化状态存储，不引入数据库或消息队列。

## 理由

1. Consul KV 内置 Watch 机制（blocking query），Aggregator 和 Watchdog 可以用 long-polling 监听状态变更，无需额外实现消息通知
2. 支持 Check-And-Set (CAS) 原子操作，天然适合 Agent 抢占 PENDING 任务的并发场景
3. 通过 HTTP API 访问（标准库 urllib 即可），Agent 不需要安装任何额外客户端或驱动
4. Consul 的 Health 检查机制（/health/service/<name>）可以直接用于 Watchdog 的 Agent 存活检测
5. KV 的目录结构（workflows/<req_id>/tasks/<name>/status）天然适合树状工作流状态建模
6. 团队已有 Consul 运维经验，部署简单（单二进制文件）

## 考虑的替代方案

| 方案 | 优点 | 缺点 | 为什么不选 |
|------|------|------|-----------|
| PostgreSQL + LISTEN/NOTIFY | 成熟的关系型存储，强一致性 | 需要安装 PostgreSQL、维护连接池、额外的 ORM 依赖 | 引入外部数据库增加了部署复杂度，与"零外部依赖"原则冲突 |
| Redis + Pub/Sub | 高性能、内存操作 | 无 CAS 支持、数据持久化需要额外配置、需要安装 Redis 客户端库 | 无法满足原子抢占的需求，且引入了 Python 外部依赖 |
| SQLite | 零配置、文件存储 | 不支持并发写入、无 Watch 机制 | 多 Agent 进程同时写入时存在竞争问题，无法实现阻塞监听 |

## 后果

### 正面
- 统一状态存储降低了系统复杂度，只维护一个基础设施组件
- CAS 机制保障了并发安全，不需要分布式锁
- blocking query 简化了 Aggregator 的变更监听实现
- Consul Health 直接用于 Agent 存活检测，Watchdog 无需单独实现心跳协议

### 负面
- Consul 的 KV 存储不是为大规模事务性负载设计的，不适合存储大量数据
- KV 值大小有限制（默认 512KB），不能存储大文件
- 极端情况下 Consul 集群故障会导致整个框架失能
- 查询效率受限于前缀扫描，不适合复杂过滤条件
