"""Canonical project paths shared by knowledge-management scripts.

The harness workspace has three deliberately separate roots:

* ``services/`` contains one or more independent source repositories.
* ``knowledge/`` contains durable, human-readable project knowledge.
* ``_context/memory/sw-shared/`` contains workflow state and generated metadata.

Keeping these paths in one module prevents individual scripts from inventing
different project roots or coupling knowledge to orchestration state.
"""

from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = SKILL_DIR.parent.parent
SERVICES_DIR = PROJECT_ROOT / "services"
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
SHARED_MEMORY_DIR = PROJECT_ROOT / "_context" / "memory" / "sw-shared"
REGISTRY_PATH = SHARED_MEMORY_DIR / "service-registry.yaml"


def project_path(*parts):
    """Return an absolute path under the harness project root."""
    return PROJECT_ROOT.joinpath(*parts)
