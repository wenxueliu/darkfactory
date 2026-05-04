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
2. **Check for duplicates** before creating (strongly recommended):
   ```bash
   python scripts/kb-log.py <type> "<title>" --stdin --dedup-check <<'EOF'
   ## Summary
   ...
   ## Details
   ...
   EOF
   ```
   - If similar entries are reported (>80% similarity): review the existing entry
     first. Use `kb-merge.py --merge <file1> <file2>` to consolidate if the new
     entry does not add substantial new information.
   - If similar entries are found (40-80%): the new entry is related but
     distinct — verify your summary/detail sections clearly differentiate it.
   - If no similar entries: safe to proceed.

3. **Write entry** (without dedup check if already verified, or with `--auto-dedup`
   to silently skip duplicates in automated pipelines):
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

4. **Verify** the entry was written:
   ```bash
   python scripts/kb-index.py --validate-only
   ```

### Batch Deduplication

When the knowledge base grows, periodically scan and clean up similar entries:

```bash
# Find similar pairs (same type, >=40% similarity)
python scripts/kb-merge.py --scan --threshold 0.4

# Find cross-type duplicates
python scripts/kb-merge.py --scan --cross-type --threshold 0.5

# Preview merging a specific pair
python scripts/kb-merge.py --merge <file1> <file2> --dry-run

# Merge a pair (older entry kept, newer merged in and removed)
python scripts/kb-merge.py --merge <file1> <file2>

# Batch merge all pairs above threshold
python scripts/kb-merge.py --merge-all --threshold 0.7
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
- **Don't create near-duplicates** — Always run `--dedup-check` before creating
