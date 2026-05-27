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
└── services/                   # 服务级知识（sw-knowledge-agent 自动发现）
    └── (services auto-discovered by sw-knowledge-agent)
```

## 更新记录

| 日期 | 更新内容 | 更新人 |
|------|----------|--------|
| — | — | — |

## Patterns

(sw-knowledge-agent 自动维护)

