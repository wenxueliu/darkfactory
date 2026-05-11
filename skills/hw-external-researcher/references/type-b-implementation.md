# TYPE B: Implementation Reference (实现参考)

## When to Activate

User asks questions like:
- "How does [library] implement [feature]?"
- "Show me the source code for [function]"
- "What is the internal logic of [algorithm]?"
- "How does [library] handle [edge case]?"
- "Walk me through the [module] implementation"

## Workflow

TYPE B research is source-code-driven. The primary evidence comes from the actual code in the repository, cited with GitHub permalinks.

---

## Phase 1: Clone and Identify (PARALLEL)

### Step 1: Find the Repository

If the repository URL is not provided, search for it:
```
Search: "[library-name] github repository"
```

Identify the canonical repository:
- npm: Check `package.json` → `repository` field
- PyPI: Check project page → `Homepage` or `Source` link
- Cargo: Check `Cargo.toml` → `repository` field
- Go: Module path IS the repository URL

### Step 2: Clone to Temp Directory (shallow, depth 1)

```bash
gh repo clone owner/repo ${TMPDIR:-/tmp}/repo-name -- --depth 1
```

Use `--depth 1` for speed. If you need git history (for blame/log), use a deeper clone:
```bash
gh repo clone owner/repo ${TMPDIR:-/tmp}/repo-name -- --depth 50
```

### Step 3: Get the Commit SHA for Permalinks

```bash
cd ${TMPDIR:-/tmp}/repo-name && git rev-parse HEAD
```

Alternative approaches:
```bash
# From GitHub API (useful before cloning)
gh api repos/owner/repo/commits/HEAD --jq '.sha'

# From a specific tag
gh api repos/owner/repo/git/refs/tags/v1.0.0 --jq '.object.sha'
```

**Store this SHA**. Every permalink needs it.

### Step 4: Parallel Setup

While cloning, run these in parallel to gather context:

```
Call 1: gh repo clone owner/repo ${TMPDIR:-/tmp}/repo -- --depth 1
Call 2: Search GitHub: "[function_name]" repo:"owner/repo"
Call 3: context7 get library docs for topic (if docs are relevant context)
```

---

## Phase 2: Navigate and Find (SEQUENTIAL)

### Step 1: Understand Project Structure

Read the top-level structure:
```bash
ls ${TMPDIR:-/tmp}/repo-name
```

Read key metadata files for context:
```
Read ${TMPDIR:-/tmp}/repo-name/README.md
Read ${TMPDIR:-/tmp}/repo-name/package.json (or Cargo.toml, setup.py, go.mod)
Read ${TMPDIR:-/tmp}/repo-name/CONTRIBUTING.md (often has architecture overview)
```

### Step 2: Locate the Target Code

Search within the cloned repo for the function/class/module:

```bash
# Search for function definition
cd ${TMPDIR:-/tmp}/repo-name

# Common patterns per language:
# TypeScript/JavaScript:
grep -r "function functionName" --include="*.ts" --include="*.js"
grep -r "export function functionName" --include="*.ts"

# Python:
grep -r "def function_name" --include="*.py"
grep -r "class ClassName" --include="*.py"

# Go:
grep -r "func FunctionName" --include="*.go"
grep -r "func (r \*Receiver) MethodName" --include="*.go"

# Rust:
grep -r "fn function_name" --include="*.rs"
grep -r "impl.*for.*Type" --include="*.rs"

# Java:
grep -r "public.*void methodName\|public.*class ClassName" --include="*.java"
```

If grep returns too many results, narrow by directory:
```bash
# Common source directories
# TypeScript/JavaScript: src/, lib/, packages/
# Python: src/, {package_name}/
# Go: internal/, pkg/, cmd/
# Rust: src/, crates/
# Java: src/main/java/
```

### Step 3: Read the Code

Once you find the target file, read it to understand the implementation:

```
Read {TMPDIR:-/tmp}/repo-name/path/to/file.ts
```

Focus on:
- The specific function/class implementation
- Related helper functions called from it
- Type definitions and interfaces
- Error handling paths
- Edge case handling

### Step 4: Trace Dependencies (if needed)

If the function delegates to other modules, trace the call chain:

```bash
# Find where helper is defined
grep -r "function helperName\|export.*helperName" --include="*.ts"

# Find where helper is called
grep -r "helperName(" --include="*.ts"
```

---

## Phase 3: Build Evidence (CRITICAL)

### Step 1: Construct GitHub Permalinks

