"""TypeScript checker — eslint (typescript-eslint) + tsc --noEmit + prettier."""

from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


class TypescriptChecker(LintChecker):
    language = "typescript"
    tool_name = "eslint"

    @classmethod
    def handles(cls, file_path: str) -> bool:
        return file_path.endswith((".ts", ".tsx", ".mts", ".cts"))

    def is_available(self) -> bool:
        return tool_is_available("npx")

    def install_hint(self) -> str:
        return "npm install -D eslint typescript-eslint"

    # tsc severity → Harness
    @staticmethod
    def _tsc_severity(_code: str) -> Severity:
        # All type errors are P1 — they indicate likely runtime issues
        return Severity.P1

    def check(self, files: list[str]) -> CheckResult:
        if not files:
            return CheckResult(language=self.language, tool_name=self.tool_name, exit_code=0)
        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name, exit_code=-1,
                tool_missing=True, install_hint=self.install_hint(),
            )

        errors: list[LintError] = []

        # eslint with ts extensions
        eslint_rc, eslint_out, eslint_err = self.run(
            ["npx", "eslint", "--ext", ".ts,.tsx,.mts,.cts"] + files
        )
        current_file = ""
        for line in eslint_out.splitlines() + eslint_err.splitlines():
            stripped = line.strip()
            if stripped.endswith((".ts", ".tsx", ".mts", ".cts")) and ":" not in stripped:
                current_file = stripped
                continue
            # Reuse the same parser as JavaScriptChecker
            import re
            m = re.match(
                r"^\s+(\d+):(\d+)\s+(error|warning)\s+(.+?)\s{2,}([\w\-/@]+)\s*$",
                line.strip(),
            )
            if m:
                sev = Severity.P0 if m.group(3) == "error" else Severity.P2
                errors.append(LintError(
                    file=current_file or "",
                    line=int(m.group(1)),
                    column=int(m.group(2)),
                    rule=m.group(5),
                    message=m.group(4),
                    severity=sev,
                    auto_fixable=m.group(5) in {
                        "@typescript-eslint/consistent-type-imports",
                        "@typescript-eslint/array-type",
                        "@typescript-eslint/no-empty-interface",
                        "@typescript-eslint/no-unnecessary-type-assertion",
                        "@typescript-eslint/prefer-optional-chain",
                    },
                    raw_line=line.strip(),
                ))

        # prettier
        fmt_rc, fmt_out, fmt_err = self.run(["npx", "prettier", "--check"] + files)
        for line in fmt_out.splitlines() + fmt_err.splitlines():
            stripped = line.strip()
            if stripped.startswith("[warn] "):
                stripped = stripped[7:]
            elif stripped.startswith("[error] "):
                stripped = stripped[8:]
            if stripped and stripped.endswith((".ts", ".tsx", ".mts", ".cts")):
                errors.append(LintError(
                    file=stripped, line=None, column=None, rule="prettier",
                    message="File would be formatted", severity=Severity.P2,
                    auto_fixable=True, raw_line=stripped,
                ))

        # tsc --noEmit (type check only — CANNOT auto-fix)
        if tool_is_available("npx"):
            tsc_rc, tsc_out, tsc_err = self.run(["npx", "tsc", "--noEmit"])
            for line in tsc_out.splitlines() + tsc_err.splitlines():
                # TypeScript error format: file(line,col): error TS1234: message
                import re as _re
                m = _re.match(
                    r"^(.+?)\((\d+),(\d+)\):\s+error\s+TS(\d+):\s+(.+)$",
                    line.strip(),
                )
                if m:
                    errors.append(LintError(
                        file=m.group(1),
                        line=int(m.group(2)),
                        column=int(m.group(3)),
                        rule=f"TS{m.group(4)}",
                        message=m.group(5),
                        severity=Severity.P1,
                        auto_fixable=False,  # type errors can't be auto-fixed
                        raw_line=line.strip(),
                    ))

        combined_rc = eslint_rc or fmt_rc
        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=combined_rc, errors=errors,
            raw_output="\n".join(filter(None, [eslint_out, eslint_err, fmt_out, fmt_err])),
        )

    def auto_fix(self, files: list[str]) -> FixResult:
        if not self.is_available():
            return FixResult(language=self.language, tool_name=self.tool_name, exit_code=-1, fixed_count=0)
        self.run(["npx", "eslint", "--fix", "--ext", ".ts,.tsx,.mts,.cts"] + files)
        self.run(["npx", "prettier", "--write"] + files)
        # tsc has no auto-fix — remaining type errors stay
        result = self.check(files)
        return FixResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=result.exit_code,
            fixed_count=max(0, len(files)),
            remaining_errors=result.errors,
            raw_output=result.raw_output,
        )
