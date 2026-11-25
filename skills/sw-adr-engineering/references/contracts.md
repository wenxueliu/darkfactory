# adrkit input/output contract

This file is the authoritative I/O specification for the skill. `SKILL.md`
summarizes it; when the two disagree, this file wins and the code is the final
arbiter.

## 1. Skill activation inputs

| Field | Type | Required | Default | Validation |
| --- | --- | --- | --- | --- |
| `operation` | enum | yes | — | `init` \| `generate` \| `index` \| `check` \| `enforce` \| `ci` |
| `repo_root` | path | no | `.` (cwd) | must contain the ADR directory and, for `--from-commit`, a git work tree |
| `adr_dir` | path | no | `docs/adr` | must exist for `index`/`check`; created by `init`/`generate` |
| `source` | object | for `generate` | — | exactly one of `{kind: commit, ref}` \| `{kind: text, text}` \| `{kind: file, path}` \| `{kind: history, since?, until?, limit?}` |
| `language` | enum | no | `zh` | `zh` \| `en`; MADR headings stay English |
| `drift_config` | path | for `enforce` | `arch.yaml` | at repo root; cannot be renamed in adr-drift 0.1.0 |

**Runtime configuration — not activation inputs.** These are read from the
environment only when `adr-gen` calls an LLM. They are never stored in ADR
content and are not needed for `--no-llm`, `index`, `check`, or `deps`.

| Config | Default | Required when |
| --- | --- | --- |
| `ADR_LLM_API_KEY` / `OPENAI_API_KEY` | — | calling a hosted model; a dummy value works for an unauthenticated local proxy |
| `ADR_LLM_BASE_URL` / `OPENAI_BASE_URL` | SDK default | DeepSeek / gateway / local vLLM or Ollama |
| `ADR_LLM_MODEL` / `--model` | `gpt-4o-mini` | never; only to override the model |

Preconditions:

- `generate` with a commit/history source requires a resolvable git ref.
- `generate` in LLM mode needs a reachable OpenAI-compatible endpoint; with no
  key/base URL it fails closed with a manual-install/credential message.
  `--no-llm` bypasses the LLM entirely.
- `enforce` requires `adr-drift==0.1.0` and at least one rule in `arch.yaml` or
  an ADR `## Constraints`; no rules is a config error (exit 2), not a pass.
- `ci` requires a committed `index.md` and `arch.yaml` (or a documented
  baseline) in the repository.

## 2. Per-command contracts

### 2.1 `adr-init`

**Inputs**

| Flag | Type | Default | Meaning |
| --- | --- | --- | --- |
| `--dir` | path | `docs/adr` | ADR directory to create |
| `--force` | bool | false | replace a differing template |
| `--quiet` | bool | false | suppress stdout |

**Outputs**

- Creates `<dir>/template/adr-template.md` (MADR 4.0 bare).
- Creates only the parent directories needed for that file.
- Does **not** create `index.md` or any ADR record.
- stdout: `adr-init: wrote <path>` and a `next -> adr-gen ...` hint; or
  `adr-init: <path> is already up to date`.
- Exit codes: `0` ok/no-op, `1` template exists and differs (without `--force`),
  `2` bundled template or directory cannot be written.
- Never overwrites a customized template without `--force`.

### 2.2 `adr-gen`

**Inputs** (one source is mandatory; they are mutually exclusive)

