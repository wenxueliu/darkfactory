from __future__ import annotations

from pathlib import Path
import os
import subprocess


def git_root(start: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    return Path(proc.stdout.strip()).resolve() if proc.returncode == 0 else None


def discover_maven_command(project: Path, platform: str | None = None) -> str:
    """Return the platform-native Maven wrapper, falling back to system Maven."""
    platform = platform or os.name
    candidates = ("mvnw.cmd",) if platform == "nt" else ("mvnw",)
    for name in candidates:
        wrapper = project / name
        if wrapper.is_file():
            return str(wrapper)
    return "mvn"


def discover(start: Path) -> dict:
    start = start.resolve()
    root = git_root(start)
    if not root:
        return {"error": "E101_NO_GIT_ROOT", "searched_from": str(start)}
    requirements = sorted(
        (path for path in root.rglob("*.md") if "requirement" in path.name.lower()),
        key=lambda path: (len(path.relative_to(root).parts), str(path)),
    )
    poms = sorted(root.rglob("pom.xml"), key=lambda path: (len(path.relative_to(root).parts), str(path)))
    if not requirements:
        return {"error": "E102_NO_REQUIREMENT", "root": str(root)}
    if not poms:
        return {"error": "E103_NO_MAVEN", "root": str(root)}
    projects = [pom.parent for pom in poms]
    containing_start = [project for project in projects if start.is_relative_to(project)]
    project = max(containing_start, key=lambda path: len(path.parts)) if containing_start else root
    local_requirements = [path for path in requirements if path.is_relative_to(project)]
    if local_requirements:
        requirement = min(local_requirements, key=lambda path: (len(path.relative_to(project).parts), str(path)))
    else:
        pairs = [(candidate, path) for candidate in projects for path in requirements if path.is_relative_to(candidate)]
        if pairs:
            project, requirement = min(
                pairs,
                key=lambda pair: (0 if start.is_relative_to(pair[0]) else 1,
                                  len(pair[1].relative_to(pair[0]).parts), str(pair[0])),
            )
        else:
            project, requirement = projects[0], requirements[0]
    pom = next((candidate for candidate in poms if candidate.parent == project), poms[0])
    return {
        "root": str(root), "project": str(project), "requirement": str(requirement),
        "pom": str(pom), "build": discover_maven_command(project),
        "candidates": {"requirements": len(requirements), "poms": len(poms)},
    }
