# KnowledgeQuery: 知识查询

## What Success Looks Like

Relevant knowledge is found and presented in context, helping make better decisions faster.

## Your Approach

### Query Types

| Query | When |
|-------|------|
| Pattern search | "Has this pattern been used before?" |
| Decision lookup | "What was decided about X?" |
| Lesson search | "What went wrong with similar approaches?" |
| API reference | "What's the existing API contract?" |

### Query Process

1. **Identify keywords** from current context
2. **Search index** for related entries
3. **Rank by relevance** — recency, usage frequency
4. **Return with context** — why this is relevant now

### Output Format

```markdown
## Knowledge Query Results

**Query:** {keywords}

**Relevant Entries:**

### {Entry Title}
- **Type:** Pattern/Decision/Lesson/API
- **Relevance:** {why relevant}
- **Summary:** {what it says}
- **Source:** {when/where from}
- **Link:** {file location}

### Usage Recommendation
{how to apply this knowledge}
```
