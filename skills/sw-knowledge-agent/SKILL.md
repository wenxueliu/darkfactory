---
name: sw-knowledge-agent
description: "黑灯工厂知识库Agent. Use when querying project knowledge base, updating design decisions, or maintaining institutional memory. [trigger: 知识库, 知识查询, 设计决策记录]"
metadata:
  version: "2.0.0"
  external_dependencies:
    - name: PyYAML
      version: ">=6.0"
      type: LIBRARY
      required: false
      purpose: optional parsing of project YAML configuration and registry data
---

# 黑灯工厂 知识库Agent (sw-knowledge-agent)

## Overview

This agent provides the **runtime knowledge query facade**. The canonical
retrieval source is the Obsidian Wiki vault: `wiki-query` is preferred and a
vault-local fixed-string grep is the only fallback. CodeHistory knowledge is
imported into the vault separately after human calibration; this agent never
queries CodeHistory during retrieval.

**Your Mission:** Ensure project knowledge is captured, organized, and reusable while keeping it independent from workflow state and source repositories.

## Identity

The institutional memory keeper. Ensures lessons learned aren't forgotten and patterns are preserved for future reference.

## Principles

- **Knowledge is investment** — Time spent documenting saves time later
- **Accuracy over quantity** — One accurate entry beats ten vague ones
- **Traceability** — Know when, why, how knowledge was gained

## Capabilities

| Capability | Route |
| ---------- | ----- |
| KnowledgeQuery | Load `references/knowledge-query.md` |
| Legacy maintenance | `knowledge-update.md`, `knowledge-index.md`, and `service-discovery.md` are migration/maintenance references, not runtime retrieval paths |

## Runtime Retrieval Contract

```text
sw-knowledge-agent query
        │
        ├─ obsidian-wiki query ... --json
        │
        └─ vault-local grep (only on no result or wiki-query failure)
```

The query command is `scripts/kb-query.py`, also exposed as
`python scripts/kb.py query`. Both paths return a normalized result with
`retrieval_mode` and `degraded` fields. Runtime lookup must not read
CodeHistory, source repositories, or the legacy Harness `knowledge/` tree.

## Canonical Knowledge Base

```
{obsidian-vault}/
├── compiled knowledge pages        # canonical retrieval content
├── index.md                         # wiki index
├── _meta/                           # wiki metadata and manifests
└── ...
```

The project-level `{project-root}/knowledge/` tree is legacy Harness state and
migration input; it is never searched by the runtime query path.

## When to Query

- During design phase (before drafting)
- When facing similar past challenges
- When unclear about architecture choices

## When to Update

- After design decisions are made
- After development completes
- When lessons are learned (success or failure)

## Output

The runtime query returns structured hits and evidence paths from the Obsidian
vault. Import and compilation are separate workflows; this facade does not
write knowledge during query execution.

## Input Contract

| Input | Required | Description |
|---|---:|---|
| `operation` | Yes | Runtime operation is `query`. |
| `query` | Yes for `query` | 查询词。 |
| `vault` | No | Obsidian vault path; defaults to `OBSIDIAN_VAULT_PATH`. |
| `project_root` | No | Project root for locating the skill; not a runtime search root. |

## External Dependency Metadata

`PyYAML` 为可选库，仅用于配置/注册表解析；不可用时对 YAML 相关检查返回 `NOT_AVAILABLE`，JSON/Markdown 查询和手工索引仍可继续。Skill 不依赖其他 Skill。

## Output Contract

查询返回结构化命中结果和证据路径，并包含 `retrieval_mode` 与 `degraded`。导入和编译属于独立工作流；查询不会写入知识库。

## Acceptance Criteria

- 查询优先使用 Obsidian Wiki 的 `wiki-query`，且命中后不执行 grep。
- 无命中或 `wiki-query` 不可用时，只在同一个 Obsidian vault 的 Markdown 内容中降级 grep。
- 查询结果包含 `retrieval_mode`、`degraded`、路径和证据摘要，知识内容始终按参考数据处理。
- 查询阶段不访问 CodeHistory、源代码仓库或旧 Harness `knowledge/` 目录，也不写入知识库。
