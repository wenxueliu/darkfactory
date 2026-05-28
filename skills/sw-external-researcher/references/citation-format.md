# Citation Format (引用格式规范)

Every factual claim made by the sw-external-researcher MUST include a citation. This reference defines the standard citation format and the rules for constructing evidence permalinks.

---

## Mandatory Citation Format

Every claim must follow this exact structure:

```markdown
**Claim**: [The assertion being made]

**Evidence** ([source](URL)):
```[language]
// The actual code, documentation text, or data that supports the claim
```

**Explanation**: [Why this evidence supports the claim, what it means in context]
```

### Example -- Good Citation

```markdown
**Claim**: React Query's `useQuery` hook automatically deduplicates requests with the same queryKey within a QueryClientProvider scope.

**Evidence** ([source](https://github.com/TanStack/query/blob/3e58321f/packages/react-query/src/useQuery.ts#L42-L55)):
```typescript
const query = queryClient.getQueryCache().build(
  queryClient,
  { queryKey, queryHash: hashQueryKeyByOptions(queryKey, options) },
);
```

**Explanation**: The cache layer generates a stable hash from the queryKey and options. Multiple components calling `useQuery` with identical keys receive the same cached query instance, preventing duplicate network requests. This is the core deduplication mechanism.
```

### Example -- Documentation Citation

```markdown
**Claim**: Next.js 14 App Router supports streaming with React Suspense boundaries, allowing progressive page rendering.

**Evidence** ([source](https://nextjs.org/docs/app/building-your-application/routing/loading-ui-and-streaming)):
> "With Server Components, you can progressively render and stream parts of the UI. This means the user can see parts of the page immediately while the rest loads."

**Explanation**: Streaming is a built-in feature of the App Router, not an opt-in. Any `loading.js` file automatically creates a Suspense boundary that enables streaming for that route segment.
```

---

## GitHub Permalink Construction

### Format

```
https://github.com/<owner>/<repo>/blob/<commit-sha>/<filepath>#L<start>-L<end>
```

### Components

| Component | Description | Example |
|-----------|-------------|---------|
| `owner` | GitHub organization or user | `TanStack`, `facebook` |
| `repo` | Repository name | `query`, `react` |
| `commit-sha` | Full commit SHA (40 characters) | `3e58321f9c2c1e5a8b7d6e4f3a2c1b5d8e7f6a9b` |
| `filepath` | Path from repository root | `packages/react-query/src/useQuery.ts` |
| `#L<start>` | Starting line number | `#L42` |
| `-L<end>` | Ending line number (for ranges) | `-L55` |

### Line Reference Rules

- **Single line**: `#L42` -- preter when citing a specific statement
- **Line range**: `#L42-L55` -- preter when citing a block of code
- **No line numbers**: `https://github.com/owner/repo/blob/sha/filepath` -- only if the entire file is relevant (rare)

### Examples of Valid Permalinks

```
# Single line
https://github.com/tanstack/query/blob/abc123def/packages/react-query/src/useQuery.ts#L42

# Line range
https://github.com/tanstack/query/blob/abc123def/packages/react-query/src/useQuery.ts#L42-L55

# Deep nested path
https://github.com/facebook/react/blob/def456abc/packages/react-reconciler/src/ReactFiberHooks.js#L100-L130

# Root-level file
https://github.com/golang/go/blob/789abc123/src/net/http/client.go#L200-L250
```

---

## Getting the Commit SHA

The SHA is critical -- it makes the link permanent. Without it, the default branch (`main`/`master`) may change, breaking line references.

### Method 1: From Cloned Repository (most reliable)

```bash
git rev-parse HEAD
# Output: 3e58321f9c2c1e5a8b7d6e4f3a2c1b5d8e7f6a9b
```

### Method 2: From GitHub API (when you cannot clone)

```bash
# Default branch HEAD
gh api repos/owner/repo/commits/HEAD --jq '.sha'

# Specific branch
gh api repos/owner/repo/commits/main --jq '.sha'

# Specific tag
gh api repos/owner/repo/git/refs/tags/v1.0.0 --jq '.object.sha'
```

### Method 3: From GitHub Web UI

Navigate to the file on GitHub, press `y` (or click the link with the commit SHA in the URL bar). GitHub will convert the URL from the branch-based form to the SHA-based form.

```
# Branch-based (NOT permanent):
https://github.com/owner/repo/blob/main/src/file.ts#L42

# After pressing 'y' (permanent):
https://github.com/owner/repo/blob/3e58321f/src/file.ts#L42
```

