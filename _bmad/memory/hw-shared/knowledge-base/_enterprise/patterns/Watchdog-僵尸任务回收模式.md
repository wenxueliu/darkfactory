# Watchdog 僵尸任务回收模式

**Type:** Pattern
**Created:** 2026-05-04
**Scope:** enterprise
**Author:** hw-controller

## Summary

Watchdog 组件定期扫描所有 IN_PROGRESS 任务，检测 Agent 是否存活以及任务是否超时，对异常的"僵尸任务"执行自动回滚或失败标记的容错恢复模式。

## Details

Watchdog 运行在独立的线程中，每 30 秒执行一次 _tick() 扫描。对每个 published workflow 中的 IN_PROGRESS 任务执行两阶段检查：

1. **Agent 存活检查**：通过 Consul Health API（/health/service/agent-worker）获取所有 passing 状态的 Agent ID。如果任务 assigned_agent 不在存活列表中，判定 Agent 死亡，执行 recover。

2. **任务超时检查**：解析任务的 started_at 时间戳，与当前时间比较。如果 age > task_timeout（默认 1 小时），判定任务超时，执行 recover。

**恢复策略**（_recover 方法）：
- 记录 last_recovery_reason（agent_dead 或 timeout）和 last_recovery_at
- 增加 retry_count
- 如果 retry_count >= max_retry（默认 3），将任务设为 FAILED，写入 error_message，同时写入 alerts/<req_id>/<task_name> 告警路径
- 如果 retry_count < max_retry，将任务回滚为 PENDING，删除 assigned_agent 和 started_at，允许其他 Agent 重新抢占

## Context

适用于任何 Agent 可能崩溃、网络分区或任务执行时间不可预测的分布式工作流系统。特别适合 Agent 按需启动的场景（Agent 执行完任务后退出，但可能在执行中意外终止）。

## Usage

1. 随 daemon 启动 Watchdog（--no-watchdog 可禁用），默认 poll_interval=30s
2. 配置 task_timeout（--task-timeout，秒）和 max_retry（--max-retry，默认 3）
3. Agent 启动时在 Consul 注册 service（service_register），框架通过 health/service/agent-worker 检测
4. Agent 执行任务时写入 started_at 时间戳，框架据此计算超时
5. 任务恢复后其他 Agent 可以重新抢占，实现"自愈"

注意：retry_count 在 Agent 主动失败时也可能递增，Framework 和 Agent 的计数共享。如果 Agent 自行重试了 2 次，Watchdog 最多补充到 max_retry。

## Related

- ADR-0001: 选择 Consul KV 作为唯一状态存储（Consul Health 用于 Agent 存活检测）
- ADR-0004: Agent 主动认领任务而非框架推送（Watchdog 回滚后重新变为 PENDING 供其他 Agent 抢占）
- DAG 依赖推进模式（两个模式配合实现 DAG 的可靠推进）
