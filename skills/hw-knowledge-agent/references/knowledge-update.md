# KnowledgeUpdate: 知识更新

## What Success Looks Like

New knowledge is accurately captured, properly categorized, and linked in the index.

## Your Approach

### Knowledge Types

| Type | What to Capture |
|------|----------------|
| Pattern | Reusable solution to recurring problem |
| Decision | Architecture choice and rationale |
| Lesson | Insight from success or failure |
| API Contract | Interface definition and usage |

### Entry Format

```markdown
# {Knowledge Title}

**Type:** {Pattern/Decision/Lesson/API}
**Created:** {date}
**Author:** {agent/human}

## Summary
{2-3 sentence description}

## Details
{detailed description}

## Context
{when/why this was created}

## Usage
{how to apply this knowledge}

## Related
{links to related entries}
```

### Update Process

1. **Categorize** the knowledge type
2. **Write entry** using the tool:
   ```bash
   python scripts/kb-log.py <type> "<title>" --stdin <<'EOF'
   ## Summary
   ...
   ## Details
   ...
   EOF
   ```
   - Use `--dry-run` first to preview
   - The script auto-updates index.md and appends a transaction log
3. **Verify** the entry was written:
   ```bash
   python scripts/kb-index.py --validate-only
   ```

### When to Update

| Event | Action |
|-------|--------|
| Design decision made | Record decision + rationale |
| Development complete | Document patterns discovered |
| Bug found | Add lesson learned |
| API created | Document contract |

## Anti-Patterns

- **Don't over-document** — Capture insights, not every detail
- **Don't Vague-document** — Be specific enough to be useful
- **Don't orphan entries** — Always link to index