| Flag | Type | Default | Meaning |
| --- | --- | --- | --- |
| `--from-commit [SHA]` | string | `HEAD` when the value is omitted | commit to turn into an ADR |
| `--from-text TEXT` | string | — | decision statement |
| `--from-file PATH` | path | — | requirement/decision document |
| `--dir` | path | `docs/adr` | target ADR directory |
| `--repo` | path | `.` | repo root for git metadata |
| `--slug` | string | derived | filename slug override |
| `--model` | string | `ADR_LLM_MODEL` or `gpt-4o-mini` | LLM model |
| `--language` | enum | `zh` | `zh` \| `en` |
| `--dry-run` | bool | false | print only; no filesystem writes |
| `--no-llm` | bool | false | deterministic scaffold, no network |
| `--force` | bool | false | bypass the signal filter |
| `--no-index` | bool | false | do not refresh `index.md` |
| `--all-commits` | bool | false | scan reachable history, one ADR per significant commit |
| `--since REV` | string | — | with `--all-commits`: exclude REV and ancestors |
| `--until REV` | string | `HEAD` | with `--all-commits`: last commit to inspect |
| `--include-merges` | bool | false | with `--all-commits`: include merges |
| `--limit N` | int | 50 | with `--all-commits`: max candidates, `0` = unlimited |
| `--git-encoding ENC` | string | UTF-8 → GB18030 | force legacy commit-message decoding |

Environment: `ADR_LLM_API_KEY` (or `OPENAI_API_KEY`), `ADR_LLM_BASE_URL` (or
`OPENAI_BASE_URL`), `ADR_LLM_MODEL`, `ADR_LLM_TIMEOUT` (seconds, default 60),
`ADR_AUTO_INSTALL=0` to disable package auto-install.

**Outputs**

- On success: `<dir>/NNNN-<slug>.md` with `status: proposed` and filled MADR
  sections; `index.md` is refreshed unless `--no-index` (conditional on
  `index.md` changing).
- Exit `0` when written **or** intentionally skipped by the signal filter.
- Exit `1` on generation/validation/install failure; nothing is written.
- Exit `2` on an invalid source: bad git ref, unreadable file, or mutually
  exclusive flags.

stdout variants:

```text
# written
adr-gen: wrote docs/adr/0007-migrate-gateway-to-rust.md (status: proposed)
  - database migration or schema changed (+5)
adr-gen: review the ADR and change status to 'accepted' when approved

# skipped (still exit 0)
adr-gen: skipped: change is not architecturally significant (score 0 < 3)
  - only docs/tests/assets/lockfiles changed
  use --force to generate anyway

# --dry-run (no writes)
<full markdown document>
---
adr-gen: would write docs/adr/0007-migrate-gateway-to-rust.md (dry run)
```

Guarantees:

- Existing files are never overwritten; the next number is `max(number) + 1`.
- A model-produced `status: accepted` is rewritten to `proposed`.
- `--dry-run` creates no directories and no files.
- `--no-llm` performs no network access.
- Validation failure is retried once with a repair prompt, then aborted.

#### 2.2.1 History backfill (`--all-commits`)

**Inputs:** `--since`, `--until` (default `HEAD`), `--include-merges`,
`--limit` (default 50, `0` = unlimited), `--dry-run`, `--no-llm`, `--force`,
`--no-index`, `--git-encoding`. Mutually exclusive with `--from-*`; `--slug` is
rejected in this mode.

**Outputs:**

- One `<dir>/NNNN-<slug>.md` per significant commit, `status: proposed`, with
  `source-commit: <full-sha>` in frontmatter.
- `index.md` regenerated **once** after a non-dry run (unless `--no-index`).
- stdout summary:

```text
adr-gen: scanned 42 commit(s): 2 already recorded, 35 noise, 5 generated
adr-gen: wrote docs/adr/0007-migrate-gateway-to-rust.md (status: proposed)
...
adr-gen: limit 50 reached; re-run to continue (recorded commits are skipped) or pass a larger --limit
```

- `--dry-run` stdout lists candidates with scores; it creates no directory and
  makes no LLM call.
- Exit codes: `0` completed, `1` at least one commit failed, `2` invalid range,
  encoding, or `--slug` misuse.
- Idempotency: commits already named by `source-commit` in any ADR are reported
  as `already recorded` and skipped. Three consecutive failures, a missing API
  key, or missing `openai` aborts the run.

### 2.3 `adr-index`

**Inputs**

| Flag | Type | Default | Meaning |
| --- | --- | --- | --- |
| `--dir` | path | `docs/adr` | directory to scan |
| `--check` | bool | false | report stale index; write nothing |
| `--no-recursive` | bool | false | only top-level `*.md` |

