# R3/R4 — enforcing decisions with adr-drift

R1/R2 (structure and supersession links) live in `adr-check`. R3/R4 answer a
different question: **does the code still obey the accepted decisions?** This
skill delegates that to [`adr-drift`](https://pypi.org/project/adr-drift/), a
language-agnostic rule engine that parses Python with `ast` and other languages
with a documented regex fallback.

## Verified baseline (important)

The original design note in this repo specified `adr-drift.toml` with
`[[rule]]` objects and `id`/`kind`/`import`/`paths`/`message` fields. **That
format does not exist in adr-drift 0.1.0**, the version published on PyPI
(2026-10-19). Verified against the installed wheel:

- the config file is hard-coded to **`arch.yaml` at the repo root**; a
  `adr-drift.toml` file is silently ignored (`check` reports "no rules found");
- `rules:` is a list of **quoted DSL strings**, not objects;
- there is **no per-rule `message`**, no `paths` key on rules (the glob in
  `forbid-pattern` is the path scope), and no `adr-drift.toml` support;
- unquoted rule lines or object-shaped rules are silently dropped — the worst
  failure mode, because CI then passes while enforcing nothing.

The rest of this document uses the real 0.1.0 contract. Pin the version in CI
(`adr-drift==0.1.0`) so a future format change cannot silently weaken the gate.

## `arch.yaml`

```yaml
# <repo-root>/arch.yaml — only this filename; there is no --config flag.
layers:
  - name: api
    paths: ["src/api/**"]
  - name: db
    paths: ["src/db/**"]
  - name: app
    paths: ["src/**"]

rules:
  # Quotes are REQUIRED. Without them YAML parses a mapping and adr-drift
  # silently drops the rule.
  - "forbid-import: api -> db"                     # api may not import db
  - "forbid-import: src.* -> pymysql"               # no MySQL driver under src/
  - "forbid-pattern: src/**.py !~ \\bpymysql\\b"    # same ban, text-level
  - "require-pattern: src/api/**.py =~ authenticate\\("  # every handler authenticates
```

| Key | Shape | Notes |
| --- | --- | --- |
| `layers` | list of `{name, paths[]}` | matched top-down, first match wins; paths are globs |
| `rules` | list of **strings** | each string is one DSL rule; `#` starts a comment |

### The DSL

| Rule | Meaning |
| --- | --- |
| `forbid-import: <from> -> <to>` | files in `<from>` may not import module `<to>` |
| `forbid-pattern: <glob> !~ <regex>` | files matching `<glob>` must not contain `<regex>` |
| `require-pattern: <glob> =~ <regex>` | files matching `<glob>` must contain `<regex>` |

- `<from>`/`<to>` match a layer name or a dotted module prefix (`db.drivers`
  matches `db.drivers.pg`); `*` wildcards use `fnmatch`.
- Python imports are parsed with `ast`, so comments and strings do not produce
  false positives. JS/TS/Go/Rust/Java/Ruby/PHP use a heuristic regex extractor
  (`--strict-py-only` disables that half).
- Only source files are scanned: `.py .js .jsx .ts .tsx .mjs .cjs .go .rs
  .java .rb .php`. **Manifests such as `pom.xml`, `package.json`, or
  `pyproject.toml` are not scanned** — a "no log4j-core in pom.xml" rule cannot
  be expressed here; use a dependency scanner for that.

## Prefer constraints inside the ADR

A rule is easier to keep alive when it sits next to the decision it enforces.
Any `docs/adr/*.md` may carry an H2 `## Constraints` section (exactly H2, not
H3); each bullet is parsed with the same DSL:

```markdown
## Constraints

- forbid-import: api -> db
- forbid-pattern: src/api/**.py !~ \bpdb\b
```

Two caveats:

1. Layer **names** only resolve when `arch.yaml` defines `layers:`. Without it,
   use dotted prefixes (`forbid-import: src.api -> src.db`).
2. `adr-drift new` and `adr-drift init` seed **live** example constraints, so a
   freshly created ADR can fail `check` immediately. Delete or comment them.

## Commands

```bash
python3 -m adrkit deps --install --only adr-drift   # check + install the pinned version
# manual equivalent: pip install adr-drift==0.1.0

adr-drift --root . --adr-dir docs/adr check          # working tree, exit 1 on violations
adr-drift --root . check --format json               # stable machine output
adr-drift --root . check --baseline .adr-baseline.json
adr-drift --root . baseline                          # grandfather current violations
adr-drift --root . drift --since <git-ref>           # only NEW violations since ref
adr-drift --root . check --fail-on none              # report-only, always exit 0
```

`--root` and `--adr-dir` are **global** options and must precede the
subcommand. There is no parent-directory search: run from the repo root or pass
`--root`. If the console script is not on `PATH` (for example a user install),
`python3 -m adr_drift ...` is the same CLI.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | clean, no new drift, or `--fail-on none` |
| 1 | violations; **also uncaught tracebacks** (e.g. `drift` outside git) |
| 2 | no rules found, DSL/YAML parse error, usage error |

Because 1 is ambiguous, use `--format json` when another tool must interpret
the result.

### `drift --since` caveats

- It compares **committed** `since..HEAD`; uncommitted working-tree changes are
  invisible. `check` is the working-tree gate.
- It only evaluates files changed in that range; pre-existing violations in
  untouched files are ignored (that is the point).
- Identity is `(file, line, rule)`, so a line shift can appear as one new plus
  one fixed violation.
- The default `--since HEAD~5` raises an uncaught `RuntimeError` on a young
  repository (exit 1). Always pass an explicit ref and fetch enough history.
- `--format json` emits only new violations; "fixed" entries are human output.
- It does not honor `.gitignore`; vendored source can produce false positives.

## Mapping the original TOML design

| Original (unsupported) | Real 0.1.0 equivalent |
| --- | --- |
| `kind = "forbid-import"`, `import = "pymysql"` | `- "forbid-import: src.* -> pymysql"` (or a layer/prefix on the left) |
| `kind = "forbid-pattern"`, `pattern`, `paths` | `- "forbid-pattern: <glob> !~ <regex>"` — the glob is the path scope |
| `kind = "forbid-import"`, `paths = ["app/api/**"]` | define `layers: [{name: api, paths: ["app/api/**"]}]` then `- "forbid-import: api -> db"` |
| `message = "..."` | not supported; put the rationale in the ADR's `## Constraints` header or `## More Information` |
| `id = "ADR-0003-..."` | not supported; the ADR file/line is the rule source in output |

If you need the TOML authoring format, write a small generator that renders
`arch.yaml` from it and treat the TOML as the source of truth — but verify the
rendered rules are non-empty, because adr-drift fails open on silently dropped
entries. This skill does not ship such a converter.

## Adoption order

0. Do **not** run `adr-drift init` or `adr-drift new` after `adr-init`: they
   allocate their own `0001-*` record, write a competing `docs/adr/README.md`
   index, and seed live example rules that can fail `check` immediately. Write
   `arch.yaml` by hand and leave ADR creation to `adr-gen`/`adr-init`.
1. `adr-init` + `adr-index` + `adr-check` (pure Markdown, safe on day one).
2. Hand-write `arch.yaml` with **one** rule that is currently true.
3. Run `adr-drift check`; if the legacy code already violates it, record
   `adr-drift baseline` and commit `.adr-baseline.json`.
4. Add `adr-drift check` to CI, then tighten one rule at a time.
5. Add `drift --since <last-release-tag>` nightly to catch drift introduced by
   merges that `check` would have caught too late.
