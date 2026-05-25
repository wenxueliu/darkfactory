# TYPE C: Context and History (上下文和历史)

## When to Activate

User asks questions like:
- "Why was [feature] changed in [library]?"
- "What is the history of [module/function]?"
- "What issue/PR led to this implementation?"
- "Who decided this and why?"
- "When was [feature] introduced/removed?"
- "What was the discussion around [decision]?"
- "Show me the related issues and PRs for [change]"

## Workflow

TYPE C research investigates the **why** behind code: issues, pull requests, release notes, git history. It combines GitHub Issues/PRs API with git log/blame to reconstruct the timeline and rationale.

---

## Phase 1: Gather Context (PARALLEL)

Run these searches in parallel to build a comprehensive picture:

### Search Issues and PRs

```bash
# Search for related issues
gh search issues "keyword" --repo owner/repo --state all --limit 15

# Search for related PRs (merged PRs indicate completed changes)
gh search prs "keyword" --repo owner/repo --state merged --limit 15

# Search for open PRs (ongoing discussions)
gh search prs "keyword" --repo owner/repo --state open --limit 5
```

Use meaningful keywords:
- Feature/module name: `"useQuery"`, `"queryClient"`
- File path: `"src/core/query.ts"`
- Concept: `"cache invalidation"`, `"stale time"`
- Error message: `"TypeError: Cannot read property"`

### Search Releases

```bash
# Get recent releases for changelog context
gh api repos/owner/repo/releases --jq '.[0:10] | .[] | {tag_name, published_at, name}'

# Get latest release
gh api repos/owner/repo/releases/latest
```

### Clone with History (depth depends on how far back you need to go)

```bash
# For recent changes (last ~50 commits)
gh repo clone owner/repo ${TMPDIR:-/tmp}/repo -- --depth 50

# For deeper history on a specific file
gh repo clone owner/repo ${TMPDIR:-/tmp}/repo -- --depth 100
```

### Parallel Execution Pattern

```
Call 1: gh search issues "keyword" --repo owner/repo --state all --limit 15
Call 2: gh search prs "keyword" --repo owner/repo --state merged --limit 15
Call 3: gh repo clone owner/repo ${TMPDIR:-/tmp}/repo -- --depth 50
Call 4: gh api repos/owner/repo/releases --jq '.[0:5]'
```

---

## Phase 2: Trace the Timeline (SEQUENTIAL, once repo is cloned)

### Step 1: Git Log for Overview

```bash
cd ${TMPDIR:-/tmp}/repo

# View recent commits affecting a specific file
git log --oneline -n 20 -- path/to/file

# View commits with dates for timeline
git log --format="%h %ad %s" --date=short -n 20 -- path/to/file

# Filter by keyword in commit message
git log --oneline --grep="keyword" -n 20
```

### Step 2: Git Blame for Line-Level History

```bash
# Who last changed each line and when
git blame path/to/file -L 10,50

# With date and commit message
git blame --date=short path/to/file -L 10,50

# Show the specific commit that changed a line
git log -1 <commit-hash>
```

### Step 3: Examine Specific Commits

```bash
# View full commit diff
git show <commit-hash>

# View commit message only (often references issues/PRs)
git log --format="%B" -1 <commit-hash>

# View commits before and after this one for context
git log --oneline <commit-hash>~3..<commit-hash>
```

### Step 4: Cross-Reference with Issues/PRs

Many commit messages reference GitHub issues or PRs:
```
fix: resolve stale closure in useCallback (#1234)
```

Extract these references and look up the actual issues:
```bash
gh issue view 1234 --repo owner/repo --comments
gh pr view 1234 --repo owner/repo --comments

# View the full diff of a PR
gh api repos/owner/repo/pulls/1234/files --jq '.[].filename'
```

---

## Phase 3: Synthesize Timeline

### Timeline Reconstruction

Build a chronological narrative:

