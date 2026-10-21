from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("harness_package", ROOT / "package.py")
assert SPEC is not None and SPEC.loader is not None
package = importlib.util.module_from_spec(SPEC)
sys.modules["harness_package"] = package
SPEC.loader.exec_module(package)

INSTALL_SPEC = importlib.util.spec_from_file_location(
    "harness_install", ROOT / "install.py"
)
assert INSTALL_SPEC is not None and INSTALL_SPEC.loader is not None
install_module = importlib.util.module_from_spec(INSTALL_SPEC)
sys.modules["harness_install"] = install_module
INSTALL_SPEC.loader.exec_module(install_module)


def _venv_python(tmp_path: Path) -> Path:
    env_dir = tmp_path / "venv"
    try:
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(env_dir)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"venv with pip is unavailable: {exc}")
    python = env_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():  # pragma: no cover - environment dependent
        pytest.skip("venv did not create a python executable")
    return python


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
    assert "document_contracts/__init__.py" in names
    assert "document_contracts/__main__.py" in names
    assert "scripts/interactive-init.py" in names
    assert "skills/sw-setup/SKILL.md" in names
    assert "pyproject.toml" in names
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


def test_document_contracts_wheel_is_pure_python(tmp_path: Path) -> None:
    wheel = install_module.build_document_contracts_wheel(tmp_path / "dist", ROOT)

    assert wheel.name == "harness_document_contracts-1.0.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    assert "document_contracts/__init__.py" in names
    assert "document_contracts/__main__.py" in names
    assert "harness_document_contracts-1.0.0.dist-info/METADATA" in names
    assert "harness_document_contracts-1.0.0.dist-info/RECORD" in names
    assert not any("__pycache__" in name for name in names)


def test_install_downloaded_package_to_project(tmp_path: Path) -> None:
    artifact = package.build_package(ROOT, tmp_path / "dist", version="1.2.4")
    target = tmp_path / "project"
    target.mkdir()
    python = _venv_python(tmp_path)

    package.install_package(
        artifact,
        target,
        platforms=("codex",),
        force=True,
        python_executable=str(python),
    )

    assert (target / ".agents" / "skills" / "sw-setup" / "SKILL.md").is_file()
    assert (target / ".codex" / "hooks.json").is_file()
    # The machine layer is a pip package, never a folder in the workspace.
    assert not (target / "document_contracts").exists()
    assert not (target / ".codex" / "document_contracts").exists()

    result = subprocess.run(
        [str(python), "-m", "document_contracts", "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


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
    assert (target / "knowledge" / "requirements").is_dir()
    assert (target / "knowledge" / "value-assessment").is_dir()
    assert (target / "knowledge" / "index.md").is_file()
    config = (target / "_context" / "config.yaml").read_text()
    assert 'business_domain: "internal-tools"' in config
    assert 'enabled_reviewers: "logic"' in config
    assert not (target / "_context" / "workspace.yaml").exists()
    assert "sw.workspace.paths" not in config
