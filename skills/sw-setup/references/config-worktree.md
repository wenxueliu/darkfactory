# ConfigureWorktree: 配置Worktree目录

## What Success Looks Like

Worktree directory exists, is properly configured, and is gitignored.

## Your Approach

### Create Directory

```bash
mkdir -p {worktree_base}
```

### Verify Gitignore

```bash
# Check if in gitignore
git check-ignore {worktree_base}

# If not, add to .gitignore
echo "{worktree_base}" >> .gitignore
```

### Update Config

Write worktree_base to config:
```yaml
hw:
  worktree_base: {worktree_base}
```

## Verification

| Check | Expected |
|-------|----------|
| Directory exists | true |
| In gitignore | true |
| Config written | true |

## Output

Report verification results.
