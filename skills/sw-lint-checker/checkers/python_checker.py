"""Python checker — ruff check + ruff format."""

import re
from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


class PythonChecker(LintChecker):
    language = "python"
    tool_name = "ruff"

    # -- file matching --------------------------------------------------
    @classmethod
    def handles(cls, file_path: str) -> bool:
        return file_path.endswith((".py", ".pyi", ".pyx"))

    # -- availability ---------------------------------------------------
    def is_available(self) -> bool:
        return tool_is_available("ruff")

    def install_hint(self) -> str:
        return "pip install ruff"

    # -- ruff severity → Harness ----------------------------------------
    @staticmethod
    def _map_severity(rule: str) -> Severity:
        if rule.startswith("E"):
            return Severity.P0
        if rule.startswith("F"):
            return Severity.P1
        if rule.startswith(("W", "I", "N", "UP", "B", "A", "PLE", "PLW", "RUF")):
            return Severity.P2
        return Severity.P3  # SIM, PLC, CPY, etc.

    @staticmethod
    def _parse_line(raw: str) -> LintError | None:
        """ruff output: ``file:line:col: RULE message``"""
        m = re.match(r"^(.+?):(\d+):(\d+):\s+(\w+)\s+(.+)$", raw.strip())
        if not m:
            return None
        rule = m.group(4)
        return LintError(
            file=m.group(1),
            line=int(m.group(2)),
            column=int(m.group(3)),
            rule=rule,
            message=m.group(5),
            severity=PythonChecker._map_severity(rule),
            auto_fixable=rule in {
                "F401", "F841", "E711", "W291", "I001", "UP006", "SIM108",
                "UP007", "UP035", "SIM118", "C401", "C403", "C407",
            },
            raw_line=raw.strip(),
        )

    # -- check ----------------------------------------------------------
    def check(self, files: list[str]) -> CheckResult:
        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name, exit_code=-1,
                tool_missing=True, install_hint=self.install_hint(),
            )

        # ruff check
        cmd = ["ruff", "check"] + files
        rc, out, err = self.run(cmd)
        errors: list[LintError] = []
        for line in out.splitlines() + err.splitlines():
            if not line.strip():
                continue
            parsed = self._parse_line(line)
            if parsed:
                errors.append(parsed)

        # ruff format --check (only if ruff check was clean or as extra info)
        fmt_rc, fmt_out, fmt_err = self.run(["ruff", "format", "--check"] + files)
        for line in fmt_out.splitlines() + fmt_err.splitlines():
            stripped = line.strip()
            if not stripped or "would reformat" not in stripped:
                continue
            # Extract file name from "Would reformat: path/to/file.py"
            file_part = stripped.split("Would reformat:", 1)[-1].strip()
            errors.append(LintError(
                file=file_part, line=None, column=None, rule="format",
                message="File would be reformatted",
                severity=Severity.P2, auto_fixable=True, raw_line=stripped,
            ))

        combined_rc = rc or fmt_rc
        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=combined_rc, errors=errors,
            raw_output="\n".join(filter(None, [out, err, fmt_out, fmt_err])),
        )

    # -- auto-fix -------------------------------------------------------
    def auto_fix(self, files: list[str]) -> FixResult:
        if not self.is_available():
            return FixResult(
                language=self.language, tool_name=self.tool_name,
                exit_code=-1, fixed_count=0,
            )
        # 1. ruff check --fix
        self.run(["ruff", "check", "--fix"] + files)
        # 2. ruff format
        self.run(["ruff", "format"] + files)
        # 3. re-check for remaining
        result = self.check(files)
        return FixResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=result.exit_code,
            fixed_count=max(0, len(files) * 2),  # best-effort count
            remaining_errors=result.errors,
            raw_output=result.raw_output,
        )