**Outputs**

- Writes `<dir>/index.md` atomically, only when content differs.
- Exact format:

```markdown
# Architecture Decision Records

* [ADR-0001](0001-use-postgresql-as-primary-db.md) - Use PostgreSQL as primary database
* [ADR-0002](0002-adopt-madr.md) - Adopt MADR for decision records
* [ADR-0003](0003-extract-notification-service.md) - Extract notification service (proposed)
```

- `accepted` has no annotation; `proposed`/`rejected`/`deprecated`/
  `superseded by ADR-NNNN` are annotated in parentheses.
- Ordering is numeric ascending; links are POSIX relative paths.
- `index.md`, `README.md`, `template/`, hidden directories, and non-matching
  filenames are excluded; invalid filenames produce stderr warnings.
- Exit codes: `0` written/up to date, `1` stale with `--check`, `2` missing
  directory or write failure.
- Idempotent: a second run produces byte-identical output and no write.

### 2.4 `adr-check`

**Inputs**

| Flag | Type | Default | Meaning |
| --- | --- | --- | --- |
| `--dir` | path | `docs/adr` | directory to validate |
| `--strict` | bool | false | warnings become failures |
| `--json` | bool | false | JSON on stdout |
| `--no-recursive` | bool | false | only top-level `*.md` |

**Human output**

```text
docs/adr/0002-old.md: ERROR   R2.2 ADR-0003 does not link back; add ...
docs/adr:             WARNING R1.3 numbering gap(s): ADR-0002

adr-check: 1 error(s), 1 warning(s) in docs/adr
```

**JSON output** (`--json`)

```json
{
  "ok": false,
  "errors": 1,
  "warnings": 1,
  "adr_dir": "docs/adr",
  "issues": [
    {
      "rule": "R2.2",
      "level": "error",
      "path": "docs/adr/0002-old.md",
      "message": "ADR-0003 does not link back; ..."
    }
  ]
}
```

- `ok` is `true` only when `errors == 0` and (`--strict` is off or
  `warnings == 0`).
- `issues[]` is sorted by `(path, rule, message)`.
- Exit codes: `0` clean, `1` errors (or warnings with `--strict`), `2` missing
  directory.
- Read-only: never modifies ADR files.

### 2.5 `python -m adrkit deps`

**Inputs**

| Flag | Type | Default | Meaning |
| --- | --- | --- | --- |
| `--install` | bool | false | install missing packages |
| `--only NAME[,NAME]` | list | all | subset of `openai`, `pyyaml`, `adr-drift` |
| `--json` | bool | false | JSON on stdout |

**JSON output**

```json
{
  "installed": [],
  "missing": ["openai"],
  "packages": {
    "openai": {
      "state": "missing",
      "spec": "openai>=1.0",
      "module": "openai",
      "feature": "gen",
      "purpose": "call an OpenAI-compatible model from adr-gen"
    }
  }
}
```

- `state` is `available` or `missing` after any install attempt.
- Exit codes: `0` all requested packages available/installed, `1` still missing,
  `2` unknown package name.
- Installation uses the current interpreter's `pip`; a PEP 668 failure is
  reported with the manual command and leaves `missing` populated.

### 2.6 `adr-drift check` (delegated, external)

**Inputs**: `<repo-root>/arch.yaml` and/or ADR `## Constraints` sections; source
files under `--root`.

```bash
adr-drift --root . --adr-dir docs/adr check --format json
```

**Output**: human report by default; JSON is a list of
`{rule, rule_source, file, line, detail}` where `rule_source` is
`arch.yaml:<line>` for arch rules and an absolute path for ADR rules.

Exit codes: `0` clean, `1` violations **or an uncaught crash**, `2` missing
rules / parse error / usage error. Because `1` is ambiguous, parse JSON when the
result is consumed by another program.

## 3. File formats

### ADR filename

```text
^[0-9]{4}-[a-z0-9]+(-[a-z0-9]+)*\.md$
```

Four digits, lowercase ASCII slug, one decision per file.

