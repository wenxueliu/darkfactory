"""CSS checker — stylelint + prettier."""

from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


class CssChecker(LintChecker):
    language = "css"
    tool_name = "stylelint"

    @classmethod
    def handles(cls, file_path: str) -> bool:
        return file_path.endswith((".css", ".scss", ".less", ".sass"))

    def is_available(self) -> bool:
        return tool_is_available("npx")

    def install_hint(self) -> str:
        return "npm install -D stylelint"

    # -- customisation points -------------------------------------------
    def _check_cmd(self, files: list[str]) -> list[str]:
        return ["npx", "stylelint"] + files

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        return [
            ["npx", "stylelint", "--fix"] + files,
            ["npx", "prettier", "--write"] + files,
        ]

    def check(self, files: list[str]) -> CheckResult:
        if not files:
            return CheckResult(language=self.language, tool_name=self.tool_name, exit_code=0)
        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name, exit_code=-1,
                tool_missing=True, install_hint=self.install_hint(),
            )

        errors: list[LintError] = []

        # stylelint
        rc, out, err = self.run(self._check_cmd(files))
        for line in out.splitlines() + err.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            errors.append(LintError(
                file="", line=None, column=None, rule="stylelint",
                message=stripped, severity=Severity.P2,
                auto_fixable=False, raw_line=stripped,
            ))

        # prettier
        fmt_rc, fmt_out, fmt_err = self.run(["npx", "prettier", "--check"] + files)
        for line in fmt_out.splitlines() + fmt_err.splitlines():
            stripped = line.strip()
            if stripped.startswith("[warn] "):
                stripped = stripped[7:]
            elif stripped.startswith("[error] "):
                stripped = stripped[8:]
            if stripped and any(stripped.endswith(ext) for ext in (".css", ".scss", ".less", ".sass")):
                errors.append(LintError(
                    file=stripped, line=None, column=None, rule="prettier",
                    message="File would be formatted", severity=Severity.P2,
                    auto_fixable=True, raw_line=stripped,
                ))

        combined_rc = rc or fmt_rc
        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=combined_rc, errors=errors,
            raw_output="\n".join(filter(None, [out, err, fmt_out, fmt_err])),
        )

    def auto_fix(self, files: list[str]) -> FixResult:
        if not self.is_available():
            return FixResult(language=self.language, tool_name=self.tool_name, exit_code=-1, fixed_count=0)
        for cmd in self._fix_cmds(files):
            self.run(cmd)
        result = self.check(files)
        return FixResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=result.exit_code,
            fixed_count=max(0, len(files)),
            remaining_errors=result.errors,
            raw_output=result.raw_output,
        )
