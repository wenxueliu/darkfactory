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
| 2026-05-05 | Pattern: Test Freshness v2 | hw-knowledge-agent |
| 2026-05-05 | Pattern: Test Freshness Pattern | hw-knowledge-agent |
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
- [Test Freshness Pattern](_enterprise/patterns/Test-Freshness-Pattern.md)

- [3-Stage 设计委托模式](_enterprise/patterns/3-Stage-设计委托模式.md)
- [DAG 依赖推进模式](_enterprise/patterns/DAG-依赖推进模式.md)
- [Test Freshness v2](_enterprise/patterns/Test-Freshness-v2.md)
- [Watchdog 僵尸任务回收模式](_enterprise/patterns/Watchdog-僵尸任务回收模式.md)
- [任务间消息通信模式（Message Bus）](_enterprise/patterns/任务间消息通信模式（Message-Bus）.md)
- [测试采集管道](_enterprise/patterns/测试采集管道.md)