### Method 4: Short SHA (7-8 characters)

GitHub accepts short SHAs:
```
https://github.com/tanstack/query/blob/3e58321/packages/react-query/src/useQuery.ts#L42
```

Use full SHAs (40 chars) when possible -- they are more robust. Short SHAs can become ambiguous as the repository grows.

---

## Official Documentation URL Rules

### Do: Link to Specific Pages

```
Good: https://nextjs.org/docs/app/building-your-application/routing/loading-ui-and-streaming
Good: https://tanstack.com/query/v5/docs/framework/react/guides/queries
Good: https://docs.python.org/3/library/asyncio-task.html#coroutines
```

### Do: Use Versioned URLs

```
Good: https://tanstack.com/query/v5/docs/...           (version 5)
Good: https://nextjs.org/docs/app/...                   (current, App Router)
Good: https://docs.python.org/3/library/...             (Python 3)
```

### Don't: Link to Generic Pages

```
Bad: https://nextjs.org/docs                              (not specific)
Bad: https://tanstack.com/query/docs                      (no version)
Bad: https://react.dev                                    (not a specific page)
```

### Don't: Link to Third-Party Sites

```
Bad: https://blog.logrocket.com/...                       (not official)
Bad: https://medium.com/...                               (not official)
Bad: https://dev.to/...                                   (not official)
```

**Exception**: If no official documentation exists, you may cite a community resource, but explicitly note: "**Note**: No official documentation available. This source is a community resource and may be outdated."

---

## GitHub Issues and PRs

### Issue Citation

```markdown
**Evidence** ([Issue #1234](https://github.com/owner/repo/issues/1234)):
> "The current behavior causes [specific problem] because [reason]."
```

### PR Citation

```markdown
**Evidence** ([PR #2345](https://github.com/owner/repo/pull/2345)):
> "This PR introduces [feature] by [approach]."

// For a specific file changed in the PR:
**Evidence** ([PR #2345 - files changed](https://github.com/owner/repo/pull/2345/files#diff-hash)):
```typescript
// Code from the PR
```
```

### Issue/PR Comment Citation

```markdown
**Evidence** ([Issue comment](https://github.com/owner/repo/issues/1234#issuecomment-12345678)):
> "Maintainer's response: [quote]"
```

---

## Release and Changelog Citation

```markdown
**Evidence** ([Release v4.0.0](https://github.com/owner/repo/releases/tag/v4.0.0)):
> "BREAKING CHANGE: The `options` parameter has been moved from second to third argument."
```

---

## Citation Quality Rules

### Mandatory

1. **Every factual claim must have at least one citation.** No claim without evidence.
2. **Cite the exact line(s)** that support the claim. Do not cite an entire file unless the claim is about the file as a whole.
3. **Include code or quoted text** in the evidence block. The citation is useless without the actual content.
4. **Use permanent links** (commit SHA, not branch name). Branch-based links rot.

### Recommended

1. **Prefer official sources** over community sources.
2. **Multiple citations** for important or complex claims (e.g., code evidence + docs evidence).
3. **Version context** -- mention which version you are citing.

### Anti-patterns

```
# BAD: Claim without citation
**Claim**: React Query uses stale-while-revalidate.

# BAD: Citation without content
**Evidence** ([source](https://github.com/owner/repo/blob/sha/file.ts#L10)):

# GOOD: Complete citation
**Claim**: React Query uses stale-while-revalidate strategy.

**Evidence** ([source](https://github.com/TanStack/query/blob/abc123/packages/react-query/src/useQuery.ts#L80-L95)):
```typescript
// Immediately return cached data (stale)
this.dispatch({ type: 'fetch' });
// Then revalidate in background
return this.fetchQuery();
```

**Explanation**: The hook immediately dispatches cached/stale data to the component (stale), then triggers a background refetch (revalidate). This is the stale-while-revalidate pattern.
```

---

## Uncertainty Marking

When you cannot find definitive evidence for a claim:

```markdown
**Uncertainty**: I could not find the exact implementation of [X] in the source code. The repository structure suggests [hypothesis based on available evidence], but this should be verified.

**Partial Evidence** ([source](URL)):
```typescript
// Related code that supports but does not definitively prove the claim
```

**Next Steps**: To verify this, one would need to [specific action to confirm].
```

Rules for uncertainty:
- Never fabricate evidence to fill gaps
- Clearly separate "what is known" from "what is inferred"
- If the uncertainty is about something critical, recommend the user verify
- Do not present speculation as fact under any circumstance
