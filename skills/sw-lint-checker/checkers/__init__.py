"""Checker auto-discovery.

Import every built-in checker module so ``discover_checkers()`` can enumerate
all concrete ``LintChecker`` subclasses known to the package.

**Business customization:** Place subclass modules in the ``checkers_local/``
directory (sibling to this ``checkers/`` directory).  Local checkers are
discovered first and take priority over built-in checkers for the same language.

To add a new language checker locally:
    1. Create ``checkers_local/newlang_checker.py`` with a ``LintChecker`` subclass.
    2. Done — ``discover_checkers()`` auto-discovers it.

To add a new language checker to the framework:
    1. Create ``checkers/newlang_checker.py`` with a ``LintChecker`` subclass.
    2. Add ``from . import newlang_checker`` below and to ``_BUILTIN_MODULES``.
"""

from __future__ import annotations

import inspect
import importlib.util
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import LintChecker

# -- built-in checker imports ------------------------------------------------
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

_BUILTIN_MODULES = [
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

_LOCAL_DIR = Path(__file__).resolve().parent.parent / "checkers_local"


# -- local discovery ---------------------------------------------------------

def _discover_local_modules() -> list:
    """Import all ``.py`` files from ``checkers_local/`` and return the
    module objects.  Returns an empty list if the directory doesnʼt exist."""
    if not _LOCAL_DIR.is_dir():
        return []

    # Ensure checkers_local/ is importable
    parent_dir = str(_LOCAL_DIR.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    modules: list = []
    for fname in sorted(os.listdir(_LOCAL_DIR)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        mod_name = fname[:-3]  # strip .py
        try:
            spec = importlib.util.spec_from_file_location(
                f"checkers_local.{mod_name}",
                str(_LOCAL_DIR / fname),
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                modules.append(mod)
        except Exception:
            # Skip broken local modules silently — the built-in fallback
            # will still handle that language.
            pass
    return modules


# -- discovery --------------------------------------------------------------

def discover_checkers() -> list[type[LintChecker]]:
    """Return every concrete ``LintChecker`` subclass.

    **Local-first:** classes from ``checkers_local/`` take priority over
    built-in checkers for the same language.  If a local checker handles
    ``"python"``, the built-in ``PythonChecker`` is excluded.
    """
    from .base import LintChecker

    def _classes_from_modules(mod_list: list) -> list[type[LintChecker]]:
        result: list[type[LintChecker]] = []
        for mod in mod_list:
            for _name, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, LintChecker) and obj is not LintChecker:
                    result.append(obj)
        return result

    local_modules = _discover_local_modules()
    local_classes = _classes_from_modules(local_modules)

    # Determine which languages are covered by local checkers
    covered_languages: set[str] = set()
    for cls in local_classes:
        # language is a class attribute (set on the class, not the instance)
        lang = getattr(cls, "language", "")
        if lang:
            covered_languages.add(lang)

    # Built-in classes, minus those whose language is already covered locally
    builtin_classes = _classes_from_modules(_BUILTIN_MODULES)
    for cls in builtin_classes:
        lang = getattr(cls, "language", "")
        if lang not in covered_languages:
            local_classes.append(cls)

    return local_classes


def checker_for_file(file_path: str) -> type[LintChecker] | None:
    """Return the first checker whose ``handles()`` matches *file_path*."""
    for cls in discover_checkers():
        if cls.handles(file_path):
            return cls
    return None
