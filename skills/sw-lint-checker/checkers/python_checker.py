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

    # -- customisation points -------------------------------------------
    @staticmethod
    def severity_map() -> dict[str, Severity]:
        """Rule-prefix → severity.  Override to adjust P0/P1/P2/P3."""
        return {
            "E": Severity.P0,
            "F": Severity.P1,
            "W": Severity.P2, "I": Severity.P2, "N": Severity.P2,
            "UP": Severity.P2, "B": Severity.P2, "A": Severity.P2,
            "PLE": Severity.P2, "PLW": Severity.P2, "RUF": Severity.P2,
        }

    @staticmethod
    def auto_fixable_rules() -> set[str]:
        """Rules ruff --fix can handle."""
        return {
            "F401", "F841", "E711", "W291", "I001", "UP006", "SIM108",
            "UP007", "UP035", "SIM118", "C401", "C403", "C407",
        }

    def _check_cmd(self, files: list[str]) -> list[str]:
        """Primary check command.  Override to switch tool or add flags."""
        return ["ruff", "check"] + files

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        """Fix commands run sequentially.  Override to reorder or change."""
        return [
            ["ruff", "check", "--fix"] + files,
            ["ruff", "format"] + files,
        ]

    # -- severity helper ------------------------------------------------
    @classmethod
    def _map_severity(cls, rule: str) -> Severity:
        sm = cls.severity_map()
        # Try exact match first, then prefix match
        if rule in sm:
            return sm[rule]
        for prefix, sev in sorted(sm.items(), key=lambda x: -len(x[0])):
            if rule.startswith(prefix):
                return sev
        return Severity.P3  # SIM, PLC, CPY, etc.

    # -- parsing --------------------------------------------------------
    @classmethod
    def _parse_line(cls, raw: str) -> LintError | None:
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
            severity=cls._map_severity(rule),
            auto_fixable=rule in cls.auto_fixable_rules(),
            raw_line=raw.strip(),
        )

    # -- check ----------------------------------------------------------
    def check(self, files: list[str]) -> CheckResult:
        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name, exit_code=-1,
                tool_missing=True, install_hint=self.install_hint(),
            )

        cmd = self._check_cmd(files)
        rc, out, err = self.run(cmd)
        errors: list[LintError] = []
        for line in out.splitlines() + err.splitlines():
            if not line.strip():
                continue
            parsed = self._parse_line(line)
            if parsed:
                errors.append(parsed)

        # ruff format --check (secondary)
        fmt_rc, fmt_out, fmt_err = self.run(["ruff", "format", "--check"] + files)
        for line in fmt_out.splitlines() + fmt_err.splitlines():
            stripped = line.strip()
            if not stripped or "would reformat" not in stripped:
                continue
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
        for cmd in self._fix_cmds(files):
            self.run(cmd)
        result = self.check(files)
        return FixResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=result.exit_code,
            fixed_count=max(0, len(files) * len(self._fix_cmds(files))),
            remaining_errors=result.errors,
            raw_output=result.raw_output,
        )
