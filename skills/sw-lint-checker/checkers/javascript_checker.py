"""JavaScript checker — eslint + prettier."""

import re
from .base import CheckResult, FixResult, LintError, LintChecker, Severity, tool_is_available


class JavaScriptChecker(LintChecker):
    language = "javascript"
    tool_name = "eslint"

    @classmethod
    def handles(cls, file_path: str) -> bool:
        # TypeScript handled by TypescriptChecker
        if file_path.endswith((".ts", ".tsx", ".mts", ".cts")):
            return False
        return file_path.endswith((".js", ".mjs", ".cjs")) or (
            "." not in file_path and cls._has_node_shebang(file_path)
        )

    @staticmethod
    def _has_node_shebang(file_path: str) -> bool:
        try:
            with open(file_path) as f:
                first = f.readline()
            return "node" in first and first.startswith("#!")
        except (OSError, UnicodeDecodeError):
            return False

    def is_available(self) -> bool:
        return tool_is_available("npx")

    def install_hint(self) -> str:
        return "npm install -D eslint"

    # -- customisation points -------------------------------------------
    @staticmethod
    def severity_map() -> dict[str, Severity]:
        """eslint severity level → Harness.  error→P0, warning→P2."""
        return {"error": Severity.P0, "warning": Severity.P2}

    @staticmethod
    def auto_fixable_rules() -> set[str]:
        return {
            "semi", "quotes", "indent", "no-var", "prefer-const",
            "eqeqeq", "arrow-parens", "comma-dangle", "comma-spacing",
            "comma-style", "key-spacing", "object-curly-spacing",
            "space-before-blocks", "space-infix-ops", "space-unary-ops",
            "eol-last", "no-multi-spaces", "no-trailing-spaces",
        }

    def _check_cmd(self, files: list[str]) -> list[str]:
        return ["npx", "eslint"] + files

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        return [
            ["npx", "eslint", "--fix"] + files,
            ["npx", "prettier", "--write"] + files,
        ]

    # -- eslint output parsing ------------------------------------------
    @classmethod
    def _parse_line(cls, raw: str) -> LintError | None:
        """eslint stylish/formatter output patterns handled."""
        raw_s = raw.strip()
        # Pattern: /path/to/file.js
        m = re.match(r"^(.+?\.\w+)\s*$", raw_s)
        if m:
            return None  # file header line, followed by detail lines
        m = re.match(
            r"^\s+(\d+):(\d+)\s+(error|warning)\s+(.+?)\s{2,}([\w\-/]+)\s*$",
            raw_s,
        )
        if m:
            sev_map = cls.severity_map()
            sev = sev_map.get(m.group(3), Severity.P2)
            return LintError(
                file="",  # filled by caller
                line=int(m.group(1)),
                column=int(m.group(2)),
                rule=m.group(5),
                message=m.group(4),
                severity=sev,
                auto_fixable=m.group(5) in cls.auto_fixable_rules(),
                raw_line=raw_s,
            )
        # Compact: file:line:col: error  message  rule [compact formatter]
        m = re.match(
            r"^(.+?):(\d+):(\d+):\s+(error|warning)\s+(.+?)\s{2,}([\w\-/]+)\s*$",
            raw_s,
        )
        if m:
            sev_map = cls.severity_map()
            sev = sev_map.get(m.group(4), Severity.P2)
            return LintError(
                file=m.group(1),
                line=int(m.group(2)),
                column=int(m.group(3)),
                rule=m.group(6),
                message=m.group(5),
                severity=sev,
                auto_fixable=m.group(6) in cls.auto_fixable_rules(),
                raw_line=raw_s,
            )
        return None

    def check(self, files: list[str]) -> CheckResult:
        if not files:
            return CheckResult(language=self.language, tool_name=self.tool_name, exit_code=0)
        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name, exit_code=-1,
                tool_missing=True, install_hint=self.install_hint(),
            )
        # eslint
        eslint_rc, eslint_out, eslint_err = self.run(self._check_cmd(files))
        errors: list[LintError] = []
        current_file = ""
        for line in eslint_out.splitlines() + eslint_err.splitlines():
            stripped = line.strip()
            if stripped.endswith((".js", ".mjs", ".cjs")) and ":" not in stripped:
                current_file = stripped
                continue
            parsed = self._parse_line(line)
            if parsed:
                if not parsed.file and current_file:
                    parsed.file = current_file
                if parsed.file:
                    errors.append(parsed)

        # prettier --check
        fmt_rc, fmt_out, fmt_err = self.run(["npx", "prettier", "--check"] + files)
        for line in fmt_out.splitlines() + fmt_err.splitlines():
            stripped = line.strip()
            if stripped.startswith("[warn] "):
                stripped = stripped[7:]
            elif stripped.startswith("[error] "):
                stripped = stripped[8:]
            if stripped and stripped.endswith((".js", ".mjs", ".cjs", ".json", ".css", ".md")):
                errors.append(LintError(
                    file=stripped, line=None, column=None, rule="prettier",
                    message="File would be formatted", severity=Severity.P2,
                    auto_fixable=True, raw_line=stripped,
                ))

        combined_rc = eslint_rc or fmt_rc
        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=combined_rc, errors=errors,
            raw_output="\n".join(filter(None, [eslint_out, eslint_err, fmt_out, fmt_err])),
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
