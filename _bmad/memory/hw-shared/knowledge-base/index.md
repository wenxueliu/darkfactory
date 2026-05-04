# 知识库索引

## 概述

黑灯工厂项目知识库，记录架构决策、设计模式、经验教训和API契约。
按三级分层结构组织：企业级全局知识、业务领域级知识、服务级知识。

## 目录结构

```
knowledge-base/
├── index.md                    # 本索引文件
├── .kb-log.jsonl               # 事务日志
├── _enterprise/                # 企业级全局知识
│   ├── decisions/              # 影响多个/全部服务的 ADR
│   ├── patterns/               # 跨服务可复用模式
│   ├── lessons/                # 全局经验教训
│   └── contracts/              # 跨服务 API 契约
├── domains/                    # 业务领域级知识（预留）
└── services/                   # 服务级知识
    ├── harness_framework/      # harness-framework 服务
    │   ├── overview.md
    │   ├── api-endpoints.md
    │   ├── db-schema.md
    │   ├── decisions/          # 服务专属 ADR
    │   ├── patterns/           # 服务专属模式
    │   └── lessons/            # 服务专属教训
    └── multiagents/            # multiagents 服务
        ├── overview.md
        ├── api-endpoints.md
        ├── db-schema.md
        ├── decisions/          # 服务专属 ADR
        ├── patterns/           # 服务专属模式
        └── lessons/            # 服务专属教训
```

## 更新记录

| 日期 | 更新内容 | 更新人 |
|------|----------|--------|
| 2026-05-04 | Pattern: 3-Stage 设计委托模式 | hw-controller |
| 2026-05-04 | Pattern: 任务间消息通信模式（Message Bus） | hw-controller |
| 2026-05-04 | Pattern: Watchdog 僵尸任务回收模式 | hw-controller |
| 2026-05-04 | Pattern: DAG 依赖推进模式 | hw-controller |
| 2026-05-04 | Decision: 框架不做 LLM 调用（纯规则引擎） | hw-controller |
| 2026-05-04 | Decision: Agent 主动认领任务而非框架推送 | hw-controller |
| 2026-05-04 | Decision: CAS 原子写入作为并发控制策略 | hw-controller |
| 2026-05-04 | Decision: 零外部依赖原则（仅 Python 标准库） | hw-controller |
| 2026-05-04 | Decision: 选择 Consul KV 作为唯一状态存储 | hw-controller |
## Patterns

- [3-Stage 设计委托模式](_enterprise/patterns/3-Stage-设计委托模式.md)
- [DAG 依赖推进模式](_enterprise/patterns/DAG-依赖推进模式.md)
- [Watchdog 僵尸任务回收模式](_enterprise/patterns/Watchdog-僵尸任务回收模式.md)
- [任务间消息通信模式（Message Bus）](_enterprise/patterns/任务间消息通信模式（Message-Bus）.md)
- [测试采集管道](_enterprise/patterns/测试采集管道.md)

## Architecture Decisions

- [ADR-0005: 框架不做 LLM 调用（纯规则引擎）](_enterprise/decisions/ADR-0005-框架不做-LLM-调用（纯规则引擎）.md)
- [ADR-0004: Agent 主动认领任务而非框架推送](_enterprise/decisions/ADR-0004-Agent-主动认领任务而非框架推送.md)
- [ADR-0003: CAS 原子写入作为并发控制策略](_enterprise/decisions/ADR-0003-CAS-原子写入作为并发控制策略.md)
- [ADR-0002: 零外部依赖原则（仅 Python 标准库）](_enterprise/decisions/ADR-0002-零外部依赖原则（仅-Python-标准库）.md)
- [ADR-0001: 选择 Consul KV 作为唯一状态存储](_enterprise/decisions/ADR-0001-选择-Consul-KV-作为唯一状态存储.md)

## Lessons Learned

- [仅用相对路径——禁止平台专属变量](_enterprise/lessons/仅用相对路径——禁止平台专属变量.md)
- [框架不管 Agent 内存——分离编排与记忆职责](_enterprise/lessons/框架不管-Agent-内存——分离编排与记忆职责.md)

## API Contracts

- [harness-framework WebAPI 端点契约](_enterprise/contracts/harness-framework-WebAPI-端点契约.md)

## Service Knowledge

### harness_framework

- [Harness Framework — API Endpoints](services/harness_framework/api-endpoints.md)
- [Harness Framework — Database Schema](services/harness_framework/db-schema.md)
- [Harness Framework — 服务概览](services/harness_framework/overview.md)

### multiagents

- [Multiagents — API Endpoints](services/multiagents/api-endpoints.md)
- [Multiagents — Database Schema](services/multiagents/db-schema.md)
- [Multiagents — 服务概览](services/multiagents/overview.md)


## 更新记录

| 日期 | 更新内容 | 更新人 |
|------|----------|--------|
| 2026-05-04 | Index rebuilt (19 entries) | kb-index.py |
