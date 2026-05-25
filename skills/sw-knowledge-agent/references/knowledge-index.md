# KnowledgeIndex: 知识索引维护

## What Success Looks Like

The knowledge base is organized, searchable, and entries are properly linked.

## Index Structure

```markdown
# Knowledge Base Index

## Shared Knowledge (跨服务共享)
### Patterns
- [Pattern Name](shared/patterns/{name}.md)
- ...

### Architecture Decisions
- [ADR-{NNNN}: Decision Title](shared/decisions/ADR-{NNNN}-{slug}.md)
- ...

### Lessons Learned
- [Lesson Title](shared/lessons/{id}.md)
- ...

## Service Knowledge (每服务专属)
### {service-id} — {服务名称}
- [Overview](services/{service-id}/overview.md) (auto-generated)
- [API Endpoints](services/{service-id}/api-endpoints.md) (auto-generated)
- [DB Schema](services/{service-id}/db-schema.md) (auto-generated)
- Service Patterns: {列表} (manual)
- ...

### {another-service-id} — {另一服务名称}
- ...

## Cross-Service Contracts
- [{service-id} OpenAPI](contracts/{service-id}-openapi.yaml)
- ...

## Service Dependency Graph
```
{service-id} ←── {consumer-id}
     ↑
     └── {another-consumer}
```

## Recent Updates
- {date} — {service-id} 服务发现更新 (commit: {sha})
- {date} — ADR-{NNNN} created
- {date} — {entry} — {type}
```

## 自动化工具

索引维护通过以下脚本自动化：

```bash
# 重建索引
python scripts/kb-index.py --rebuild

# 仅校验不修改
python scripts/kb-index.py --validate-only

# 检测孤立条目
python scripts/kb-index.py --detect-orphans

# 完整维护 (重建 + 校验 + 孤儿检测)
python scripts/kb-index.py
```

## 索引维护任务

| 任务 | 频率 | 操作 |
|------|------|------|
| 新知识条目 | 事件驱动 | `kb-log.py` 自动更新索引 |
| 服务发现重新生成 | 每个需求完成后 | `kb-service-discovery.py` + `kb-index.py --rebuild` |
| 孤儿条目检查 | 每周 | `kb-index.py --detect-orphans` |
| 服务依赖图更新 | 服务发现后 | `kb-service-discovery.py` 自动生成 |
| 重复合并 | 每季度 | 人工审查后合并类似条目 |

## 质量检查清单

- [ ] 所有共享知识条目有类型、日期、作者
- [ ] 所有服务有 auto-generated 概览文件 (monolith 模式跳过)
- [ ] 所有条目在索引中可发现
- [ ] 服务依赖图与 service-registry.yaml 一致
- [ ] 无孤儿条目
- [ ] Auto-generated 文件标注 `DO NOT EDIT MANUALLY`
