# adr-gen — signal filter, recency injection, prompt contract

`adr-gen` has four input modes. All of them pass through the same pipeline:
**signal filter → recency digest → LLM fill → validation → human gate →
write + index**.

```bash
adr-gen --from-commit HEAD                 # commit; HEAD when the value is omitted
adr-gen --from-commit 4f2c1ab --dry-run
adr-gen --from-text "网关从 Node 迁移到 Rust"
adr-gen --from-file requirements/REQ-1024.md
adr-gen --all-commits --dry-run            # preview a whole-history backfill
adr-gen --from-text "..." --no-llm         # offline scaffold, deterministic
```

## 1. Signal filter (`assess`)

Explicit text/file input is always significant by definition. Commits are
scored; the ADR is generated only when the score reaches **3**.

| Signal | Points |
| --- | --- |
| database migration or `schema.sql`/`*.sql` | +5 |
| deployment/infrastructure (`Dockerfile`, `docker-compose`, `k8s/`, `helm/`, `*.tf`, workflows) | +4 |
| module/file deleted | +4 |
| dependency/build manifest (`pyproject.toml`, `package.json`, `go.mod`, `pom.xml`, …) | +3 |
| authentication/security path | +3 |
| module/file renamed | +3 |
| new top-level module | +3 |
| module boundary path (`api/`, `handlers/`, `adapters/`, `domain/`, …) | +2 |
| commit message contains an architecture verb (`migrate`, `switch`, `replace`, `adopt`, `remove`, `extract`, …) | +2 |
| commit message names a domain concern (`database`, `queue`, `gateway`, `auth`, …) | +2 (keyword total capped at 4) |
| ≥15 meaningful files | +1 |

Noise (never scored): `docs/`, `tests/`, `.github/`, `LICENSE`/`CHANGELOG`,
`*.md`/`*.rst`, images, lockfiles (`package-lock.json`, `poetry.lock`,
`go.sum`, …). A commit that touches only noise is skipped with an explanation:

```text
adr-gen: skipped: change is not architecturally significant (score 0 < 3)
  - only docs/tests/assets/lockfiles changed
  use --force to generate anyway
```

`--force` bypasses the filter, not the validation or the human gate. Use it
when the decision is real but the diff is small (for example a one-line
dependency swap).

## 2. Recency injection

Before calling the model, `adr-gen` injects:

- the **10 newest ADRs** as `ADR-NNNN [status, date] title`, so the model does
  not duplicate an existing decision and can cite a supersession;
- the **8 most recent commits** (`git log -n8 --format=%h %s`) for single-commit
  mode; omitted during `--all-commits` so a 2019 commit is not given 2026 context;
- the repository's **top-level layout**, so paths in the ADR are plausible.

The prompt explicitly instructs the model to add `- Supersedes ADR-NNNN` under
`## More Information` when the new decision replaces an old one. The human then
sets the old ADR's status to `superseded by ADR-NNNN`; `adr-check` R2.2 requires
the backlink, so the pair cannot drift apart.

## 3. LLM configuration

Any OpenAI-compatible endpoint works (OpenAI, DeepSeek, Azure-compatible
gateways, a local vLLM/Ollama proxy):

| Variable | Required | Default |
| --- | --- | --- |
| `ADR_LLM_API_KEY` (fallback `OPENAI_API_KEY`) | yes, unless `--no-llm` | — |
| `ADR_LLM_BASE_URL` (fallback `OPENAI_BASE_URL`) | no | SDK default |
| `ADR_LLM_MODEL` | no | `gpt-4o-mini` (or `--model`) |

```bash
export ADR_LLM_API_KEY=sk-...
export ADR_LLM_BASE_URL=https://api.deepseek.com
export ADR_LLM_MODEL=deepseek-chat
adr-gen --from-commit HEAD
```

`openai` is imported lazily. When it is missing, `adr-gen` makes one automatic
installation attempt (`python3 -m adrkit deps --install --only openai`
semantics) and retries the import; `ADR_AUTO_INSTALL=0` disables that attempt.
`adr-index` and `adr-check` never need it.

## 4. Prompt contract

The model must answer in this exact shape:

```text
SLUG: <kebab-case-ascii-slug>
---
status: proposed
date: YYYY-MM-DD
decision-makers: []
consulted: []
informed: []
---

# <title>

## Context and Problem Statement
...
## Decision Drivers
...
## Considered Options
...
## Decision Outcome

Chosen option: "<name>", because <specific reason>.

### Consequences
...
## More Information
```

- Prose language is `--language zh|en` (default `zh`); MADR headings stay
  English so tooling and cross-team review stay stable.
