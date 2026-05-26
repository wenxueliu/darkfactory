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

    @staticmethod
    def _map_severity(linter: str) -> Severity:
        critical = {"errcheck", "govet", "staticcheck"}
        major = {"unused", "ineffassign", "nilerr", "gosec"}
        if linter in critical:
            return Severity.P0
        if linter in major:
            return Severity.P1
        if linter in {"revive", "stylecheck", "misspell", "goimports"}:
            return Severity.P2
        return Severity.P3  # gosimple, etc.

    @staticmethod
    def _parse_line(raw: str) -> LintError | None:
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
            severity=GoChecker._map_severity(linter),
            auto_fixable=linter in {"gofmt", "goimports", "misspell"},
            raw_line=raw.strip(),
        )

    def check(self, files: list[str]) -> CheckResult:
        if not files:
            return CheckResult(language=self.language, tool_name=self.tool_name, exit_code=0)

        errors: list[LintError] = []

        # golangci-lint
        if self.is_available():
            rc, out, err = self.run(["golangci-lint", "run"] + files)
            for line in out.splitlines() + err.splitlines():
                parsed = self._parse_line(line)
                if parsed:
                    errors.append(parsed)
            lint_rc = rc
        else:
            lint_rc = 0

        # gofmt
        if tool_is_available("gofmt"):
            fmt_rc, fmt_out, fmt_err = self.run(["gofmt", "-d"] + files)
            for line in fmt_out.splitlines():
                if line.startswith("diff "):
                    # Parse filename from diff line: diff a/foo.go b/foo.go
                    parts = line.split()
                    if len(parts) >= 4:
                        fname = parts[3].replace("b/", "")
                        errors.append(LintError(
                            file=fname, line=None, column=None, rule="gofmt",
                            message="File needs formatting (gofmt)", severity=Severity.P2,
                            auto_fixable=True, raw_line=line.strip(),
                        ))
        else:
            fmt_rc = 0

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
        else:
            vet_rc = 0

        combined_rc = lint_rc or fmt_rc or vet_rc
        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name, exit_code=combined_rc,
                errors=errors, tool_missing=True, install_hint=self.install_hint(),
            )
        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=combined_rc, errors=errors,
            raw_output="\n".join(filter(None, [out if 'out' in dir() else "", err if 'err' in dir() else ""])),
        )

    def auto_fix(self, files: list[str]) -> FixResult:
        if self.is_available():
            self.run(["golangci-lint", "run", "--fix"] + files)
        if tool_is_available("gofmt"):
            self.run(["gofmt", "-w"] + files)
        if tool_is_available("goimports"):
            self.run(["goimports", "-w"] + files)
        result = self.check(files)
        return FixResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=result.exit_code,
            fixed_count=max(0, len(files)),
            remaining_errors=result.errors,
            raw_output=result.raw_output,
        )
