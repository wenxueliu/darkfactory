"""Shell checker — shellcheck + shfmt."""

import re
from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


SHELL_EXTENSIONS = {".sh", ".bash", ".zsh", ".dash"}
SHELL_SHEBANGS = ("/bash", "/sh", "/zsh", "/dash", "/ksh")


class ShellChecker(LintChecker):
    language = "shell"
    tool_name = "shellcheck"

    @classmethod
    def handles(cls, file_path: str) -> bool:
        if file_path.endswith(tuple(SHELL_EXTENSIONS)):
            return True
        # extensionless file with shell shebang
        try:
            with open(file_path) as f:
                first = f.readline()
            return any(s in first for s in SHELL_SHEBANGS) and first.startswith("#!")
        except (OSError, UnicodeDecodeError):
            return False

    def is_available(self) -> bool:
        return tool_is_available("shellcheck")

    def install_hint(self) -> str:
        return "apt install shellcheck"

    @staticmethod
    def _map_severity(level: str) -> Severity:
        return {"error": Severity.P0, "warning": Severity.P1,
                "info": Severity.P2, "style": Severity.P3}.get(level, Severity.P2)

    @staticmethod
    def _parse_line(raw: str) -> LintError | None:
        """shellcheck output: ``file:line:col: level: message [SC####]``"""
        m = re.match(
            r"^(.+?):(\d+):(\d+):\s+(error|warning|info|style):\s+(.+?)\s+\[(SC\d+)\]\s*$",
            raw.strip(),
        )
        if not m:
            # Older format: In file line N:
            return None
        return LintError(
            file=m.group(1),
            line=int(m.group(2)),
            column=int(m.group(3)),
            rule=m.group(6),
            message=m.group(5),
            severity=ShellChecker._map_severity(m.group(4)),
            auto_fixable=False,  # shellcheck has no auto-fix
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

        # shellcheck
        rc, out, err = self.run(["shellcheck"] + files)
        errors: list[LintError] = []
        for line in (out + "\n" + err).splitlines():
            if not line.strip():
                continue
            parsed = self._parse_line(line)
            if parsed:
                errors.append(parsed)

        # shfmt --diff
        if tool_is_available("shfmt"):
            fmt_rc, fmt_out, fmt_err = self.run(["shfmt", "-d"] + files)
            for line in fmt_out.splitlines():
                if line.strip():
                    errors.append(LintError(
                        file="", line=None, column=None, rule="shfmt",
                        message="Shell file would be reformatted",
                        severity=Severity.P2, auto_fixable=True,
                        raw_line=line.strip(),
                    ))

        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=rc, errors=errors,
            raw_output="\n".join(filter(None, [out, err])),
        )

    def auto_fix(self, files: list[str]) -> FixResult:
        # shellcheck: no auto-fix
        # shfmt: auto-format
        if tool_is_available("shfmt"):
            self.run(["shfmt", "-w"] + files)
        result = self.check(files)
        return FixResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=result.exit_code,
            fixed_count=max(0, len(files)) if tool_is_available("shfmt") else 0,
            remaining_errors=result.errors,
            raw_output=result.raw_output,
        )
