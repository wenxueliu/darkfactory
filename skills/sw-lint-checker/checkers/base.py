"""Base class and dataclasses for language-specific lint checkers."""

import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    """Harness severity levels (P0–P3)."""
    P0 = "P0"  # Fatal — blocks all phases
    P1 = "P1"  # Severe — blocks next phase
    P2 = "P2"  # General — blocks next phase
    P3 = "P3"  # Suggestion — document only


@dataclass
class LintError:
    """A single lint / format finding."""
    file: str
    line: int | None
    rule: str          # e.g. "F401", "no-unused-vars", "SC2086"
    message: str
    severity: Severity
    auto_fixable: bool = False
    column: int | None = None   # optional — editor navigation hint
    raw_line: str = ""          # original tool output line for debugging


@dataclass
class CheckResult:
    """Full output from a single tool run."""
    language: str
    tool_name: str
    exit_code: int
    errors: list[LintError] = field(default_factory=list)
    raw_output: str = ""
    tool_missing: bool = False
    install_hint: str = ""


@dataclass
class FixResult:
    """Result of an auto-fix run."""
    language: str
    tool_name: str
    exit_code: int
    fixed_count: int
    remaining_errors: list[LintError] = field(default_factory=list)
    raw_output: str = ""


# ---------------------------------------------------------------------------
# Convenience helper for running subprocesses
# ---------------------------------------------------------------------------

def run_tool(cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """Run a lint/formatter tool and return (exit_code, stdout, stderr).

    All tool invocations go through this helper so output capture,
    timeout handling, and error reporting are uniform.
    """
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return -127, "", f"TOOL_NOT_FOUND: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -124, "", f"TIMEOUT: {' '.join(cmd)} (>{timeout}s)"


def tool_is_available(name: str) -> bool:
    """Check whether *name* is on PATH (or is npx / go / pip available)."""
    if name == "npx":
        return shutil.which("npx") is not None or shutil.which("node") is not None
    return shutil.which(name) is not None


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class LintChecker(ABC):
    """Abstract base for a language-specific lint / format checker.

    To add a new language:
        1. Subclass LintChecker.
        2. Implement every abstract method / property.
        3. Import the module in checkers/__init__.py.

    The runner calls `handles()` to map files → checker, then `check()`
    followed by `auto_fix()` (in a loop).  Everything else is internal.
    """

    # -- identity -------------------------------------------------------

    @property
    @abstractmethod
    def language(self) -> str:
        """Short language key: 'python', 'javascript', 'go', ..."""
        ...

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Primary tool name (for status reports)."""
        ...

    # -- file matching --------------------------------------------------

    @classmethod
    @abstractmethod
    def handles(cls, file_path: str) -> bool:
        """Return True if this checker should process *file_path*."""
        ...

    # -- tool availability ----------------------------------------------

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the required tool(s) can be found on PATH."""
        ...

    @abstractmethod
    def install_hint(self) -> str:
        """One-line install command for the primary tool."""
        ...

    # -- core operations -------------------------------------------------

    @abstractmethod
    def check(self, files: list[str]) -> CheckResult:
        """Run lint / format *check* on *files* (read-only — no fixes)."""
        ...

    @abstractmethod
    def auto_fix(self, files: list[str]) -> FixResult:
        """Run auto-fix on *files*.  Return count of fixed + remaining errors."""
        ...

    # -- helpers ---------------------------------------------------------

    def run(self, cmd: list[str], timeout: int = 120) -> tuple[int, str, str]:
        """Thin wrapper around run_tool for convenience."""
        return run_tool(cmd, timeout)
