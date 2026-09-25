import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kb_paths import KNOWLEDGE_DIR, PROJECT_ROOT, REGISTRY_PATH, SERVICES_DIR, SHARED_MEMORY_DIR


def test_project_paths_use_workspace_boundaries():
    assert PROJECT_ROOT.name == "multiagents"
    assert SERVICES_DIR == PROJECT_ROOT / "services"
    assert KNOWLEDGE_DIR == PROJECT_ROOT / "knowledge"
    assert SHARED_MEMORY_DIR == PROJECT_ROOT / "_context" / "memory" / "sw-shared"
    assert REGISTRY_PATH == SHARED_MEMORY_DIR / "service-registry.yaml"


def test_paths_are_path_objects():
    for path in (PROJECT_ROOT, SERVICES_DIR, KNOWLEDGE_DIR, SHARED_MEMORY_DIR, REGISTRY_PATH):
        assert isinstance(path, Path)
