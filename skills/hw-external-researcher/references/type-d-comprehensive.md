# TYPE D: Comprehensive Research (全面研究)

## When to Activate

User asks questions like:
- "Tell me everything about [library/feature]"
- "Deep dive into [topic]"
- "How does [library X] compare to [library Y]?"
- "What are the trade-offs between [approach A] and [approach B]?"
- "Give me a comprehensive overview of [ecosystem/tool]"
- Complex or ambiguous requests that do not fit cleanly into TYPE A/B/C

## Workflow

TYPE D is the most intensive research mode, combining documentation discovery with source code analysis, issue research, and real-world usage patterns.

---

## Phase 1: Request Decomposition (SEQUENTIAL, planning only)

Break down the complex question into sub-questions:

```
Complex: "Give me a comprehensive overview of React Query"

Sub-questions:
1. What is React Query? What problem does it solve? (TYPE A)
2. How does the caching mechanism work internally? (TYPE B)
3. What are the latest features and API changes? (TYPE A + C)
4. How does it compare to SWR and Apollo Client? (TYPE A, comparative)
5. What are real-world usage patterns and pitfalls? (TYPE A, examples)
```

Each sub-question maps to a TYPE A, B, or C workflow. Coordinate these for maximum parallelism.

---

## Phase 2: Documentation Discovery (SEQUENTIAL, shared across sub-questions)

Execute Documentation Discovery ONCE for all sub-questions. This is a shared foundation.

### Step 1: Find Official Documentation

```
Search: "[library-name] official documentation"
Search: "[library-name] docs"
```

Identify:
- Official docs URL
- GitHub repository URL
- npm/PyPI/Cargo package page URL (for metadata)

### Step 2: Version Check

```
Fetch: {official_docs_url}/versions
Fetch: {official_docs_url}/releases
```

Get the latest version and note any version-specific doc paths.

### Step 3: Sitemap Discovery

```
Fetch: {official_docs_url}/sitemap.xml
```

From the sitemap, map out the documentation structure:
- **Getting Started** -- basic concepts, quick start
- **Guides** -- in-depth guides for each feature area
- **API Reference** -- detailed API documentation
- **Examples** -- usage examples
- **Migration** -- upgrade guides between versions
- **FAQ/Troubleshooting** -- common problems

Identify which documentation sections are relevant to each sub-question.

---

## Phase 3: Parallel Deep Research

Execute research for ALL sub-questions in parallel. This is the key optimization -- gather everything at once.

### Execution Pattern (3-6 parallel calls)

```
// Documentation (from sitemap discovery)
Call 1: webfetch(doc_page_for_subquestion_1)
Call 2: webfetch(doc_page_for_subquestion_2)

// Context7 for in-depth doc queries
Call 3: context7 query docs for subquestion topic

// Code Search
Call 4: Search GitHub: "[pattern1]" language:[TypeScript]
Call 5: Search GitHub: "[pattern2]" language:[TypeScript]

// Repository Analysis
Call 6: gh repo clone owner/repo ${TMPDIR:-/tmp}/repo -- --depth 1
```

### Parallel Calls Per Research Area

**For understanding the architecture (TYPE B):**
```
Search GitHub: "function [mainEntryPoint]" repo:"owner/repo"
Search GitHub: "[key]:" language:[TypeScript]
```

**For finding real-world examples (TYPE A):**
```
Search GitHub: "import { [mainExport] } from '[library]'"
Search GitHub: "[functionName](" language:[TypeScript] stars:>50
```

**For understanding recent changes (TYPE C):**
```
gh search issues "[library]" --repo owner/repo --state all --limit 10
gh api repos/owner/repo/releases --jq '.[0:5]'
```

**For comparative research (TYPE A comparative):**
```
Search: "[library1] vs [library2] comparison"
Fetch: {library2_official_docs_url}/introduction
```

---

## Phase 4: Synthesis and Organization

### Organize Findings

Group findings by sub-topic, not by source:

```markdown
## Comprehensive Research: [Topic]

### 1. Overview and Core Concepts

**What is [Library]?**
[Definition with official docs citation]

**Core Concepts:**
- **Concept 1**: [explanation, with doc reference]
- **Concept 2**: [explanation, with doc reference]
- **Concept 3**: [explanation, with doc reference]

### 2. Architecture and Internals

**High-Level Architecture:**
[Explanation of how the library is structured]

**Evidence** ([source](https://github.com/owner/repo/blob/sha/src/index.ts#L1-L20)):
```typescript
// Architecture-defining code
```

**Key Mechanisms:**
1. **[Mechanism 1]**: [how it works, with permalink evidence]
2. **[Mechanism 2]**: [how it works, with permalink evidence]

### 3. API and Usage Patterns

**Core API Surface:**
| API | Purpose | Documentation |
|-----|---------|--------------|
| `functionA()` | [purpose] | [docs link] |
| `functionB()` | [purpose] | [docs link] |

**Common Usage Pattern:**

**Evidence** ([source](https://docs.example.com/guides/basic-usage)):
```typescript
// Basic usage example
```

**Real-World Example:**

**Evidence** ([source](https://github.com/some-oss-project/blob/sha/src/app.tsx#L30-L50)):
```typescript
// Production usage from a well-known project
```

### 4. Recent Changes and Evolution

**Timeline:**
| Version | Date | Key Change | Source |
|---------|------|------------|--------|
| v4.0 | 2024-01 | [change] | [PR link] |
| v3.0 | 2023-06 | [change] | [PR link] |

**Current Direction** (from recent issues/PRs):
- [What's being actively developed]
- [Known issues being addressed]
- [Roadmap items]

### 5. Comparison with Alternatives (if applicable)

**[Library A] vs [Library B] vs [Library C]:**

| Dimension | Library A | Library B | Library C |
|-----------|-----------|-----------|-----------|
| Bundle Size | X kB | Y kB | Z kB |
| API Style | [style] | [style] | [style] |
| Caching | [approach] | [approach] | [approach] |
| Ecosystem | [size/maturity] | [size/maturity] | [size/maturity] |
| Learning Curve | [rating] | [rating] | [rating] |

**When to Use Each:**
- **Library A**: Best for [scenario], because [reason with citation]
- **Library B**: Best for [scenario], because [reason with citation]
- **Library C**: Best for [scenario], because [reason with citation]

### 6. Best Practices and Pitfalls

**Dos:**
1. **[Practice 1]**: [explanation] -- [source](URL)
2. **[Practice 2]**: [explanation] -- [source](URL)

**Don'ts:**
1. **[Anti-pattern 1]**: [explanation + what to do instead] -- [source](URL)
2. **[Anti-pattern 2]**: [explanation + what to do instead] -- [source](URL)

**Common Pitfalls:**
- **[Pitfall 1]**: [description, why it happens, how to avoid]
**Evidence** ([GitHub Issue](https://github.com/owner/repo/issues/1234)):
> [Relevant quote from issue discussion]

### 7. Recommendations

[If the user is making a decision, provide evidence-based recommendations]

**For [use case 1]**: Use [Library X] because [reason with evidence].
**For [use case 2]**: Use [Library Y] because [reason with evidence].

### 8. Sources

- [Official Documentation](https://docs.example.com)
- [GitHub Repository](https://github.com/owner/repo)
- [Specific doc page 1](https://docs.example.com/page1)
- [GitHub source file 1](https://github.com/owner/repo/blob/sha/path)
- [Related Issue](https://github.com/owner/repo/issues/1234)
- [Related PR](https://github.com/owner/repo/pull/2345)
```

---

## Coordination Patterns

### Sequential Gates

Some sub-questions depend on answers to others:

```
Sub-question 1 (What is X?) MUST complete before:
  Sub-question 3 (How does X compare to Y?)
  Sub-question 4 (What are X's limitations?)

Sub-question 2 (How does X work?) CAN run in parallel with:
  Sub-question 1 (What is X?)
  Sub-question 5 (What are real-world examples of X?)
```

Dependency resolution:
1. Start with all independent sub-questions in parallel
2. When foundational sub-questions complete, launch dependent sub-questions
3. Synthesize all findings together

### When to Stop

TYPE D research can expand indefinitely. Set boundaries:

- **Time/rounds**: After 3 rounds of investigation, synthesize what you have and ask the user if they want deeper investigation into any specific area.
- **Depth**: Two levels of depth is usually sufficient. You do not need to trace every function call chain to its root.
- **Scope**: If the question covers a very large library, focus on the most commonly used parts (80/20 rule).

### Managing Output Size

For very comprehensive research, use progressive disclosure:

1. **First response**: Executive summary + detailed findings for top 3 sub-questions
2. **Offer expansion**: "I have additional findings on [sub-topic 4, 5, 6]. Would you like me to elaborate on any of these?"
3. **Full report**: Make the complete report available as structured markdown

---

## Special Cases

### Comparative Research (Library A vs Library B)

Add comparative criteria:
```markdown
| Criteria | Library A | Library B | Winner |
|----------|-----------|-----------|--------|
| Performance | [data + source] | [data + source] | [winner] |
| Bundle size | [data + source] | [data + source] | [winner] |
| API design | [analysis + source] | [analysis + source] | [winner] |
| Ecosystem | [data + source] | [data + source] | [winner] |
| Documentation | [analysis + source] | [analysis + source] | [winner] |
| Community | [data + source] | [data + source] | [winner] |

**Overall**: [Which to choose for which scenario, not a universal winner]
```

### Ecosystem Research

When asked about an entire ecosystem (e.g., "What is the state of React meta-frameworks?"):
1. List the key players
2. For each player: brief overview + official docs link + GitHub link
3. Comparison table
4. Trends (where is the ecosystem heading?)
5. Recommendations by use case

### Unknown Library/Domain

If you encounter a library or domain you have limited information about:
1. Start with broad searches to understand the landscape
2. Identify the authoritative sources (official docs, main repos)
3. Be explicit about the limits of your research: "I found these 3 primary sources. There may be additional community resources not covered here."
4. Mark speculative conclusions clearly
