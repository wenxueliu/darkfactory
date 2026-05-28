"""Go checker — golangci-lint + gofmt + go vet."""

import re
from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


class GoChecker(LintChecker):
    language = "go"
    tool_name = "golangci-lint"

    @classmethod
    def handles(cls, file_path: str) -> bool:
        return file_path.endswith(".go")

    def is_available(self) -> bool:
        return tool_is_available("golangci-lint")

    def install_hint(self) -> str:
        return "go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest"

    # -- customisation points -------------------------------------------
    @staticmethod
    def severity_map() -> dict[str, Severity]:
        """Linter name → severity.  Override to adjust per-linter severity."""
        return {
            "errcheck": Severity.P0, "govet": Severity.P0, "staticcheck": Severity.P0,
            "unused": Severity.P1, "ineffassign": Severity.P1,
            "nilerr": Severity.P1, "gosec": Severity.P1,
            "revive": Severity.P2, "stylecheck": Severity.P2,
            "misspell": Severity.P2, "goimports": Severity.P2,
        }

    @staticmethod
    def auto_fixable_rules() -> set[str]:
        return {"gofmt", "goimports", "misspell"}

    def _check_cmd(self, files: list[str]) -> list[str]:
        return ["golangci-lint", "run"] + files

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        cmds = [["golangci-lint", "run", "--fix"] + files]
        if tool_is_available("gofmt"):
            cmds.append(["gofmt", "-w"] + files)
        if tool_is_available("goimports"):
            cmds.append(["goimports", "-w"] + files)
        return cmds

    # -- severity helper ------------------------------------------------
    @classmethod
    def _map_severity(cls, linter: str) -> Severity:
        sm = cls.severity_map()
        return sm.get(linter, Severity.P3)

    # -- parsing --------------------------------------------------------
    @classmethod
    def _parse_line(cls, raw: str) -> LintError | None:
        """golangci-lint output: ``file:line:col: message (linter)``"""
        m = re.match(r"^(.+?):(\d+):(\d+):\s+(.+?)\s+\((\w+)\)\s*$", raw.strip())
        if not m:
            return None
        linter = m.group(5)
        return LintError(
            file=m.group(1),
            line=int(m.group(2)),
            column=int(m.group(3)),
            rule=linter,
            message=m.group(4),
            severity=cls._map_severity(linter),
            auto_fixable=linter in cls.auto_fixable_rules(),
            raw_line=raw.strip(),
        )

    def check(self, files: list[str]) -> CheckResult:
        if not files:
            return CheckResult(language=self.language, tool_name=self.tool_name, exit_code=0)

        errors: list[LintError] = []
        combined_rc = 0

        # golangci-lint
        if self.is_available():
            rc, out, err = self.run(self._check_cmd(files))
            for line in out.splitlines() + err.splitlines():
                parsed = self._parse_line(line)
                if parsed:
                    errors.append(parsed)
            combined_rc = combined_rc or rc

        # gofmt
        if tool_is_available("gofmt"):
            fmt_rc, fmt_out, fmt_err = self.run(["gofmt", "-d"] + files)
            for line in fmt_out.splitlines():
                if line.startswith("diff "):
                    parts = line.split()
                    if len(parts) >= 4:
                        fname = parts[3].replace("b/", "")
                        errors.append(LintError(
                            file=fname, line=None, column=None, rule="gofmt",
                            message="File needs formatting (gofmt)", severity=Severity.P2,
                            auto_fixable=True, raw_line=line.strip(),
                        ))
            combined_rc = combined_rc or fmt_rc

        # go vet
        if tool_is_available("go"):
            vet_rc, vet_out, vet_err = self.run(["go", "vet"] + files)
            for line in vet_out.splitlines() + vet_err.splitlines():
                m = re.match(r"^(.+\.go):(\d+):(\d+):\s+(.+)$", line.strip())
                if m:
                    errors.append(LintError(
                        file=m.group(1), line=int(m.group(2)),
                        column=int(m.group(3)), rule="govet",
                        message=m.group(4), severity=Severity.P0,
                        auto_fixable=False, raw_line=line.strip(),
                    ))
            combined_rc = combined_rc or vet_rc

        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name, exit_code=combined_rc,
                errors=errors, tool_missing=True, install_hint=self.install_hint(),
            )
        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=combined_rc, errors=errors,
            raw_output="",
        )

    def auto_fix(self, files: list[str]) -> FixResult:
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
