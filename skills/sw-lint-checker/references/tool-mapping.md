# 语言→工具映射表 (Language → Tool Mapping)

## What Success Looks Like

Every changed file is classified to exactly one language, and every detected language has its tools run. No language is missed, no tool is skipped.

## Detection Table

Detect language by file extension first, then by filename pattern, then by shebang content.

| Language | Extensions | Filename Patterns | Shebang |
|----------|-----------|-------------------|---------|
| Python | `.py`, `.pyi`, `.pyx` | — | `#!/usr/bin/env python`, `#!/usr/bin/python` |
| JavaScript | `.js`, `.mjs`, `.cjs` | — | `#!/usr/bin/env node` |
| TypeScript | `.ts`, `.tsx`, `.mts`, `.cts` | — | — |
| Go | `.go` | — | — |
| Shell | `.sh`, `.bash`, `.zsh` | — | `#!/bin/bash`, `#!/bin/sh`, `#!/usr/bin/env bash` |
| Markdown | `.md`, `.mdx` | — | — |
| CSS | `.css`, `.scss`, `.less`, `.sass` | — | — |
| Dockerfile | — | `Dockerfile`, `Dockerfile.*`, `*.dockerfile` | — |
| YAML | `.yaml`, `.yml` | — | — |
| TOML | `.toml` | — | — |
| JSON | `.json` | — | — |

## Tool Table

For each language, the table lists all tools to run, in priority order (primary tool first).

| Language | Primary Tool | Check Command | Auto-Fix Command | Fallback / Alt Tool |
|----------|-------------|---------------|------------------|---------------------|
| Python | ruff | `ruff check .` | `ruff check --fix .` | `ruff format .` for formatting |
| JavaScript | eslint | `eslint .` | `eslint --fix .` | `prettier --check .` |
| TypeScript | eslint | `eslint .` | `eslint --fix .` | `tsc --noEmit` (type check, no fix) |
| Go | golangci-lint | `golangci-lint run ./...` | — (no auto-fix std) | `gofmt -d .` (format diff), `go vet ./...` |
| Shell | shellcheck | `shellcheck *.sh` | — (no auto-fix) | `shfmt -d .` (format diff) |
| Markdown | markdownlint | `markdownlint '**/*.md'` | `markdownlint --fix '**/*.md'` | — |
| CSS | stylelint | `stylelint '**/*.css'` | `stylelint --fix '**/*.css'` | `prettier --check .` |
| Dockerfile | hadolint | `hadolint Dockerfile*` | — (no auto-fix) | — |
| YAML | yamllint | `yamllint .` | — (format only) | `prettier --check '**/*.yaml'` |
| TOML | taplo | `taplo format --check .` | `taplo format .` | — |
| JSON | prettier | `prettier --check '**/*.json'` | `prettier --write '**/*.json'` | `jsonlint` (validate only) |

## Skip Rules

These file patterns should be excluded from all checks:

| Pattern | Reason |
|---------|--------|
| `node_modules/**` | Third-party dependencies |
| `dist/**`, `build/**`, `out/**` | Build output |
| `.git/**` | Git internals |
| `*.min.js`, `*.min.css` | Minified/bundled files |
| `*.lock`, `*-lock.*` | Lock files (auto-generated) |
| `*.pyc`, `__pycache__/**` | Python bytecode |
| `*.generated.*`, `*.gen.*` | Code generation output |
| `vendor/**` | Go/other vendored dependencies |
| `coverage/**`, `.nyc_output/**` | Test artifacts |
| `.worktree/**` | Harness worktree isolation |

## Tool Installation Check

Before running any tool, check it exists:

```bash
command -v <tool> >/dev/null 2>&1 || echo "TOOL_MISSING: <tool>"
```

If a primary tool is missing, try the fallback tool. If both are missing, report:
```
WARNING: No <language> lint tool available. Install <primary> (<install-cmd>) or skip.
```

Tools and their common install commands:

| Tool | Python pip | Node npm | System package |
|------|-----------|----------|---------------|
| ruff | `pip install ruff` | — | `apt install ruff` |
| eslint | — | `npm install -D eslint` | — |
| prettier | — | `npm install -D prettier` | — |
| golangci-lint | — | — | `go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest` |
| shellcheck | — | — | `apt install shellcheck` |
| markdownlint | — | `npm install -D markdownlint-cli` | — |
| stylelint | — | `npm install -D stylelint` | — |
| hadolint | — | — | `brew/apt install hadolint` |
| yamllint | `pip install yamllint` | — | `apt install yamllint` |
| taplo | — | `npm install -D @taplo/cli` | `cargo install taplo-cli` |
| jsonlint | — | `npm install -D jsonlint` | — |

## Parallel Execution

Languages are independent — run tools for different languages in parallel.

Within a single language:
- Primary tool first (lint check)
- If clean, run format check (if separate tool)
- If not clean, auto-fix runs before re-check

Example parallel grouping for a change touching Python + TypeScript + YAML:
```
Group 1 (parallel):
  - Python: ruff check + ruff format --check
  - TypeScript: eslint + prettier --check
  - YAML: yamllint

Then in parallel: auto-fix whatever failed.
Then in parallel: re-check fixed languages.
```
