from __future__ import annotations

import importlib.util
import json
import sys
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("harness_package", ROOT / "package.py")
assert SPEC is not None and SPEC.loader is not None
package = importlib.util.module_from_spec(SPEC)
sys.modules["harness_package"] = package
SPEC.loader.exec_module(package)


def test_build_package_contains_manifest_and_payload(tmp_path: Path) -> None:
    artifact = package.build_package(ROOT, tmp_path / "dist", version="9.9.9")

    manifest = package.read_manifest(artifact)
    assert manifest["name"] == "harness-multiagents"
    assert manifest["version"] == "9.9.9"
    assert any(item["path"] == "skills/sw-setup/SKILL.md" for item in manifest["payload"])

    with tarfile.open(artifact, "r:gz") as archive:
        names = set(archive.getnames())
    assert "harness-package.json" in names
    assert "package.py" in names
    assert "change.py" in names
    assert "skills/sw-setup/SKILL.md" in names
    assert ".claude/settings.local.json" not in names


def test_local_publish_and_download_use_repository_index(tmp_path: Path) -> None:
    artifact = package.build_package(ROOT, tmp_path / "dist", version="1.2.3")
    repository = tmp_path / "repository"

    result = package.publish_local(artifact, repository)
    assert result["version"] == "1.2.3"
    index = json.loads((repository / "packages" / "index.json").read_text())
    assert index["latest"] == "1.2.3"

    downloaded = package.download_package(repository, tmp_path / "downloads")
    assert downloaded.name == artifact.name
    assert downloaded.read_bytes() == artifact.read_bytes()


def test_install_downloaded_package_to_project(tmp_path: Path) -> None:
    artifact = package.build_package(ROOT, tmp_path / "dist", version="1.2.4")
    target = tmp_path / "project"
    target.mkdir()

    package.install_package(artifact, target, platforms=("codex",), force=True)

    assert (target / ".agents" / "skills" / "sw-setup" / "SKILL.md").is_file()
    assert (target / ".codex" / "hooks.json").is_file()


def test_initialize_workspace_is_idempotent_and_writes_agent_config(tmp_path: Path) -> None:
    target = tmp_path / "workspace"

    first = package.initialize_workspace(
        target,
        business_domain="internal-tools",
        communication_language="Chinese",
        user_name="Alice",
        enabled_reviewers="logic",
    )
    second = package.initialize_workspace(
        target,
        business_domain="internal-tools",
        communication_language="Chinese",
        user_name="Alice",
        enabled_reviewers="logic",
    )

    assert first["created"]
    assert second["created"] == []
    assert (target / "services").is_dir()
    assert (target / "knowledge" / "index.md").is_file()
    config = (target / "_context" / "config.yaml").read_text()
    assert 'business_domain: "internal-tools"' in config
    assert 'enabled_reviewers: "logic"' in config
