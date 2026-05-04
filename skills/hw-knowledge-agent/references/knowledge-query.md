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
2. **Search** using the tool:
   ```bash
   python scripts/kb-search.py "<query>" [--type pattern|decision|lesson|api] [--json] [--max-results 10]
   ```
   - Use `--json` for programmatic consumption
   - Use `--type` to filter by knowledge type
   - The script handles relevance ranking automatically
3. **Return with context** — present top results with relevance explanation

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
