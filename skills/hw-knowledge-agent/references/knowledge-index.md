# KnowledgeIndex: 知识索引维护

## What Success Looks Like

The knowledge base is organized, searchable, and entries are properly linked.

## Index Structure

```markdown
# Knowledge Base Index

## Patterns
- [Pattern Name](patterns/{name}.md)
- ...

## Decisions
- [Decision Title](decisions/{id}.md)
- ...

## Lessons Learned
- [Lesson Title](lessons/{id}.md)
- ...

## API Contracts
- [Contract Name](api-contracts/{name}.md)
- ...

## Recent Updates
- {date} - {entry} - {type}
- ...
```

## Maintenance Tasks

| Task | Frequency | Action |
|------|-----------|--------|
| Add new entries | On event | Link in index |
| Check orphans | Weekly | Link or remove |
| Update recency | Monthly | Refresh dates |
| Merge duplicates | Quarterly | Consolidate |

## Quality Checklist

- [ ] All entries have type
- [ ] All entries have dates
- [ ] All entries are linked from index
- [ ] No orphaned entries
- [ ] Index is well-organized by type
