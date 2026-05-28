"""
Example: Custom Python checker that uses flake8 instead of ruff.

Place your custom checker modules in this ``checkers_local/`` directory.
They are discovered automatically and take priority over built-in checkers
for the same language.

To use:
    1. Copy this file as ``python_checker.py`` (or your own name).
    2. Edit the class — override only what you need to change.
    3. Run ``python lint_runner.py --auto-fix --json`` as usual.

The local checker is picked up automatically — no changes to the
framework needed.
"""

# Import from the built-in checkers package (checkers/ is on sys.path)
from checkers.python_checker import PythonChecker
from checkers.base import Severity


class Flake8PythonChecker(PythonChecker):
    """Custom Python checker: flake8 instead of ruff, stricter P0 rules."""

    tool_name = "flake8"

    # -- override tool availability --------------------------------------

    def is_available(self) -> bool:
        from checkers.base import tool_is_available
        return tool_is_available("flake8")

    def install_hint(self) -> str:
        return "pip install flake8"

    # -- override commands -----------------------------------------------

    def _check_cmd(self, files: list[str]) -> list[str]:
        cfg = self.get_config()
        cmd = ["flake8"]
        if cfg.get("config"):
            cmd += ["--config", cfg["config"]]
        return cmd + files

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        # flake8 has no auto-fix; return empty
        return []

    # -- override severity — treat all F rules as P0 --------------------

    @staticmethod
    def severity_map() -> dict[str, Severity]:
        return {
            "E": Severity.P0,  # errors
            "F": Severity.P0,  # pyflakes — promoted from P1 to P0
            "W": Severity.P1,  # warnings
            "N": Severity.P2,  # naming
        }

    @staticmethod
    def auto_fixable_rules() -> set[str]:
        return set()  # flake8 can't auto-fix


# ------------------------------------------------------------------
# Alternative: minimal override — just add a custom extension
# ------------------------------------------------------------------

class ExtendedPythonChecker(PythonChecker):
    """Same as default PythonChecker, but also handles .jinja2 files."""

    @classmethod
    def handles(cls, file_path: str) -> bool:
        if file_path.endswith(".jinja2"):
            return True
        return super().handles(file_path)