```markdown
## History of [Feature/Change]

### Timeline

| Date | Event | Source |
|------|-------|--------|
| 2023-06 | Feature introduced in v3.1.0 | [PR #1234](https://github.com/owner/repo/pull/1234) |
| 2023-09 | Bug fix: stale closure | [Commit abc123](https://github.com/owner/repo/commit/abc123) |
| 2024-01 | Refactored in v4.0.0 | [PR #2345](https://github.com/owner/repo/pull/2345) |
| 2024-03 | Performance regression reported | [Issue #3456](https://github.com/owner/repo/issues/3456) |
| 2024-05 | Regression fixed in v4.1.0 | [PR #4567](https://github.com/owner/repo/pull/4567) |
```

### Decision Rationale

For each significant change, explain WHY it was made:

```markdown
### v4.0.0 Refactor: Why the API Changed

**Original Implementation** (v3.x):
**Evidence** ([commit abc123](https://github.com/owner/repo/commit/abc123)):
```typescript
// v3.x code
function oldWay() { ... }
```

**Problem Identified**:
**Evidence** ([Issue #2000](https://github.com/owner/repo/issues/2000)):
> "The current API causes [specific problem] because [reason]"

Discussion summary: The maintainers discussed alternatives in [Issue #2000] and [PR #2001]. The chosen approach was...

**New Implementation** (v4.x):
**Evidence** ([PR #2345](https://github.com/owner/repo/pull/2345)):
```typescript
// v4.x code
function newWay() { ... }
```

**Trade-offs Discussed**: [from PR comments]
- Pro: [benefit]
- Con: [cost, and why it was accepted]
```

---

## Phase 4: Output

### Output Template

```markdown
## Why Was [X] Changed?

### Summary

[1-2 sentences answering the question directly]

### Timeline

[Table showing key events in chronological order]

### The Original Problem

**Evidence** ([Issue #1234](https://github.com/owner/repo/issues/1234)):
> [Relevant quote from the issue]

The problem was [explanation].

### Discussion and Decision

**Evidence** ([PR #2345](https://github.com/owner/repo/pull/2345)):
> [Relevant quote from PR discussion]

The maintainers decided to [decision] because [rationale].

**Alternative considered** ([PR comment](https://github.com/owner/repo/pull/2345#discussion_r12345)):
> [Quote about alternative approach]
Rejected because [reason].

### The Implementation

**Evidence** ([commit abc123](https://github.com/owner/repo/commit/abc123)):
```typescript
// Key change in the implementation
```

### Related Discussions

- [Issue #3456](https://github.com/owner/repo/issues/3456): [Brief description of related issue]
- [PR #4567](https://github.com/owner/repo/pull/4567): [Brief description of follow-up change]

### Key Takeaways

1. [Lesson or insight from this history]
2. [Implication for users of this library]
```

---

## Special Cases

### No Issues/PRs Found

If the repository does not use GitHub Issues actively:
```bash
# Check for discussions tab
gh api repos/owner/repo/discussions --jq '.[0:10]'

# Check commit messages for context (often contain rationale)
git log --format="%B" -n 50 -- path/to/file

# Check for CHANGELOG
cat ${TMPDIR:-/tmp}/repo/CHANGELOG.md
cat ${TMPDIR:-/tmp}/repo/CHANGES.md
```

### Monorepo -- Change in a Specific Package

Narrow git log to the package directory:
```bash
git log --oneline -n 20 -- packages/package-name/
git blame packages/package-name/src/file.ts
```

Search issues with the package name:
```bash
gh search issues "package-name" --repo owner/repo --state all
```

### Very Old Change (before GitHub migration)

If the project migrated from another platform (SourceForge, Google Code, etc.), note that:
- Early history may only exist in commit messages
- Look for `[svn]` or `[git-svn]` tags in old commits
- Note in your output that pre-GitHub history is limited

### Breaking Change Analysis

If the user asks specifically about a breaking change:
```bash
# Find the version where it was introduced
git log --oneline --grep="BREAKING CHANGE" -n 20
git log --oneline --grep="breaking" -n 20

# Look for migration guides
gh search issues "migration guide" --repo owner/repo
Search GitHub: "[library] migration vX to vY"
```
