# DAG 依赖推进模式

**Type:** Pattern
**Created:** 2026-05-04
**Scope:** enterprise
**Author:** hw-controller

## Summary

Aggregator 组件基于 DAG 拓扑的任务依赖关系，在上游任务全部完成后自动推进下游任务状态从 BLOCKED 到 PENDING 的模式。

## Details

Aggregator 每 5 秒轮询 workflows/<req_id>/tasks/*/status，解析 dependencies JSON 中的 DAG 拓扑。对每个任务，检查其 depends_on 列表中的所有上游任务是否已为 DONE 状态。当所有阻塞依赖（blocking=true）均 DONE 时，将本任务设为 PENDING（激活状态）。支持 blocking/non-blocking 依赖的区分——blocking 依赖未完成时任务保持 BLOCKED，non-blocking 依赖不影响激活。

复合节点处理（`type: parallel` 和 `type: aggregate`）：parallel 节点在其所有依赖 DONE 时，将 children 列表中的子任务全部设置为 PENDING，然后自身标记为 DONE。aggregate 节点是 parallel 的同步屏障——所有上游 parallel DONE 后，自身 DONE 并激活下游依赖本 aggregate 的任务。

控制信号支持：PAUSE 时跳过 tick 循环（不推进任何任务），ABORT 时将所有非终态任务设为 ABORTED，RESUME 删除 control 键恢复调度。

优先级排序：支持按 priority 降序处理需求，高优先级 workflow 的任务先被激活。

## Context

适用于任何需要按依赖关系自动推进多步骤工作流的场景。典型场景：需求经过 design -> backend -> test -> deploy 串行阶段，每个阶段的完成自动触发下一个阶段。

## Usage

1. 在 dependencies JSON 中定义任务拓扑（每个任务指定 type、depends_on、blocking 属性）
2. 启动 Aggregator（默认随 daemon 启动，poll_interval=5s）
3. 确保 workflow 的 published=true（否则 Aggregator 跳过草稿）
4. Agent 通过 CAS 抢占 PENDING 任务并执行
5. 任务完成后写入 DONE 状态，Aggregator 在下一次 tick 中自动激活下游

注意：Aggregator 只在 `_tick()` 轮询中推进状态，不实时响应变更。如果需要更快的响应，可以减小 poll_interval（但会增加 Consul 负载）。

## Related

- ADR-0001: 选择 Consul KV 作为唯一状态存储（DAG 状态存储在 Consul KV 中）
- ADR-0004: Agent 主动认领任务而非框架推送（Aggregator 只激活为 PENDING，Agent 自己认领）
- Watchdog 僵尸任务回收模式（与 Aggregator 一起保障工作流推进）
