#!/usr/bin/env python3
"""Build, publish, download, install, and initialize Harness packages.

The package format is intentionally boring: a gzip-compressed tar archive with
one JSON manifest at its root.  That keeps downloads inspectable, works
offline, and avoids adding a runtime dependency to the installed project.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_NAME = "harness-multiagents"
PACKAGE_SCHEMA_VERSION = "1.0.0"
DEFAULT_VERSION = "1.0.0"
MANIFEST_NAME = "harness-package.json"
PACKAGE_DIRS = (
    "skills",
    "agents",
    "hooks",
    "docs",
    "scripts",
    "document_contracts",
    ".claude-plugin",
    ".codex-plugin",
    ".opencode",
)
PACKAGE_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "install.py",
    "install.sh",
    "package.py",
    "change.py",
)
EXCLUDED_PARTS = {
    ".git",
    ".claude",
    ".pytest_cache",
    ".omc",
    ".remember",
    "_context-output",
    "__pycache__",
    "reference",
}


class PackageError(RuntimeError):
    """Raised for invalid package input or an unsafe package operation."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_name(value: str) -> str:
    result = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-.")
    if not result:
        raise PackageError("version must contain at least one filename-safe character")
    return result


def _source_revision(source_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _is_excluded(path: Path, source_root: Path) -> bool:
    relative = path.relative_to(source_root)
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return True
    if path.name.endswith((".pyc", ".pyo")):
        return True
    if path.parts[-2:] == ("hooks", "tests") or "hooks/tests" in relative.as_posix():
        return True
    return False


def _iter_payload_files(source_root: Path) -> Iterable[tuple[Path, str]]:
    seen: set[str] = set()
    for directory in PACKAGE_DIRS:
        root = source_root / directory
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink() or _is_excluded(path, source_root):
                continue
            relative = path.relative_to(source_root).as_posix()
            if relative not in seen:
                seen.add(relative)
                yield path, relative
    for filename in PACKAGE_FILES:
        path = source_root / filename
        if path.is_file() and not path.is_symlink() and not _is_excluded(path, source_root):
            relative = path.relative_to(source_root).as_posix()
            if relative not in seen:
                seen.add(relative)
                yield path, relative


def _validate_relative_path(value: str) -> None:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise PackageError(f"unsafe package path: {value!r}")


def _validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    required = ("schema_version", "name", "version", "payload")
    missing = [key for key in required if key not in manifest]
    if missing:
        raise PackageError(f"package manifest is missing: {', '.join(missing)}")
    if manifest["schema_version"] != PACKAGE_SCHEMA_VERSION:
        raise PackageError(
            f"unsupported package schema {manifest['schema_version']!r}; "
            f"expected {PACKAGE_SCHEMA_VERSION!r}"
        )
    if not isinstance(manifest["payload"], list):
        raise PackageError("package manifest payload must be a list")
    seen: set[str] = set()
    for item in manifest["payload"]:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise PackageError("every payload item must contain a path")
        _validate_relative_path(item["path"])
        if item["path"] in seen:
            raise PackageError(f"duplicate payload path: {item['path']}")
        seen.add(item["path"])
        if not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))):
            raise PackageError(f"invalid sha256 for payload path: {item['path']}")
    return manifest


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    os.replace(temporary, path)


