"""Deployer auto-discovery.

Import every built-in deployer module so ``discover_deployers()`` can enumerate
all concrete ``Deployer`` subclasses known to the package.

**Business customization:** Place subclass modules in the ``deployers_local/``
directory (sibling to this ``deployers/`` directory).  Local deployers are
discovered first and take priority over built-in deployers for the same target.

To add a custom deployer locally:
    1. Create ``deployers_local/my_deployer.py`` with a ``Deployer`` subclass.
    2. Done — ``discover_deployers()`` auto-discovers it.

To add a built-in deployer:
    1. Create ``deployers/my_deployer.py`` with a ``Deployer`` subclass.
    2. Import it here and add to ``_BUILTIN_MODULES``.
"""

from __future__ import annotations

import importlib.util
import inspect
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import Deployer

# -- built-in deployer imports ------------------------------------------------
from . import direct_deployer   # noqa: F401
from . import docker_deployer    # noqa: F401
from . import k8s_deployer       # noqa: F401

_BUILTIN_MODULES = [
    direct_deployer,
    docker_deployer,
    k8s_deployer,
]

_LOCAL_DIR = Path(__file__).resolve().parent.parent / "deployers_local"


# -- local discovery ---------------------------------------------------------

def _discover_local_modules() -> list:
    """Import all ``.py`` files from ``deployers_local/`` and return the
    module objects.  Returns an empty list if the directory doesn't exist."""
    if not _LOCAL_DIR.is_dir():
        return []

    parent_dir = str(_LOCAL_DIR.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    modules: list = []
    for fname in sorted(os.listdir(_LOCAL_DIR)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        mod_name = fname[:-3]
        try:
            spec = importlib.util.spec_from_file_location(
                f"deployers_local.{mod_name}",
                str(_LOCAL_DIR / fname),
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                modules.append(mod)
        except Exception:
            pass
    return modules


# -- discovery --------------------------------------------------------------

def discover_deployers() -> list[type[Deployer]]:
    """Return every concrete ``Deployer`` subclass.

    **Local-first:** classes from ``deployers_local/`` take priority over
    built-in deployers for the same target.  If a local deployer has
    ``target = "test"``, the built-in ``DirectDeployer`` is excluded.
    """
    from .base import Deployer

    def _classes_from_modules(mod_list: list) -> list[type[Deployer]]:
        result: list[type[Deployer]] = []
        for mod in mod_list:
            for _name, obj in inspect.getmembers(mod, inspect.isclass):
                if issubclass(obj, Deployer) and obj is not Deployer:
                    result.append(obj)
        return result

    local_modules = _discover_local_modules()
    local_classes = _classes_from_modules(local_modules)

    # Determine which targets are covered by local deployers
    covered_targets: set[str] = set()
    for cls in local_classes:
        t = getattr(cls, "target", "")
        if t:
            covered_targets.add(t)

    # Built-in classes, minus those whose target is already covered locally
    builtin_classes = _classes_from_modules(_BUILTIN_MODULES)
    for cls in builtin_classes:
        t = getattr(cls, "target", "")
        if t not in covered_targets:
            local_classes.append(cls)

    return local_classes


def deployer_for_target(target: str, method: str = "") -> type[Deployer] | None:
    """Return the first deployer whose ``handles(target, method)`` returns True."""
    for cls in discover_deployers():
        if cls.handles(target, method):
            return cls
    return None
