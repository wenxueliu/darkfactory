# 任务间消息通信模式（Message Bus）

**Type:** Pattern
**Created:** 2026-05-04
**Scope:** enterprise
**Author:** hw-controller

## Summary

基于 Consul KV 的异步消息队列模式，支持任务间通过发送消息实现通信协同，典型场景：Test Agent 测试失败后发送 FIX 消息通知开发 Agent，修复完成后收到反馈再重测。

## Details

Message Bus 在框架中实现为 `message_bus.py` 模块，使用 Consul KV 的目录结构作为消息队列。消息存储在 `workflows/<req_id>/requests/<target_task>/<msg_id>` 路径下。

**消息生命周期**：PENDING → PROCESSING → DONE/FAILED/TIMEOUT

**核心操作**：
1. **send()**：创建消息（含 msg_id、from、to、action、params），写入目标任务的请求前缀路径
2. **poll()**：读取目标任务前缀下的所有消息，按 created_at 升序排列（FIFO），支持按状态过滤和 limit 控制
3. **claim()**：使用 CAS 原子操作抢占消息。读取消息（获取 ModifyIndex）→ 检查 status==PENDING → CAS 写入 PROCESSING。CAS 失败说明被其他消费者抢走
4. **complete()/fail()**：使用 CAS 更新消息状态为 DONE/FAILED
5. **check_timeout()**：检测 PENDING/PROCESSING 消息是否超过 timeout 阈值，标记为 TIMEOUT

**FIX 重测闭环流程**：
- Test 任务 FAILED → Test Agent 调用 `message_bus.send(req_id, "test", "backend", "FIX", {"details": ...})`
- Backend Agent 轮询自己的消息队列，收到 FIX 消息后 claim → 修复 → complete
- Test Agent 轮询所有发送给 "test" 的消息，等所有消息状态为 DONE → 重新测试

## Context

适用于需要任务间传递状态和要求（而非仅通过 DAG 依赖关系耦合）的场景。典型用例：测试失败通知、代码审查请求、配置变更通知。

## Usage

1. 发送方：实例化 MessageBus(consul)，调用 `send(req_id, from_task, to_task, action, params)`
2. 接收方：轮询检查自己的消息队列，调用 `poll(req_id, task_name, status=PENDING)` 
3. 接收方：调用 `claim()` 使用 CAS 竞争消息的处理权
4. 接收方：处理完成后调用 `complete()` 或 `fail()`
5. 发送方：定期 `poll()` 检查发出的消息是否已完成

重要提示：CAS 保证同一条消息不会被多个消费者重复处理。消息的超时由 check_timeout() 处理，超时消息标记为 TIMEOUT 供发送方决策是否重发。

## Related

- ADR-0001: 选择 Consul KV 作为唯一状态存储（Message Bus 复用 Consul KV 做消息存储）
- ADR-0003: CAS 原子写入作为并发控制策略（消息的 claim/complete 均使用 CAS）
- DAG 依赖推进模式（Message Bus 提供 DAG 之外的带数据通信机制）
