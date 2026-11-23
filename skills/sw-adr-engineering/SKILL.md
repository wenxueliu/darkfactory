---
name: sw-adr-engineering
description: "ADR 工程化：MADR 4.0 模板、从提交/文本生成决策记录、索引、R1/R2 结构校验，以及 adr-drift 的 R3/R4 代码漂移门禁。Use when creating, generating, indexing, validating, or enforcing Architecture Decision Records. [trigger: ADR, MADR, 架构决策记录, 决策记录, adr-init, adr-gen, adr-check, adr-drift, decision record, architecture decision]"
metadata:
  version: "1.0.1"
  external_dependencies: []
---

# 黑灯工厂 ADR 工程化 (sw-adr-engineering)

## Overview

把架构决策变成可执行资产，而不只是 Markdown 归档：

1. **MADR 4.0 bare 模板** — 语言无关，`adr-init` 落地；
2. **adrkit** — `adr-gen` / `adr-index` / `adr-check`，一个内部 pip 包；
3. **adr-drift** — 把 ADR 红线翻译成 `arch.yaml` / `## Constraints` 规则，
   在 CI 里检查代码是否还在遵守决策。

**Your Mission:** 让每条决策都有编号、有状态、有索引、有双向 supersede 链接，
并且（当配置了规则时）有机械化门禁。生成层只写 `proposed`，`accepted` 永远由人确认。

## Identity

The decision-record engineer. Treats an ADR as a contract: if it cannot be
indexed, linked, and checked, it will rot. Prefers mechanical enforcement over
documents that ask nicely.

## Principles

- **Human gate on status** — `adr-gen` 永远写 `proposed`；只有人能把状态改为
  `accepted`。AI 不得代替人做价值判断。
- **Idempotent by construction** — `index.md` 整文件重写，重复执行输出不变；
  CI 用 `git diff` 或 `--check` 即可发现漂移。
- **Supersession is bidirectional** — 旧记录写 `superseded by ADR-NNNN`，新记录
  必须写 `supersedes: [ADR-NNNN]` 或正文 `Supersedes ADR-NNNN`；R2.2 强制。
- **Enforce what is checkable** — 结构/引用交给 `adr-check`（零依赖），代码
  漂移交给 `adr-drift`。不要用一段"请遵守"的文字冒充门禁。
- **Fail closed on config** — `adr-drift` 无规则时 exit 2；不要吞掉它。

## Capabilities

| Capability | Command | Load |
| --- | --- | --- |
| 初始化 ADR 目录 + 模板 | `adr-init` | `references/madr-template.md` |
| 从提交/文本/需求生成 ADR | `adr-gen` | `references/generation.md` |
| 重建索引 | `adr-index` | — |
| R1/R2 结构/引用校验 | `adr-check` | `references/adr-rules.md` |
| R3/R4 代码漂移检查 | `adr-drift check` | `references/adr-drift.md` |
| CI 门禁 | GitHub Actions | `references/ci-gate.md` |

## Package Dependencies

`metadata.external_dependencies` is reserved for **other skills**; this skill
has none. Python packages are a separate axis: they are checked immediately
before the feature that needs them and installed on demand
(`ADR_AUTO_INSTALL=0` disables the automatic install).

| Package | Needed for | Behaviour when missing |
| --- | --- | --- |
| `openai>=1.0` | `adr-gen` LLM filling | installed automatically on the first LLM call; `--no-llm` bypasses it |
| `pyyaml>=6.0` | full MADR frontmatter parsing | optional; a stdlib parser is built in |
| `adr-drift==0.1.0` | R3/R4 drift gate | install explicitly before `adr-drift` (step 6) |

```bash
python3 -m adrkit deps                  # report; exit 1 when something is missing
python3 -m adrkit deps --install        # install all missing packages
python3 -m adrkit deps --install --only adr-drift
python3 -m adrkit deps --json
```