def build_package(source_root: Path, output_dir: Path, version: str = DEFAULT_VERSION) -> Path:
    """Build a validated Harness tarball and its sibling checksum file."""
    source_root = Path(source_root).resolve()
    if not (source_root / "skills").is_dir():
        raise PackageError(f"source root does not contain skills/: {source_root}")
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_version = _safe_name(version)
    archive_name = f"{PACKAGE_NAME}-{safe_version}.tar.gz"
    archive_path = output_dir / archive_name

    payload = []
    files = list(_iter_payload_files(source_root))
    if not files:
        raise PackageError("source root has no package payload")
    for path, relative in files:
        payload.append({"path": relative, "sha256": _sha256(path), "size": path.stat().st_size})

    manifest: dict[str, Any] = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "name": PACKAGE_NAME,
        "version": version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {"revision": _source_revision(source_root)},
        "payload": payload,
        "install": {
            "entrypoint": "install.py",
            "platforms": ["claude", "codex", "opencode"],
            "scopes": ["project", "user"],
        },
    }

    with tempfile.TemporaryDirectory(prefix="harness-package-") as staging_name:
        staging = Path(staging_name)
        for path, relative in files:
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
        (staging / MANIFEST_NAME).write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        with archive_path.open("wb") as raw:
            import gzip

            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as archive:
                    archive.add(staging / MANIFEST_NAME, arcname=MANIFEST_NAME, recursive=False)
                    for _, relative in files:
                        archive.add(staging / relative, arcname=relative, recursive=False)

    archive_hash = _sha256(archive_path)
    (archive_path.with_name(archive_path.name + ".sha256")).write_text(
        f"{archive_hash}  {archive_path.name}\n", encoding="utf-8"
    )
    return archive_path


def read_manifest(archive_path: Path) -> dict[str, Any]:
    """Read and validate the manifest from a package archive."""
    archive_path = Path(archive_path)
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            member = archive.getmember(MANIFEST_NAME)
            if not member.isfile():
                raise PackageError(f"{MANIFEST_NAME} is not a regular file")
            stream = archive.extractfile(member)
            if stream is None:
                raise PackageError(f"cannot read {MANIFEST_NAME}")
            manifest = json.load(stream)
    except (tarfile.TarError, OSError, json.JSONDecodeError, KeyError) as exc:
        raise PackageError(f"invalid package archive: {archive_path}") from exc
    return _validate_manifest(manifest)


def _validate_archive_members(archive: tarfile.TarFile) -> None:
    for member in archive.getmembers():
        _validate_relative_path(member.name)
        if member.issym() or member.islnk():
            raise PackageError(f"symbolic and hard links are not allowed: {member.name}")


def _extract_package(archive_path: Path, destination: Path) -> dict[str, Any]:
    manifest = read_manifest(archive_path)
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as archive:
        _validate_archive_members(archive)
        archive.extractall(destination)

    for item in manifest["payload"]:
        path = destination / item["path"]
        if not path.is_file() or _sha256(path) != item["sha256"]:
            raise PackageError(f"payload checksum mismatch: {item['path']}")
    return manifest


def _version_key(value: str) -> tuple[Any, ...]:
    parts = re.split(r"[.-]", value)
    return tuple(int(part) if part.isdigit() else part for part in parts)


def _read_index(repository: Path) -> dict[str, Any]:
    index_path = repository / "packages" / "index.json"
    if not index_path.exists():
        return {"schema_version": PACKAGE_SCHEMA_VERSION, "name": PACKAGE_NAME, "latest": None, "releases": {}}
    try:
        value = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"invalid repository index: {index_path}") from exc
    if not isinstance(value.get("releases"), dict):
        raise PackageError(f"repository index has no releases map: {index_path}")
    return value


def publish_local(package_path: Path, repository: Path) -> dict[str, Any]:
    """Publish an archive into a local package repository and update its index."""
    package_path = Path(package_path).resolve()
    if not package_path.is_file():
        raise PackageError(f"package archive does not exist: {package_path}")
    manifest = read_manifest(package_path)
    repository = Path(repository).resolve()
    package_dir = repository / "packages"
    package_dir.mkdir(parents=True, exist_ok=True)
    destination = package_dir / package_path.name
    shutil.copy2(package_path, destination)
    digest = _sha256(destination)
    (destination.with_name(destination.name + ".sha256")).write_text(
        f"{digest}  {destination.name}\n", encoding="utf-8"
    )

    index = _read_index(repository)
    releases = index.setdefault("releases", {})
    releases[manifest["version"]] = {
        "artifact": destination.name,
        "sha256": digest,
        "manifest": {"name": manifest["name"], "version": manifest["version"]},
    }
    versions = sorted(releases, key=_version_key)
    index.update(
        {
            "schema_version": PACKAGE_SCHEMA_VERSION,
            "name": manifest["name"],
            "latest": versions[-1] if versions else None,
        }
    )
    _write_json(package_dir / "index.json", index)
    return {
        "status": "READY",
        "repository": str(repository),
        "artifact": str(destination),
        "version": manifest["version"],
        "sha256": digest,
    }


