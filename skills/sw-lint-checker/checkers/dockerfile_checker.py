"""Dockerfile checker — hadolint."""

from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available

# Filenames matched without extension
DOCKERFILE_PATTERNS = ("Dockerfile", "dockerfile")


class DockerfileChecker(LintChecker):
    language = "dockerfile"
    tool_name = "hadolint"

    @classmethod
    def handles(cls, file_path: str) -> bool:
        import os
        base = os.path.basename(file_path)
        if base == "Dockerfile" or base.startswith("Dockerfile."):
            return True
        if base.endswith(".dockerfile") or base == "dockerfile":
            return True
        return False

    def is_available(self) -> bool:
        return tool_is_available("hadolint")

    def install_hint(self) -> str:
        return "apt install hadolint / brew install hadolint"

    @staticmethod
    def _map_severity(level: str) -> Severity:
        return {"error": Severity.P0, "warning": Severity.P1,
                "info": Severity.P2, "style": Severity.P3}.get(level, Severity.P2)

    def check(self, files: list[str]) -> CheckResult:
        if not files:
            return CheckResult(language=self.language, tool_name=self.tool_name, exit_code=0)
        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name, exit_code=-1,
                tool_missing=True, install_hint=self.install_hint(),
            )

        errors: list[LintError] = []
        combined_rc = 0
        all_out: list[str] = []
        all_err: list[str] = []

        import re
        for f in files:
            rc, out, err = self.run(["hadolint", f])
            all_out.append(out)
            all_err.append(err)
            combined_rc = combined_rc or rc
            for line in (out + "\n" + err).splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                # hadolint format: file:line DL#### level message
                m = re.match(
                    r"^.+?:(\d+)\s+(DL\d+)\s+(error|warning|info|style)\s+(.+)$",
                    stripped,
                )
                if m:
                    errors.append(LintError(
                        file=f, line=int(m.group(1)), column=None,
                        rule=m.group(2), message=m.group(4),
                        severity=self._map_severity(m.group(3)),
                        auto_fixable=False,  # hadolint has no auto-fix
                        raw_line=stripped,
                    ))

        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=combined_rc, errors=errors,
            raw_output="\n".join(all_out + all_err),
        )

    def auto_fix(self, files: list[str]) -> FixResult:
        # hadolint has no auto-fix
        result = self.check(files)
        return FixResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=result.exit_code, fixed_count=0,
            remaining_errors=result.errors,
            raw_output=result.raw_output,
        )