### ADR frontmatter

```yaml
---
status: proposed | accepted | rejected | deprecated | superseded by ADR-NNNN
date: YYYY-MM-DD
decision-makers: [name]
consulted: [name]
informed: [name]
supersedes: [ADR-NNNN]        # optional; required for the R2.2 backlink
source-commit: <full-sha>     # written by adr-gen; makes batch runs idempotent
---
```

Legacy `## Status` sections are accepted as a fallback.

### `arch.yaml`

```yaml
layers:
  - name: api
    paths: ["src/api/**"]
rules:
  - "forbid-import: api -> db"
  - "forbid-pattern: src/**.py !~ \\bpdb\\b"
```

`rules:` entries must be quoted strings; unquoted entries are silently dropped
by adr-drift 0.1.0.

## 4. Invariants and side effects

| Invariant | Enforcement |
| --- | --- |
| `index.md` is deterministic | full rewrite + sorted numeric order |
| `index.md` write is atomic | temp file + `os.replace` |
| ADR files are never overwritten | next number + existence check |
| Generated status is always `proposed` | `_patch_frontmatter` |
| No writes in `--dry-run` / `--check` / `check` | code paths return before write |
| No network except LLM and pip | `adr-gen` LLM call / `deps --install` |
| Exit codes are stable | table per command above |

| Command | Reads | Writes | Network |
| --- | --- | --- | --- |
| `adr-init` | bundled template | `template/adr-template.md` | no |
| `adr-gen` | git/input, ADRs | new ADR, `index.md` | only LLM mode |
| `adr-gen --all-commits` | git history, ADRs | new ADRs, `index.md` once | only LLM mode |
| `adr-index` | ADR files | `index.md` | no |
| `adr-check` | ADR files | nothing | no |
| `adrkit deps` | imports | site-packages (with `--install`) | only with `--install` |
| `adr-drift check` | `arch.yaml`, ADRs, source | nothing | no |

## 5. Agent handoff (skill-level output)

The executing agent must end with a structured handoff, not just prose. The
status vocabulary follows the harness worktree contract.

```json
{
  "operation": "generate",
  "status": "DONE",
  "adr_dir": "docs/adr",
  "artifacts": [
    "docs/adr/0007-migrate-gateway-to-rust.md",
    "docs/adr/index.md"
  ],
  "commands": [
    {"cmd": "adr-gen --from-commit HEAD --dir docs/adr", "exit": 0, "summary": "wrote 0007 (proposed)"},
    {"cmd": "adr-index --dir docs/adr --check", "exit": 0, "summary": "up to date"},
    {"cmd": "adr-check --dir docs/adr", "exit": 0, "summary": "0 errors, 0 warnings"}
  ],
  "package_deps": {"installed": [], "missing": []},
  "drift": {"ran": true, "exit": 0, "config": "arch.yaml"},
  "open_questions": []
}
```

| Status | When |
| --- | --- |
| `DONE` | requested operation completed; `adr-check` exits 0; drift (if in scope) exits 0 |
| `DONE_WITH_CONCERNS` | completed but skipped by the signal filter, warnings remain, or drift was explicitly not configured |
| `NEEDS_CONTEXT` | missing `adr_dir`, decision source, or LLM key with no `--no-llm` fallback |
| `BLOCKED` | validation errors remain, `adr-drift` exit 2 (no rules/parse error), or pip cannot satisfy a required package |

Rules:

- `commands[]` contains only commands actually executed, with their real exit
  codes. Do not report a command that was not run.
- `artifacts[]` contains only files written during this run.
- `drift.ran=false` is required when no `arch.yaml`/`## Constraints` exists;
  never omit the field silently. `drift.config` names the file actually used.
- `open_questions[]` carries human decisions that block `accepted` status.
- The handoff must not claim "enforced" when `drift.ran` is false.
- When `--all-commits` ran, include
  `batch: {scanned, already, noise, generated, failed, limit_hit, aborted}`;
  `generated` is a count, not the `artifacts` list.
