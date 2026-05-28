"""YAML checker — yamllint."""

import re
from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


class YamlChecker(LintChecker):
    language = "yaml"
    tool_name = "yamllint"

    @classmethod
    def handles(cls, file_path: str) -> bool:
        return file_path.endswith((".yaml", ".yml"))

    def is_available(self) -> bool:
        return tool_is_available("yamllint")

    def install_hint(self) -> str:
        return "pip install yamllint"

    # -- customisation points -------------------------------------------
    @staticmethod
    def severity_map() -> dict[str, Severity]:
        return {"error": Severity.P2, "warning": Severity.P3}

    def _check_cmd(self, files: list[str]) -> list[str]:
        return ["yamllint"] + files

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        # yamllint has no auto-fix; prettier can format YAML
        if tool_is_available("npx"):
            return [["npx", "prettier", "--write"] + files]
        return []

    @staticmethod
    def _map_severity(level: str) -> Severity:
        return YamlChecker.severity_map().get(level, Severity.P3)

    @staticmethod
    def _parse_line(raw: str) -> LintError | None:
        """yamllint output: ``file:line:col: [level] message (rule)``"""
        m = re.match(
            r"^(.+?):(\d+):(\d+):\s+\[(error|warning)\]\s+(.+?)\s+\((.+?)\)\s*$",
            raw.strip(),
        )
        if not m:
            return None
        return LintError(
            file=m.group(1),
            line=int(m.group(2)),
            column=int(m.group(3)),
            rule=m.group(6),
            message=m.group(5),
            severity=YamlChecker._map_severity(m.group(4)),
            auto_fixable=False,
            raw_line=raw.strip(),
        )

    def check(self, files: list[str]) -> CheckResult:
        if not files:
            return CheckResult(language=self.language, tool_name=self.tool_name, exit_code=0)
        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name, exit_code=-1,
                tool_missing=True, install_hint=self.install_hint(),
            )

        rc, out, err = self.run(self._check_cmd(files))
        errors: list[LintError] = []
        for line in (out + "\n" + err).splitlines():
            parsed = self._parse_line(line)
            if parsed:
                errors.append(parsed)

        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=rc, errors=errors,
            raw_output="\n".join(filter(None, [out, err])),
        )

    def auto_fix(self, files: list[str]) -> FixResult:
        for cmd in self._fix_cmds(files):
            self.run(cmd)
        result = self.check(files)
        return FixResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=result.exit_code, fixed_count=0,
            remaining_errors=result.errors,
            raw_output=result.raw_output,
        )
