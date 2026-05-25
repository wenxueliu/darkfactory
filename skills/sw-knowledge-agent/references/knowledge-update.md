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
| Knowledge superseded | Run `kb-freshness.py --mark-superseded <old> --by <new>` to link old→new |
| Knowledge expired | Run `kb-freshness.py --mark-expired <entry>` or `kb-log.py ... --status expired` |
| Knowledge reactivated | Run `kb-freshness.py --reactivate <entry>` to set status back to active |
| Periodic review | Run `kb-freshness.py --list-stale` to find decayed entries for review |

### Freshness Management

Knowledge decays over time. Use the following to maintain freshness:

```bash
# Check overall freshness health
python scripts/kb-freshness.py --all

# List entries needing attention
python scripts/kb-freshness.py --list-stale       # Confidence decayed
python scripts/kb-freshness.py --list-expired     # Past expiry
python scripts/kb-freshness.py --list-superseded  # Replaced
python scripts/kb-freshness.py --list-deprecated  # No longer recommended

# Mark entries
python scripts/kb-freshness.py --mark-superseded patterns/old.md --by patterns/new.md
python scripts/kb-freshness.py --mark-expired lessons/outdated.md
python scripts/kb-freshness.py --mark-deprecated patterns/legacy.md
python scripts/kb-freshness.py --reactivate patterns/still-valid.md

# Create new entry that supersedes an old one (backlink auto-written)
python scripts/kb-log.py pattern "New Pattern" --status active \
  --supersedes "old-pattern.md" --stdin <<'EOF'
...
EOF

# Check a specific entry's freshness
python scripts/kb-freshness.py --check patterns/some-entry.md
```

### Confidence Decay Rules

Knowledge entries lose confidence over time based on their source:

| Source | Decay Rate | Rationale |
|--------|-----------|-----------|
| `user-stated` | No decay | Human knowledge is stable |
| `observed` | -1 per 60 days | Observations may become stale |
| `inferred` | -1 per 30 days | Inferred knowledge is less reliable |
| `cross-model` | -1 per 30 days | Cross-model knowledge has highest uncertainty |

## Anti-Patterns

- **Don't over-document** — Capture insights, not every detail
- **Don't Vague-document** — Be specific enough to be useful
- **Don't orphan entries** — Always link to index
- **Don't create near-duplicates** — Always run `--dedup-check` before creating