If pip is externally managed (PEP 668), the installer fails closed and prints
the manual command; use a virtualenv rather than forcing the install.

## Setup

The toolkit ships inside this skill as a pip-installable package at
`<skill-dir>/scripts`. Pick one:

```bash
# A. Install once (recommended; puts adr-* on PATH; core has no hard deps)
pip install "<skill-dir>/scripts"

# A2. Optional: install openai + pyyaml + adr-drift up front
pip install "<skill-dir>/scripts[all]"

# B. No install (CI-friendly fallback)
PYTHONPATH="<skill-dir>/scripts/src" python3 -m adrkit index --dir docs/adr

# C. Vendor into the target repo so CI can install it
cp -r "<skill-dir>/scripts" tools/adrkit
pip install ./tools/adrkit
```

`adr-index` / `adr-check` need only the standard library. Optional packages are
not a setup prerequisite: `python3 -m adrkit deps` reports them, `adr-gen`
installs `openai` on first use, and step 6 installs `adr-drift`.

## Workflow

### 0. Locate the record set

Default `docs/adr`. Existing repositories may use `doc/adr` (adr-tools) or
`docs/decisions` (MADR). Check before creating:

```bash
for d in docs/adr doc/adr docs/decisions adr; do [ -d "$d" ] && echo "$d"; done
```

If none exists, use `docs/adr` and run `adr-init`.

### 1. Initialize

```bash
adr-init --dir docs/adr
```

Creates `docs/adr/template/adr-template.md` (MADR 4.0 bare). Idempotent; a
customized template is not overwritten without `--force`.

### 2. Generate

```bash
# from a commit (HEAD when the value is omitted)
adr-gen --from-commit HEAD --dir docs/adr

# from a decision statement in the conversation
adr-gen --from-text "网关从 Node 迁移到 Rust" --dir docs/adr --language zh

# from a requirement document
adr-gen --from-file requirements/REQ-1024.md --dir docs/adr

# inspect first, write later
adr-gen --from-commit 4f2c1ab --dry-run
```

The signal filter skips docs/tests/lockfile-only commits. If it skips a real
decision, use `--force`. If no model is available, use `--no-llm` for a
deterministic scaffold. Details: [`references/generation.md`](references/generation.md).

### 3. Human review (mandatory)

Show the generated file to the user. The human edits `status: proposed` to
`status: accepted` when the decision is approved. If it replaces an earlier
record, update the old record to `superseded by ADR-NNNN` and ensure the new
record links back.

**Never change a status to `accepted` on the user's behalf.**

### 4. Refresh the index

```bash
adr-index --dir docs/adr
adr-index --dir docs/adr --check   # exit 1 when stale, writes nothing
```

Expected output:

```markdown
# Architecture Decision Records

* [ADR-0001](0001-use-postgresql-as-primary-db.md) - Use PostgreSQL as primary database
* [ADR-0002](0002-adopt-madr.md) - Adopt MADR for decision records
* [ADR-0003](0003-extract-notification-service.md) - Extract notification service (proposed)
```

Non-`accepted` states are annotated; `accepted` is the unmarked default.

### 5. Validate R1/R2

```bash
adr-check --dir docs/adr
adr-check --dir docs/adr --strict   # warnings fail too
adr-check --dir docs/adr --json     # machine-readable
```

Fix every error before reporting completion. Warnings are advisory unless the
project opts into `--strict`. Rule catalog: [`references/adr-rules.md`](references/adr-rules.md).

### 6. Enforce R3/R4 (when rules exist)

```bash
python3 -m adrkit deps --install --only adr-drift
adr-drift --root . --adr-dir docs/adr check
```

`adrkit deps` checks the importable module, installs `adr-drift==0.1.0` when
missing, and fails with the manual command when pip cannot install.