def _run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        raise PackageError(f"command failed: {' '.join(command)}\n{detail}") from exc


def publish_remote(package_path: Path, repository: str, branch: str | None = None) -> dict[str, Any]:
    """Clone a remote Git repository, publish, commit, and push the package."""
    with tempfile.TemporaryDirectory(prefix="harness-publish-") as temporary:
        checkout = Path(temporary) / "repository"
        command = ["git", "clone"]
        if branch:
            command += ["--branch", branch]
        command += [repository, str(checkout)]
        _run(command)
        result = publish_local(package_path, checkout)
        _run(["git", "add", "packages"], cwd=checkout)
        status = _run(["git", "status", "--porcelain", "packages"], cwd=checkout)
        if status.stdout.strip():
            _run(["git", "commit", "-m", f"publish {PACKAGE_NAME} {result['version']}"], cwd=checkout)
            push = ["git", "push", "origin"]
            if branch:
                push.append(branch)
            _run(push, cwd=checkout)
        result["repository"] = repository
        result["published_remote"] = True
        return result


def _is_remote_repository(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return value.startswith("git@") or parsed.scheme in {"git", "ssh"} or value.endswith(".git")


def _copy_to_output(source: Path, output: Path) -> Path:
    output = Path(output).resolve()
    if output.suffixes[-2:] == [".tar", ".gz"]:
        output.parent.mkdir(parents=True, exist_ok=True)
        destination = output
    else:
        output.mkdir(parents=True, exist_ok=True)
        destination = output / source.name
    if source.resolve() == destination.resolve():
        read_manifest(destination)
        return destination
    shutil.copy2(source, destination)
    read_manifest(destination)
    return destination


def _resolve_index_artifact(repository: Path, version: str | None, output: Path) -> Path:
    index = _read_index(repository)
    selected = version or index.get("latest")
    if not selected or selected not in index.get("releases", {}):
        raise PackageError(f"package version not found in repository: {version or 'latest'}")
    release = index["releases"][selected]
    artifact_name = release.get("artifact")
    if not isinstance(artifact_name, str):
        raise PackageError("repository release has no artifact")
    _validate_relative_path(artifact_name)
    source = repository / "packages" / artifact_name
    if not source.is_file():
        raise PackageError(f"repository artifact does not exist: {source}")
    destination = _copy_to_output(source, output)
    expected = release.get("sha256")
    if expected and _sha256(destination) != expected:
        raise PackageError(f"repository checksum mismatch: {destination.name}")
    return destination


def _download_url(url: str, output: Path, expected_sha256: str | None = None) -> Path:
    output = Path(output).resolve()
    if output.suffixes[-2:] != [".tar", ".gz"]:
        output.mkdir(parents=True, exist_ok=True)
        filename = Path(urllib.parse.urlparse(url).path).name or "harness-package.tar.gz"
        output = output / filename
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url) as response, output.open("wb") as stream:
            shutil.copyfileobj(response, stream)
    except OSError as exc:
        raise PackageError(f"download failed: {url}") from exc
    if expected_sha256 and _sha256(output) != expected_sha256:
        raise PackageError(f"download checksum mismatch: {output.name}")
    read_manifest(output)
    return output


