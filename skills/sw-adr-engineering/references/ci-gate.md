# CI gate — GitHub Actions, pure Python

The gate has three independent jobs of work, in increasing cost:

1. **index in sync** — `adr-index` rewrites `index.md`; a dirty tree means the
   author forgot to commit it (or hand-edited it).
2. **R1/R2** — `adr-check` validates structure, numbering, status vocabulary,
   and bidirectional supersession links. Pure Markdown, milliseconds.
3. **R3/R4** — `adr-drift check` validates the code against `arch.yaml` and
   every ADR's `## Constraints`. Python `ast` for Python, regex fallback for
   other languages.

No Node, no site build, one `setup-python` step. Pin `adr-drift==0.1.0`: the
config format is version-specific (see [`adr-drift.md`](adr-drift.md)).

## `adr-gate.yml`

```yaml
name: adr-gate

on:
  pull_request:
    branches: [main]

permissions:
  contents: read

jobs:
  adr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # adr-drift baseline/drift and history need it

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install tooling
        # Vendor adrkit at tools/adrkit, or install from the internal index:
        #   pip install "adrkit==0.2.0" "adr-drift==0.1.0"
        # CI installs explicitly; the runtime `adrkit deps` auto-install is for
        # local runs and must not be the only thing keeping the gate honest.
        run: pip install ./tools/adrkit "pyyaml>=6.0" "adr-drift==0.1.0"

      - name: Index is in sync
        run: adr-index --dir docs/adr --check

      - name: R1/R2 structure and supersession links
        run: adr-check --dir docs/adr

      - name: R3/R4 code drift
        run: adr-drift --root . --adr-dir docs/adr check
```

`adr-index --dir docs/adr --check` is preferred over rewriting the index and
running `git diff`: `git diff` only sees tracked files, so an `index.md` created
for the first time stays untracked and the gate would pass. If the project
requires the diff form, run `git add -N docs/adr/index.md` (or
`git status --porcelain -- docs/adr/`) before `git diff`.

If the repository legitimately carries legacy violations, commit the baseline
once and change the last step to:

```yaml
      - name: R3/R4 code drift
        run: adr-drift --root . --adr-dir docs/adr check --baseline .adr-baseline.json
```

Do **not** use `--fail-on none` in the gate; it turns the check into a report
and lets drift merge.

## Nightly drift report

`check` already runs on every PR, but a nightly job catches drift introduced by
merges that bypassed review (or by long-lived branches). Note that
`drift --since origin/main` is empty on `main`; use the last release tag.

```yaml
name: adr-drift-nightly

on:
  schedule:
    - cron: "0 3 * * *"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - run: pip install ./tools/adrkit "pyyaml>=6.0" "adr-drift==0.1.0"

      - name: New drift since the last release
        run: |
          BASE="$(git describe --tags --abbrev=0 2>/dev/null || git rev-list --max-parents=0 HEAD)"
          echo "checking drift since $BASE"
          adr-drift --root . --adr-dir docs/adr drift --since "$BASE"
```

## Operational notes

- **Fail closed on configuration.** `adr-drift check` exits `2` when it finds no
  rules. That is intentional: a missing `arch.yaml` or a section typo must not
  look like a pass. Fix the config instead of swallowing the exit code.
- **Quotes in `arch.yaml` are load-bearing.** Unquoted `rules:` entries are
  valid YAML mappings and are silently dropped. After editing rules, introduce
  one known violation locally and confirm `check` fails.
- **Python version.** `adrkit` requires Python ≥3.10; `adr-drift` ≥3.10. The
  workflow pins 3.12, matching the rest of the toolchain.
- **Fork PRs.** `pull_request` gives a read-only token and no secrets, which is
  what this gate needs. Do not switch to `pull_request_target` with a checkout
  of PR code.
- **Cache.** Not required; both packages are small. Add `actions/cache` only if
  the internal index is slow.
- **Local pre-commit equivalent.** Run the same three commands before pushing:

```bash
adr-index --dir docs/adr && \
adr-check --dir docs/adr && \
adr-drift --root . --adr-dir docs/adr check
```

## Copy checklist

- [ ] `tools/adrkit/` vendored (or `adrkit` published to the internal index)
- [ ] `arch.yaml` exists at the repo root, with at least one true rule
- [ ] `docs/adr/index.md` committed
- [ ] `adr-drift` pinned to `0.1.0`
- [ ] legacy violations grandfathered with `.adr-baseline.json` if needed
- [ ] nightly job's base ref matches the release process (tag vs. branch)
