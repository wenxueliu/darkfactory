# 自动修复策略 (Auto-Fix Strategy)

## What Success Looks Like

Every fixable issue is auto-fixed by `lint_runner.py --auto-fix` without human intervention. Every non-fixable issue is delegated to the right agent with complete context. No issue is left unaddressed.

## Decision Flow

```
lint_runner.py --auto-fix --json returns errors
  │
  ├─ error.auto_fixable == true → handled by the script (each checker's auto_fix())
  │   → Re-run lint_runner.py, check if fixed
  │
  ├─ error.auto_fixable == false and severity in [P0, P1, P2]
  │   ├─ Phase A: LLM direct fix (sw-lint-checker agent reads file, applies targeted Edit, re-verifies)
  │   │   → Re-run lint_runner.py --files <fixed_file> --json after each file
  │   │   → If error_count increases → revert that fix
  │   └─ Phase B: Delegate remaining to sw-tdd-agent (for issues LLM could not fix)
  │       → type errors, logic issues, cross-file changes, or complex restructures
  │
  └─ error.severity == P3
      → Document only, don't block
```

## LLM Direct Fix (Phase A) — Rules

The sw-lint-checker agent applies LLM fixes BEFORE delegating to sw-tdd-agent:

1. **One file at a time.** Read → analyze error → Edit → verify → next file.
2. **Targeted fix only.** Fix ONLY the reported lint error. Do not refactor or change behavior.
3. **Verify after each file.** `lint_runner.py --files <fixed_file> --auto-fix --json`
4. **Revert on regression.** If error_count increases after fix → revert and skip that error.
5. **Know your limits.** Complex cross-file changes, type system issues, or security-sensitive code → skip LLM fix, leave for sw-tdd-agent.
6. **Evidence rule.** Every fix must cite before/after lint_runner.py output.

## Auto-Fix: Handled by Python Checker Classes

The `lint_runner.py` script delegates auto-fix to each checker's `auto_fix()` method.
Per-checker auto-fix capabilities are defined in the checker classes under `checkers/`:

| Checker | auto_fix() behaviour | Fixable | Not Fixable |
|---------|---------------------|---------|-------------|
| PythonChecker | `ruff check --fix` + `ruff format` | F401, I001, E711, W291, UP006, SIM108, formatting | F821, E501*, type issues |
| JavaScriptChecker | `eslint --fix` + `prettier --write` | semi, quotes, indent, no-var, prefer-const, eqeqeq, formatting | no-unused-vars, no-undef |
| TypescriptChecker | `eslint --fix` + `prettier --write` (tsc has NO fix) | ts-eslint fixable rules, formatting | TS**** type errors (P1, delegate) |
| GoChecker | `golangci-lint --fix` + `gofmt -w` + `goimports -w` | gofmt, goimports, misspell | errcheck, unused, govet |
| ShellChecker | `shfmt -w` (shellcheck has NO fix) | Formatting only | SC**** violations (delegate) |
| MarkdownChecker | `markdownlint --fix` | MD009, MD012, MD022, MD029, MD031, MD032, MD047 | MD033, MD034, MD036, MD041 |
| CssChecker | `stylelint --fix` + `prettier --write` | Formatting | Invalid values, unknown properties |
| DockerfileChecker | (no auto-fix) | — | All DL**** violations (delegate) |
| YamlChecker | `prettier --write` (yamllint has NO fix) | Formatting | Indentation, truthy, document-start |
| TomlChecker | `taplo format` | Formatting | Parse errors, schema violations |
| JsonChecker | `prettier --write` | Formatting | Invalid JSON syntax (P0) |

\* E501 (line too long) can sometimes be fixed by `ruff format`, sometimes not.

## When to Delegate to sw-tdd-agent (Phase B — after LLM fix)

Only delegate after LLM direct fix (Phase A) has been attempted. Delegate when ALL of these apply:
- `error.auto_fixable == false` (from lint_runner.py JSON output)
- `error.severity` is P0, P1, or P2
- LLM direct fix was attempted and failed, or the fix requires cross-file changes / complex type restructure
- The error is not a tool-missing (`tool_missing == true`)

### Delegation Prompt Template

```
Fix lint issues found by lint_runner.py. These issues CANNOT be auto-fixed.

TASK: Fix {N} lint issues in {language} files.

ISSUES (from lint_runner.py --json output):
{file}:{line} — [{rule}] {message} — {severity}

CONSTRAINTS:
- Fix ONLY the reported issues, do not refactor unrelated code
- Re-run: python lint_runner.py --files {comma-separated file list} --json
  to confirm issues are resolved
- Do not change behavior — only fix style/types/convention issues
- Report which files were changed and which issues were resolved

Context: These files were just completed through the TDD cycle.
All tests pass. The lint issues are the ONLY remaining blockers.
```

## Fix Iteration Limit

Maximum 3 total rounds:

```
Round 1: lint_runner.py --auto-fix --json → tool auto-fixes via checker classes → re-check
Round 2: LLM direct fix for remaining auto_fixable=false P0/P1/P2 → re-check per file → full re-check
Round 3: Delegate to sw-tdd-agent for issues LLM could not fix → re-run lint_runner.py

If after Round 3 P0/P1 issues remain → LINT_BLOCKED, escalate to human
```

## Post-Fix Verification

After ANY fix (auto or delegated), ALWAYS:

1. Re-run `python lint_runner.py --files <fixed_files> --auto-fix --json`
2. Compare the error count before vs after the fix
3. If error count increased → the fix broke something → revert and try different approach
4. Only report LINT_PASS when the script JSON shows `status: PASS`
