"""Markdown checker — markdownlint."""

import re
from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


class MarkdownChecker(LintChecker):
    language = "markdown"
    tool_name = "markdownlint"

    @classmethod
    def handles(cls, file_path: str) -> bool:
        return file_path.endswith((".md", ".mdx"))

    def is_available(self) -> bool:
        return tool_is_available("npx")

    def install_hint(self) -> str:
        return "npm install -D markdownlint-cli"

    # -- customisation points -------------------------------------------
    @staticmethod
    def auto_fixable_rules() -> set[str]:
        return {"MD009", "MD012", "MD022", "MD029", "MD031", "MD032", "MD047"}

    def _check_cmd(self, files: list[str]) -> list[str]:
        return ["npx", "markdownlint"] + files + ["--ignore", "node_modules"]

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        return [["npx", "markdownlint", "--fix"] + files + ["--ignore", "node_modules"]]

    # -- parsing --------------------------------------------------------
    @classmethod
    def _parse_line(cls, raw: str) -> LintError | None:
        """markdownlint output: ``file:line:col MD###/rule-name message`` or
        ``file:line MD### message``"""
        m = re.match(
            r"^(.+?):(\d+):?(\d*)\s+(MD\d+)/([\w\-]+)\s+(.+)$",
            raw.strip(),
        )
        if not m:
            m = re.match(r"^(.+?):(\d+)\s+(MD\d+)\s+(.+)$", raw.strip())
            if not m:
                return None
            return LintError(
                file=m.group(1), line=int(m.group(2)), column=None,
                rule=m.group(3), message=m.group(4),
                severity=Severity.P3,
                auto_fixable=m.group(3) in cls.auto_fixable_rules(),
                raw_line=raw.strip(),
            )
        return LintError(
            file=m.group(1),
            line=int(m.group(2)),
            column=int(m.group(3)) if m.group(3) else None,
            rule=m.group(4),
            message=m.group(6),
            severity=Severity.P3,
            auto_fixable=m.group(4) in cls.auto_fixable_rules(),
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
        for line in out.splitlines() + err.splitlines():
            parsed = self._parse_line(line)
            if parsed:
                errors.append(parsed)
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