- At least two real options are required; "do nothing" counts.
- The model is told to cite real files/modules from the evidence and to put
  uncertainty under `## More Information` — never to invent facts.

**Validation** (`validate_generated`) rejects output that lacks frontmatter, a
title, any required section, or `Chosen option:`. On failure the model is asked
**once** to repair; a second failure aborts with exit 1 and writes nothing.

**Human gate:** whatever the model returned, `_patch_frontmatter` forces
`status: proposed` and ensures a `date`. `adr-gen` never produces an accepted
ADR.

## 5. Filename and numbering

- Number = `max(existing) + 1`, zero-padded to four digits.
- Slug = `--slug`, else the model's `SLUG:` line, else ASCII words from the
  title, else `decision-<commit8>`/`decision-<YYYYMMDD>`.
- Slug is normalized to `^[a-z0-9]+(-[a-z0-9]+)*$` and truncated to 60 chars.
- Existing files are never overwritten; a number collision is a hard error.

## 6. Offline scaffold (`--no-llm`)

Writes a structurally valid MADR file with `TODO` placeholders and the signal
reasons as decision drivers. Use it when there is no API key, when the network
is unavailable, or when a human wants to write the prose. The scaffold is
`status: proposed` and is not intended to pass review unchanged.

## 7. After generation

```bash
# 1. Review the prose and evidence.
$EDITOR docs/adr/0007-migrate-gateway-to-rust.md

# 2. Approve it (human decision).
#    Change status: proposed  ->  status: accepted

# 3. If it replaces an ADR, update the old record:
#    status: superseded by ADR-0007

# 4. Refresh the index and validate.
adr-index --dir docs/adr
adr-check --dir docs/adr
```

The order matters: run `adr-index` **after** the status edits, then commit the
ADR and `index.md` together. CI rejects a stale index.

## 8. Git output encoding (GBK / legacy repositories)

Git stores commit messages as bytes. On a Windows-era repository they are often
GBK without an `encoding` header, so a UTF-8-only decoder raises or mangles
them. `adr-gen` decodes all git output (`show`, `log`, `rev-list`, `diff`) with:

1. UTF-8 (the modern default);
2. GB18030 (a superset of GBK/GB2312) when UTF-8 fails;
3. `ADR_GIT_ENCODING` or `--git-encoding <codec>` when the repo uses Big5 or
   another legacy codec;
4. UTF-8 with replacement characters as a last resort (never a traceback).

```bash
adr-gen --from-commit HEAD --git-encoding gbk
ADR_GIT_ENCODING=big5 adr-gen --all-commits --dry-run
```

If you see `�` in a generated title, pass the repository's real encoding
explicitly. Git may already re-encode commits that declare
`i18n.commitEncoding`/`encoding`, in which case no override is needed.

## 9. Backfill from all commits (`--all-commits`)

`--all-commits` walks the history reachable from `--until` (default `HEAD`),
**oldest first**, and generates one ADR per commit that passes the signal
filter. It is not a single "summarize the repo" ADR.

```bash
adr-gen --all-commits --dry-run                       # cost estimate, no writes
adr-gen --all-commits --limit 20                      # at most 20 ADRs
adr-gen --all-commits --since v1.0.0 --limit 50       # only after a tag
adr-gen --all-commits --include-merges --limit 10
adr-gen --all-commits --no-llm                        # offline scaffolds
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `--since REV` | — | exclude `REV` and its ancestors |
| `--until REV` | `HEAD` | last commit to inspect |
| `--include-merges` | false | include merge commits (usually empty changes) |
| `--limit N` | 50 | max candidate ADRs; `0` = unlimited |
| `--dry-run` | false | print candidates and scores; no files, no LLM |
| `--no-llm` | false | deterministic scaffolds instead of model calls |
| `--force` | false | bypass the per-commit signal filter (use sparingly) |

**Idempotency:** every commit-generated ADR gets
`source-commit: <full-sha>` in frontmatter. A later batch run reads all ADRs and
reports a matching commit as `already recorded`, so reruns do not duplicate
records. Single-commit `adr-gen --from-commit` uses the same mechanism.

**Failure policy:** a commit that fails validation is recorded and the batch
continues; three consecutive failures, a missing API key, or a missing
`openai` aborts the run. Exit `1` when any commit failed, `0` otherwise.

**Recommended sequence for a large repository:**

```bash
adr-gen --all-commits --dry-run                 # inspect candidates
adr-gen --all-commits --limit 10                 # first chunk, review them
adr-gen --all-commits --dry-run                 # see what remains
adr-gen --all-commits --limit 10                 # next chunk
```

`--dry-run` never creates `docs/adr/`; the index is regenerated once after a
non-dry batch that wrote at least one ADR, not once per commit.