**Critical:** adr-drift 0.1.0 reads **`arch.yaml`**, not `adr-drift.toml`.
Rules are quoted DSL strings; per-rule `message`/`paths` do not exist. Read
[`references/adr-drift.md`](references/adr-drift.md) before writing config — an
unquoted rule is silently dropped and the gate passes while enforcing nothing.

### 7. CI

Copy the workflow from [`references/ci-gate.md`](references/ci-gate.md): index
sync, R1/R2, R3/R4, plus a nightly `drift --since <last-release-tag>` job.

## Command Reference

| Command | Important flags | Exit codes |
| --- | --- | --- |
| `adr-init` | `--dir`, `--force`, `--quiet` | 0 ok, 1 template conflict, 2 missing bundled template |
| `adr-gen` | `--from-commit [SHA]`, `--from-text`, `--from-file`, `--dry-run`, `--no-llm`, `--force`, `--slug`, `--model`, `--language zh\|en`, `--no-index` | 0 written/skipped, 1 generation/validation error, 2 bad git ref/input |
| `adr-index` | `--dir`, `--check`, `--no-recursive` | 0 ok, 1 stale with `--check`, 2 missing dir |
| `adr-check` | `--dir`, `--strict`, `--json`, `--no-recursive` | 0 clean, 1 violations (or warnings with `--strict`), 2 missing dir |
| `python -m adrkit deps` | `--install`, `--only NAME[,NAME]`, `--json` | 0 all available/installed, 1 still missing, 2 unknown package |

`adr-gen` prints why a commit was skipped and which signals fired; include that
in the report so a skip is auditable.

## Input Contract

| Input | Required | Description |
| --- | --- | --- |
| `operation` | yes | `init`, `generate`, `index`, `check`, `enforce`, or `ci` |
| `adr_dir` | no | default `docs/adr`; locate an existing root first |
| `decision_source` | for generate | commit SHA, free text, or requirement file |
| `language` | no | prose language `zh`/`en`; MADR headings stay English |
| `llm` | no | `ADR_LLM_API_KEY`, optional `ADR_LLM_BASE_URL`/`ADR_LLM_MODEL` |
| `drift_config` | for enforce | `arch.yaml` + optional ADR `## Constraints` |

## Output Contract

- New ADR file `NNNN-kebab-slug.md`, `status: proposed`, MADR sections filled.
- `docs/adr/index.md` regenerated deterministically.
- `adr-check` output with rule IDs and exit code.
- If R3/R4 ran: `adr-drift` output/exit code, and the config path used.
- Every completion claim cites a fresh command run (no "should pass").

## Acceptance Criteria

- [ ] `adr-index --dir docs/adr` is idempotent: a second run produces no diff.
- [ ] `adr-check --dir docs/adr` exits 0, or every error is reported with its
      rule ID and a concrete fix.
- [ ] Generated records are `proposed`; no AI-set `accepted` status.
- [ ] Supersession links are bidirectional (`R2.2` clean).
- [ ] If `arch.yaml`/`## Constraints` exist, `adr-drift check` was executed and
      its real exit code reported; missing rules are treated as a config error,
      not a pass.
- [ ] CI snippet uses the real adr-drift 0.1.0 contract (`arch.yaml`, quoted
      rules, `--root` before the subcommand).
- [ ] `python3 -m adrkit deps` was run; every package needed by the executed
      feature was installed, or the failure includes a runnable pip/venv command.

## External Skill Dependencies

无。`metadata.external_dependencies: []`，本技能不调用其他 Skill；所有参考文件
都在本目录内。

Python 包依赖不属于 `external_dependencies`，运行时由
`python3 -m adrkit deps` 检查并按需安装，见
[Package Dependencies](#package-dependencies)：

- 无 `openai`：首次 LLM 调用时自动安装；`--no-llm` 可绕过。
- 无 `PyYAML`：回退到内置解析器，不阻塞。
- 无 `adr-drift`：R1/R2 仍可执行；R3/R4 必须显式安装，不能声称已强制。