For each piece of evidence, construct a permalink:
```
https://github.com/<owner>/<repo>/blob/<sha>/<filepath>#L<start>-L<end>

Example:
https://github.com/tanstack/query/blob/abc123def/packages/react-query/src/useQuery.ts#L42-L50
```

### Step 2: Cite with Context

Follow the mandatory citation format:

```markdown
**Claim**: useQuery deduplicates requests by queryKey internally.

**Evidence** ([source](https://github.com/tanstack/query/blob/abc123/packages/react-query/src/useQuery.ts#L42-L50)):
```typescript
const query = queryCache.build(cache, queryKey, {
  queryHash: hashQueryKeyByOptions(queryKey, options),
  // Same queryKey + same options = same queryHash = deduplication
});
```

**Explanation**: The cache layer uses `hashQueryKeyByOptions` to generate a hash from the queryKey and options. Requests with the same hash share the same query instance, preventing duplicate network calls. This is why using consistent queryKey structures is important.
```

### Step 3: Multiple Entry Points

If the implementation spans multiple files or modules, cite each relevant piece:

```markdown
**Claim**: The retry mechanism uses exponential backoff with a configurable maximum.

**Evidence 1** -- Retry timer calculation ([source](https://github.com/owner/repo/blob/sha/src/retry.ts#L15-L25)):
```typescript
const delay = Math.min(1000 * 2 ** attempt, options.maxDelay);
```

**Evidence 2** -- Retry decision logic ([source](https://github.com/owner/repo/blob/sha/src/query.ts#L80-L95)):
```typescript
if (failureCount < options.retry) {
  setTimeout(() => fetchQuery(query), delay);
}
```

**Explanation**: The delay doubles each attempt (exponential backoff: 1s, 2s, 4s, 8s...) but is capped at `maxDelay`. The retry counter `failureCount` is compared against `options.retry` to decide whether to keep retrying.
```

---

## Phase 4: Explain

After collecting evidence, provide a clear explanation:

### Output Template

```markdown
## How [Library] Implements [Feature]

### High-Level Overview

[2-3 sentences explaining the architecture/approach]

### Implementation Walkthrough

#### Step 1: Entry Point

**Evidence** ([source](https://github.com/owner/repo/blob/sha/src/index.ts#L10-L20)):
```typescript
// Entry point code
```

**Explanation**: [What happens when the function is called]

#### Step 2: Core Logic

**Evidence** ([source](https://github.com/owner/repo/blob/sha/src/core.ts#L42-L60)):
```typescript
// Core logic code
```

**Explanation**: [How the core algorithm works]

#### Step 3: Edge Case Handling

**Evidence** ([source](https://github.com/owner/repo/blob/sha/src/edge-cases.ts#L5-L15)):
```typescript
// Edge case handling code
```

**Explanation**: [How edge cases are handled]

### Key Design Decisions

1. **[Decision 1]**: [Why they chose this approach, evidence from code structure]
2. **[Decision 2]**: [Why, evidence from code or comments]

### Related Source Files

- [Main implementation](https://github.com/owner/repo/blob/sha/src/main.ts)
- [Helper utilities](https://github.com/owner/repo/blob/sha/src/utils.ts)
- [Type definitions](https://github.com/owner/repo/blob/sha/src/types.ts)

### Caveats

- This analysis is based on version [sha/tag]. Behavior may differ in other versions.
- [Any other caveats about the analysis]
```

---

## Special Cases

### Monorepo (multiple packages)

Navigate to the correct package directory first:
```bash
ls ${TMPDIR:-/tmp}/repo-name/packages/
cd ${TMPDIR:-/tmp}/repo-name/packages/package-name
```

Common monorepo structures:
- `packages/<name>/` (Lerna, Yarn workspaces)
- `crates/<name>/` (Rust workspace)
- `modules/<name>/` (Go workspace)

### Compiled/Transpiled Source

If the repo contains compiled output, find the source:
```bash
# TypeScript source is typically in src/, never in dist/ or lib/
# Rust source is in src/, never in target/
# Go source is at repo root or in cmd/internal/pkg/
# Java source is in src/main/java/, never in target/ or build/
```

### Old Codebase with No TypeScript/Modern Structure

```bash
# Find entry points through package.json
cat package.json | grep '"main"\|"module"\|"exports"'

# Find entry points through setup.py/setup.cfg
cat setup.py | grep 'packages\|py_modules'
```

### Private/Internal Repositories

If `gh repo clone` fails with permission errors:
- Search for mirrors or public forks
- Search for the package on npm/PyPI -- sometimes the published package contains source maps or unminified code
- Note to the user that the repository is private and analysis is limited
