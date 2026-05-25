# KnowledgeQuery: 知识查询

## What Success Looks Like

Relevant knowledge is found and presented in context, helping make better decisions faster. Freshness-aware: stale/superseded knowledge is flagged or excluded so decisions are based on current information.

## Your Approach

### Query Types

| Query | When |
|-------|------|
| Pattern search | "Has this pattern been used before?" |
| Decision lookup | "What was decided about X?" |
| Lesson search | "What went wrong with similar approaches?" |
| API reference | "What's the existing API contract?" |

### Freshness-Aware Query

知识库会随时间推移而衰减。查询时应注意以下新鲜度规则：

| Status | Meaning | Query Behavior |
|--------|---------|---------------|
| `active` | Current and valid | Normal search results |
| `stale` | Confidence decayed due to age | Penalized in scoring (-3), flagged with marker |
| `deprecated` | No longer recommended | Penalized in scoring (-5), flagged with [D] |
| `superseded` | Replaced by a newer entry | Penalized in scoring (-10), flagged with [S]; exclude with `--exclude-superseded` |
| `expired` | Past its expiry date | Penalized in scoring (-10), flagged with [E]; exclude with `--exclude-expired` |

### Query Process

1. **Identify keywords** from current context
2. **Search** using the tool:
   ```bash
   # Basic search
   python scripts/kb-search.py "<query>" [--type pattern|decision|lesson|api] [--json] [--max-results 10]

   # Freshness-aware search (recommended for critical decisions)
   python scripts/kb-search.py "<query>" --exclude-expired --exclude-superseded

   # Strict freshness: exclude all non-active entries
   python scripts/kb-search.py "<query>" --exclude-expired --exclude-superseded --exclude-deprecated
   ```
   - Use `--json` for programmatic consumption
   - Use `--type` to filter by knowledge type
   - Use `--exclude-expired` / `--exclude-superseded` / `--exclude-deprecated` for freshness filtering
   - The script handles relevance ranking automatically, with freshness penalties applied to non-current entries
3. **Check freshness** of critical entries:
   ```bash
   python scripts/kb-freshness.py --check <relative-path>
   ```
4. **Return with context** — present top results with relevance explanation. Include freshness status when entries are not `active`.

### Output Format

```markdown
## Knowledge Query Results

**Query:** {keywords}
**Freshness filter:** {active / no-expired / no-superseded / strict}

**Relevant Entries:**

### {Entry Title}
- **Type:** Pattern/Decision/Lesson/API
- **Status:** active / stale / deprecated / superseded / expired
- **Relevance:** {why relevant}
- **Summary:** {what it says}
- **Source:** {when/where from}
- **Link:** {file location}

### Usage Recommendation
{how to apply this knowledge}
{If status is not active: include warning about freshness concern}
```

### Freshness Warning Protocol

When a search result has non-active status:
- **stale**: "This entry's confidence has decayed to {eff_conf}/10. Consider reviewing for accuracy before applying."
- **deprecated**: "This entry is deprecated and no longer recommended. Seek current alternatives."
- **superseded**: "This entry has been superseded by {superseded_by}. Use the newer entry instead."
- **expired**: "This entry has expired. Do not apply without re-validation."
