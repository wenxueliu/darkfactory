# TYPE A: Conceptual Question (概念性问题)

## When to Activate

User asks questions like:
- "How do I use [library]?"
- "What is the best practice for [framework feature]?"
- "Show me examples of [library] usage"
- "How do I configure [tool]?"
- "What API does [library] provide for [task]?"

## Workflow

TYPE A research follows a **two-phase** process: Documentation Discovery (sequential) -> Targeted Investigation (parallel).

---

## Phase 1: Documentation Discovery (SEQUENTIAL)

Before searching code, find and understand the documentation landscape. This prevents random searching and ensures you are looking at the right version.

### Step 1: Find Official Documentation

Search for the official documentation site. Distinguish official docs from blogs, tutorials, and third-party content.

```
Search for: "[library-name] official documentation"
Search for: "[library-name] docs"
```

What to look for:
- Domains like `docs.example.com`, `example.dev/docs`, `example.readthedocs.io`
- GitHub Pages: `owner.github.io/repo-name`
- Official project websites with `/docs/` paths
- npm/PyPI/Cargo pages linking to documentation

**Avoid**: Medium posts, dev.to articles, unofficial tutorials, YouTube videos.

If the library is small or has no official docs, note this and proceed directly to source code analysis (TYPE B-style).

### Step 2: Version Check

If the user specified a version (e.g., "React 18", "Next.js 14", "v2.x"), confirm version-specific documentation.

```
Fetch: {official_docs_url}/versions
Fetch: {official_docs_url}/v{major_version}
Fetch: {official_docs_url}/releases
```

Many documentation sites have versioned paths:
- VitePress: `/v2/guide/`, `/v3/guide/`
- Docusaurus: `/docs/2.x/`, `/docs/next/`
- ReadTheDocs: `/en/stable/`, `/en/v2.1.0/`
- Next.js: `/docs/` always shows current, but old versions at `/docs/pages/` subdirectory

If versioned docs are not found, note in your response and fall back to latest.

### Step 3: Sitemap Discovery

Understand the documentation structure before deep-reading individual pages.

```
Fetch: {official_docs_url}/sitemap.xml
```

Fallback URLs if `/sitemap.xml` returns 404:
- `/sitemap-0.xml`
- `/sitemap_index.xml`
- `/docs/sitemap.xml`
- `/en/sitemap.xml`

Parse the sitemap to understand:
- **Top-level sections**: Getting Started, Guides, API Reference, Configuration, Examples
- **Relevant pages**: Which URLs match the user's specific question
- **Structure**: How the documentation is organized

If no sitemap is available, fetch the docs index page and parse the navigation/sidebar.

### Step 4: Targeted Investigation

Now that you know WHERE to look, fetch the specific pages relevant to the user's question.

```
Fetch: {specific_doc_page_from_sitemap_1}
Fetch: {specific_doc_page_from_sitemap_2}
```

For API reference questions:
- Look up specific API pages (e.g., `/docs/api/useQuery`, `/reference/useState`)
- Check the type definitions if available

For usage/pattern questions:
- Look up guide pages (e.g., `/docs/guides/queries`, `/docs/basics/configuration`)
- Check example pages (e.g., `/docs/examples/basic`)

---

## Phase 2: Execution (PARALLEL)

Once you have identified the right documentation targets, execute searches in parallel:

### Tools and Their Uses

**Official Documentation (primary source):**
- Use `context7` to resolve library ID and query docs
- Use `webfetch` to read specific documentation pages identified from sitemap

**Real-world Usage Examples (secondary source):**
```
Search GitHub for usage patterns:
- Search: "[library-name] [function-name](" language:[TypeScript]
- Search: "import { [function] } from '[library]'" language:[JavaScript]
- Search: "[config-key]:" language:[YAML]
```

**Version-specific Queries (if applicable):**
```
Search: "[library-name] v{version} [topic]"
Search: "[library-name] migration guide v{old} to v{new}"
```

### Parallel Execution Pattern

Run these in parallel (minimum 2 calls):

```
Call 1: webfetch(targeted_doc_page_from_sitemap)
Call 2: context7 query docs for specific topic
Call 3: Search GitHub for real-world usage examples (optional, when docs are insufficient)
```

You can also vary the search queries:
```
# Good -- different angles
Search GitHub: "useQuery(" language:[TypeScript]
Search GitHub: "queryOptions" language:[TypeScript]
Search GitHub: "staleTime:" language:[TypeScript]

# Bad -- same pattern repeated
Search GitHub: "useQuery" language:[TypeScript]
Search GitHub: "useQuery" language:[TypeScript]
```

---

## Phase 3: Evidence Synthesis

After collecting information:

1. **Summarize the answer** -- what does the user need to know?
2. **Cite official docs** -- link to the specific documentation page with version info
3. **Provide code examples** -- from docs and real-world usage, with GitHub permalinks where applicable
4. **Note version-specific caveats** -- if behavior changed across versions, mention this
5. **Mark uncertainty** -- if something is unclear or speculative, state it

### Output Template

```markdown
## Answer

[Clear, direct answer to the question]

## How to Use

```[language]
// Code example with explanation
```

**Evidence** ([source](https://docs.example.com/v2/api/useQuery)):
> Documentation states: "useQuery accepts a queryKey and queryFn..."

**Explanation**: [What this means in practice]

## Best Practices

1. **Practice 1**: [explanation with doc reference]
2. **Practice 2**: [explanation with doc reference]

## Real-world Examples

**Evidence** ([source](https://github.com/owner/repo/blob/abc123/src/app.tsx#L20-L30)):
```[language]
// Real-world usage from OSS project
```

## Version Notes (if applicable)

- v2.x: [behavior]
- v1.x: [different behavior -- specify if user needs to care]

## Sources

- [Official Docs: API Reference](https://docs.example.com/v2/api)
- [Official Docs: Guides](https://docs.example.com/v2/guides)
- [GitHub: Example Implementation](https://github.com/owner/repo/blob/abc123/path)
```

---

## Special Cases

### Library has no official docs
Skip Doc Discovery. Search for README in the repo:
```
gh repo clone owner/repo ${TMPDIR:-/tmp}/repo -- --depth 1
Read ${TMPDIR:-/tmp}/repo/README.md
Read ${TMPDIR:-/tmp}/repo/CONTRIBUTING.md
```
Also search for usage in other projects that depend on this library.

### Library is very popular (thousands of search results)
Narrow down by language, stars, or recency:
```
Search GitHub: "[function]" language:[TypeScript] stars:>100
```

### User asking about migration between versions
Focus on migration guides and changelogs:
```
Fetch: {docs_url}/migration-guide
Fetch: {docs_url}/changelog
Search: "[library] v{old} to v{new} migration guide"
```

### User asking about alternative libraries
Compare official docs side by side:
```
Fetch: {lib_a_docs_url}/introduction
Fetch: {lib_b_docs_url}/introduction
Search GitHub: "[lib_a] vs [lib_b]" language:[Markdown]
```