def download_package(source: str | Path, output: Path, version: str | None = None) -> Path:
    """Download a package from an archive, local repository, URL, or Git repo."""
    source_text = str(source)
    source_path = Path(source_text).expanduser()
    if source_path.exists():
        if source_path.is_file():
            return _copy_to_output(source_path.resolve(), output)
        return _resolve_index_artifact(source_path.resolve(), version, output)

    if _is_remote_repository(source_text):
        with tempfile.TemporaryDirectory(prefix="harness-download-") as temporary:
            checkout = Path(temporary) / "repository"
            _run(["git", "clone", source_text, str(checkout)])
            downloaded = _resolve_index_artifact(checkout, version, Path(temporary) / "download")
            return _copy_to_output(downloaded, output)

    parsed = urllib.parse.urlparse(source_text)
    if parsed.scheme not in {"http", "https"}:
        raise PackageError(f"package source does not exist or is not a supported URL: {source_text}")
    if parsed.path.endswith((".tar.gz", ".tgz")):
        return _download_url(source_text, output)

    index_url = source_text.rstrip("/") + "/packages/index.json"
    try:
        with urllib.request.urlopen(index_url) as response:
            index = json.load(response)
    except (OSError, json.JSONDecodeError) as exc:
        raise PackageError(f"cannot read remote package index: {index_url}") from exc
    selected = version or index.get("latest")
    release = index.get("releases", {}).get(selected)
    if not selected or not isinstance(release, dict):
        raise PackageError(f"package version not found in remote repository: {version or 'latest'}")
    artifact_url = urllib.parse.urljoin(index_url, release["artifact"])
    return _download_url(artifact_url, output, release.get("sha256"))


