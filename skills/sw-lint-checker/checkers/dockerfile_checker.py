"""Dockerfile checker — hadolint."""

import re
from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


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

    # -- customisation points -------------------------------------------
    @staticmethod
    def severity_map() -> dict[str, Severity]:
        return {"error": Severity.P0, "warning": Severity.P1,
                "info": Severity.P2, "style": Severity.P3}

    def _check_cmd(self, files: list[str]) -> list[str]:
        # hadolint processes one file at a time; build for first file
        return ["hadolint", files[0]] if files else ["hadolint"]

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        return []  # hadolint has no auto-fix

    @classmethod
    def _map_severity(cls, level: str) -> Severity:
        return cls.severity_map().get(level, Severity.P2)

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

        for f in files:
            rc, out, err = self.run(["hadolint", f])
            all_out.append(out)
            all_err.append(err)
            combined_rc = combined_rc or rc
            for line in (out + "\n" + err).splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                m = re.match(
                    r"^.+?:(\d+)\s+(DL\d+)\s+(error|warning|info|style)\s+(.+)$",
                    stripped,
                )
                if m:
                    errors.append(LintError(
                        file=f, line=int(m.group(1)), column=None,
                        rule=m.group(2), message=m.group(4),
                        severity=self._map_severity(m.group(3)),
                        auto_fixable=False,
                        raw_line=stripped,
                    ))

        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=combined_rc, errors=errors,
            raw_output="\n".join(all_out + all_err),
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
