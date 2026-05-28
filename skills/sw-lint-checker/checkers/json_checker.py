"""JSON checker — prettier (+ jsonlint fallback)."""

from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


class JsonChecker(LintChecker):
    language = "json"
    tool_name = "prettier"

    @classmethod
    def handles(cls, file_path: str) -> bool:
        return file_path.endswith(".json")

    def is_available(self) -> bool:
        return tool_is_available("npx")

    def install_hint(self) -> str:
        return "npm install -D prettier"

    # -- customisation points -------------------------------------------
    def _check_cmd(self, files: list[str]) -> list[str]:
        return ["npx", "prettier", "--check"] + files

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        return [["npx", "prettier", "--write"] + files]

    def check(self, files: list[str]) -> CheckResult:
        if not files:
            return CheckResult(language=self.language, tool_name=self.tool_name, exit_code=0)
        if not self.is_available():
            # Python fallback: validate JSON syntax
            import json as _json
            errors: list[LintError] = []
            for f in files:
                try:
                    with open(f) as fh:
                        _json.load(fh)
                except _json.JSONDecodeError as e:
                    errors.append(LintError(
                        file=f, line=e.lineno, column=e.colno,
                        rule="json-parse", message=e.msg,
                        severity=Severity.P0, auto_fixable=False,
                        raw_line=str(e),
                    ))
            combined_rc = 1 if errors else 0
            return CheckResult(
                language=self.language, tool_name="jsonlint",
                exit_code=combined_rc, errors=errors,
                tool_missing=True, install_hint=self.install_hint(),
            )

        rc, out, err = self.run(self._check_cmd(files))
        errors: list[LintError] = []
        for line in out.splitlines() + err.splitlines():
            stripped = line.strip()
            if stripped.startswith("[warn] "):
                stripped = stripped[7:]
            elif stripped.startswith("[error] "):
                stripped = stripped[8:]
            if stripped and stripped.endswith(".json"):
                errors.append(LintError(
                    file=stripped, line=None, column=None, rule="prettier",
                    message="File would be formatted", severity=Severity.P2,
                    auto_fixable=True, raw_line=stripped,
                ))

        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=rc, errors=errors,
            raw_output="\n".join(filter(None, [out, err])),
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