def _load_installer(source_root: Path) -> Any:
    installer_path = source_root / "install.py"
    if not installer_path.is_file():
        raise PackageError("package does not contain install.py")
    module_name = f"harness_installer_{abs(hash(source_root))}"
    spec = importlib.util.spec_from_file_location(module_name, installer_path)
    if spec is None or spec.loader is None:
        raise PackageError("cannot load package installer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _platforms(value: str | Iterable[str]) -> tuple[str, ...]:
    values = (value.split(",") if isinstance(value, str) else list(value))
    normalized = tuple(dict.fromkeys(item.strip().lower() for item in values if item.strip()))
    if "all" in normalized:
        normalized = ("claude", "codex", "opencode")
    invalid = set(normalized) - {"claude", "codex", "opencode"}
    if invalid or not normalized:
        raise PackageError(f"unsupported platform(s): {', '.join(sorted(invalid)) or value}")
    return normalized


def _copy_tree(source: Path, destination: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _install_opencode(source_root: Path, target: Path, dry_run: bool) -> None:
    source_opencode = source_root / ".opencode"
    if not source_opencode.is_dir():
        raise PackageError("package does not contain .opencode/")
    if dry_run:
        return
    _copy_tree(source_opencode / "plugins", target / ".opencode" / "plugins")
    _copy_tree(source_root / "skills", target / "skills")
    source_config = source_opencode / "opencode.json"
    target_config = target / ".opencode" / "opencode.json"
    if source_config.is_file() and not target_config.exists():
        _copy_tree(source_config, target_config)


def _record_installation(target: Path, manifest: dict[str, Any], platforms: tuple[str, ...], scope: str) -> None:
    record = target / ".harness" / "installation.json"
    value: dict[str, Any] = {}
    if record.exists():
        try:
            value = json.loads(record.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            value = {}
    value.update(
        {
            "package": manifest["name"],
            "version": manifest["version"],
            "scope": scope,
            "platforms": list(platforms),
            "installed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _write_json(record, value)


def _install_from_root(
    source_root: Path,
    target: Path | None,
    platforms: Iterable[str],
    scope: str = "project",
    minimal: bool = False,
    force: bool = False,
    dry_run: bool = False,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del force  # The package installer is already non-interactive at this layer.
    selected = _platforms(platforms)
    if scope not in {"project", "user"}:
        raise PackageError(f"unsupported install scope: {scope}")
    root = Path(target).resolve() if target else Path.home().resolve()
    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)

    installer = None
    native = set(selected) & {"claude", "codex"}
    if native:
        installer = _load_installer(source_root)
        args = argparse.Namespace(
            user=scope == "user" and target is None,
            target=None if scope == "user" and target is None else root,
            claude="claude" in native,
            codex="codex" in native,
            minimal=minimal,
            dry_run=dry_run,
            force=True,
        )
        roots = installer.get_platform_roots(args)
        skills = installer.get_skill_list(args)
        installer.install_skills(args, skills, roots, dry_run)
        installer.install_agent_templates(args, roots, dry_run)
        installer.install_hooks(args, roots, dry_run)
    if "opencode" in selected:
        _install_opencode(source_root, root, dry_run)

    result_manifest = manifest or {
        "name": PACKAGE_NAME,
        "version": DEFAULT_VERSION,
    }
    if not dry_run:
        _record_installation(root, result_manifest, selected, scope)
    return {
        "status": "READY",
        "target": str(root),
        "scope": scope,
        "platforms": list(selected),
        "version": result_manifest["version"],
    }


def install_package(
    source: str | Path,
    target: Path | None = None,
    platforms: Iterable[str] = ("all",),
    scope: str = "project",
    minimal: bool = False,
    force: bool = False,
    dry_run: bool = False,
    version: str | None = None,
) -> dict[str, Any]:
    """Download, verify, extract, and install a Harness package."""
    with tempfile.TemporaryDirectory(prefix="harness-install-") as temporary:
        artifact = download_package(source, Path(temporary) / "download", version)
        manifest = read_manifest(artifact)
        with tempfile.TemporaryDirectory(prefix="harness-extract-") as extracted_name:
            source_root = Path(extracted_name)
            _extract_package(artifact, source_root)
            result = _install_from_root(
                source_root,
                target,
                platforms,
                scope=scope,
                minimal=minimal,
                force=force,
                dry_run=dry_run,
                manifest=manifest,
            )
        result["package"] = manifest["name"]
        result["source"] = str(source)
        return result


def _write_if_missing(path: Path, content: str, created: list[str], target: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    created.append(path.relative_to(target).as_posix())


def initialize_workspace(
    target: Path,
    *,
    business_domain: str = "general",
    communication_language: str = "Chinese",
    user_name: str = "",
    worktree_base: str = ".worktree",
    min_iteration_before_human: int = 3,
    enabled_reviewers: str = "security,logic,performance",
    knowledge_base_auto_update: bool = True,
    merge_strategy: str = "merge",
) -> dict[str, Any]:
    """Create the shared Harness workspace without overwriting user files."""
    target = Path(target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    directories = (
        "services",
        "knowledge/patterns",
        "knowledge/decisions",
        "knowledge/lessons",
        "knowledge/contracts",
        "knowledge/domains",
        "knowledge/services",
        "knowledge/sw-controller",
        "knowledge/reviews",
        "_context",
    )
    for directory in directories:
        path = target / directory
        if not path.exists():
            path.mkdir(parents=True)
            created.append(directory)

    config = (
        "sw:\n"
        f'  business_domain: "{business_domain}"\n'
        f"  min_iteration_before_human: {int(min_iteration_before_human)}\n"
        f'  enabled_reviewers: "{enabled_reviewers}"\n'
        f"  knowledge_base_auto_update: {'true' if knowledge_base_auto_update else 'false'}\n"
        f'  merge_strategy: "{merge_strategy}"\n'
        f'  worktree_base: "{worktree_base}"\n'
    )
    user_config = f'communication_language: "{communication_language}"\nuser_name: "{user_name}"\n'
    _write_if_missing(target / "_context" / "config.yaml", config, created, target)
    _write_if_missing(target / "_context" / "config.user.yaml", user_config, created, target)
    _write_if_missing(
        target / "knowledge" / "index.md",
        "# Harness Knowledge Base\n\nThis directory stores shared project knowledge and workflow state.\n",
        created,
        target,
    )
    _write_if_missing(
        target / "knowledge" / "requirements-tracker.yaml",
        'version: "1.0.0"\nrequirements: {}\n',
        created,
        target,
    )
    _write_if_missing(
        target / "knowledge" / "sw-controller" / "global-state.yaml",
        'version: "1.0.0"\nstatus: initialized\n',
        created,
        target,
    )
    _write_if_missing(
        target / "knowledge" / "sw-controller" / "worktree-registry.yaml",
        'version: "1.0.0"\nworktrees: {}\n',
        created,
        target,
    )

    worktree = target / worktree_base
    if not worktree.exists():
        worktree.mkdir(parents=True)
        created.append(worktree.relative_to(target).as_posix())
    gitignore = target / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    additions = [".worktree/", "_context-output/"]
    missing = [line for line in additions if line not in existing.splitlines()]
    if missing:
        separator = "" if not existing or existing.endswith("\n") else "\n"
        gitignore.parent.mkdir(parents=True, exist_ok=True)
        gitignore.write_text(existing + separator + "\n".join(missing) + "\n", encoding="utf-8")
        if ".gitignore" not in created:
            created.append(".gitignore")
    return {"status": "READY", "target": str(target), "created": created, "ready": True}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="package.py", description="Harness package lifecycle CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build a verified .tar.gz package")
    build.add_argument("--source", type=Path, default=SCRIPT_DIR)
    build.add_argument("--output", type=Path, default=Path("dist"))
    build.add_argument("--version", default=DEFAULT_VERSION)

    publish = subparsers.add_parser("publish", help="publish to a local or remote Git repository")
    publish.add_argument("--package", required=True, type=Path)
    publish.add_argument("--repository", required=True)
    publish.add_argument("--branch")

    download = subparsers.add_parser("download", help="download from an archive or package repository")
    download.add_argument("--source", required=True)
    download.add_argument("--output", type=Path, default=Path("."))
    download.add_argument("--version")

    install = subparsers.add_parser("install", help="download and install into a project or user directory")
    install.add_argument("--source", required=True)
    install.add_argument("--target", type=Path)
    install.add_argument("--scope", choices=("project", "user"), default="project")
    install.add_argument("--platform", default="all", help="claude,codex,opencode, or all")
    install.add_argument("--version")
    install.add_argument("--minimal", action="store_true")
    install.add_argument("--force", action="store_true")
    install.add_argument("--dry-run", action="store_true")

    initialize = subparsers.add_parser("init", help="initialize a workspace after an Agent interview")
    initialize.add_argument("--target", type=Path, default=Path("."))
    initialize.add_argument("--package", dest="source")
    initialize.add_argument("--version", help="package version when --package points to a repository")
    initialize.add_argument("--no-install", action="store_true")
    initialize.add_argument("--platform", default="all")
    initialize.add_argument("--minimal", action="store_true")
    initialize.add_argument("--business-domain", default="general")
    initialize.add_argument("--language", default="Chinese")
    initialize.add_argument("--user-name", default="")
    initialize.add_argument("--worktree-base", default=".worktree")
    initialize.add_argument("--min-iteration-before-human", type=int, default=3)
    initialize.add_argument("--enabled-reviewers", default="security,logic,performance")
    initialize.add_argument("--merge-strategy", default="merge")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "build":
            artifact = build_package(args.source, args.output, args.version)
            print(artifact)
        elif args.command == "publish":
            if _is_remote_repository(args.repository):
                result = publish_remote(args.package, args.repository, args.branch)
            else:
                result = publish_local(args.package, Path(args.repository))
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "download":
            print(download_package(args.source, args.output, args.version))
        elif args.command == "install":
            result = install_package(
                args.source,
                args.target,
                _platforms(args.platform),
                scope=args.scope,
                minimal=args.minimal,
                force=args.force,
                dry_run=args.dry_run,
                version=args.version,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "init":
            result = initialize_workspace(
                args.target,
                business_domain=args.business_domain,
                communication_language=args.language,
                user_name=args.user_name,
                worktree_base=args.worktree_base,
                min_iteration_before_human=args.min_iteration_before_human,
                enabled_reviewers=args.enabled_reviewers,
                merge_strategy=args.merge_strategy,
            )
            if not args.no_install:
                source = args.source or str(SCRIPT_DIR)
                result["installation"] = (
                    install_package(
                        source,
                        args.target,
                        _platforms(args.platform),
                        minimal=args.minimal,
                        force=True,
                        version=args.version,
                    )
                    if args.source
                    else _install_from_root(
                        SCRIPT_DIR,
                        args.target,
                        _platforms(args.platform),
                        minimal=args.minimal,
                        force=True,
                        manifest={"name": PACKAGE_NAME, "version": DEFAULT_VERSION},
                    )
                )
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except PackageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
