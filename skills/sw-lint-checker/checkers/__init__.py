"""Checker auto-discovery.

Import every checker module so ``discover_checkers()`` can enumerate all
concrete ``LintChecker`` subclasses known to the package.

To add a new language checker:
    1. Create ``checkers/newlang_checker.py`` with a ``LintChecker`` subclass.
    2. Add ``from . import newlang_checker`` below.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import LintChecker

# -- explicit imports trigger class registration ----------------------------
from . import python_checker       # noqa: F401
from . import javascript_checker   # noqa: F401
from . import typescript_checker   # noqa: F401
from . import go_checker           # noqa: F401
from . import shell_checker        # noqa: F401
from . import markdown_checker     # noqa: F401
from . import css_checker          # noqa: F401
from . import dockerfile_checker   # noqa: F401
from . import yaml_checker         # noqa: F401
from . import toml_checker         # noqa: F401
from . import json_checker         # noqa: F401

# Collect references to the imported modules (not their classes yet) so the
# discovery function can walk each module's namespace.
_IMPORTED_MODULES = [
    python_checker,
    javascript_checker,
    typescript_checker,
    go_checker,
    shell_checker,
    markdown_checker,
    css_checker,
    dockerfile_checker,
    yaml_checker,
    toml_checker,
    json_checker,
]


# -- discovery --------------------------------------------------------------

def discover_checkers() -> list[type[LintChecker]]:
    """Return every concrete ``LintChecker`` subclass from imported modules."""
    from .base import LintChecker

    result: list[type[LintChecker]] = []
    for mod in _IMPORTED_MODULES:
        for _name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, LintChecker) and obj is not LintChecker:
                result.append(obj)
    return result


def checker_for_file(file_path: str) -> type[LintChecker] | None:
    """Return the first checker whose ``handles()`` matches *file_path*."""
    for cls in discover_checkers():
        if cls.handles(file_path):
            return cls
    return None
