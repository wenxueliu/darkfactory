"""TOML checker — taplo."""

from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


class TomlChecker(LintChecker):
    language = "toml"
    tool_name = "taplo"

    @classmethod
    def handles(cls, file_path: str) -> bool:
        return file_path.endswith(".toml")

    def is_available(self) -> bool:
        return tool_is_available("taplo")

    def install_hint(self) -> str:
        return "npm install -D @taplo/cli  OR  cargo install taplo-cli"

    # -- customisation points -------------------------------------------
    def _check_cmd(self, files: list[str]) -> list[str]:
        return ["taplo", "format", "--check"] + files

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        return [["taplo", "format"] + files]

    def check(self, files: list[str]) -> CheckResult:
        if not files:
            return CheckResult(language=self.language, tool_name=self.tool_name, exit_code=0)
        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name, exit_code=-1,
                tool_missing=True, install_hint=self.install_hint(),
            )

        errors: list[LintError] = []

        rc, out, err = self.run(self._check_cmd(files))
        for line in out.splitlines() + err.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            errors.append(LintError(
                file="", line=None, column=None, rule="taplo",
                message=stripped, severity=Severity.P2,
                auto_fixable=True, raw_line=stripped,
            ))

        # taplo lint
        lint_rc, lint_out, lint_err = self.run(["taplo", "lint"] + files)
        for line in lint_out.splitlines() + lint_err.splitlines():
            stripped = line.strip()
            if not stripped or "error" not in stripped.lower():
                continue
            errors.append(LintError(
                file="", line=None, column=None, rule="taplo",
                message=stripped, severity=Severity.P1,
                auto_fixable=False, raw_line=stripped,
            ))

        combined_rc = rc or lint_rc
        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=combined_rc, errors=errors,
            raw_output="\n".join(filter(None, [out, err, lint_out, lint_err])),
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
