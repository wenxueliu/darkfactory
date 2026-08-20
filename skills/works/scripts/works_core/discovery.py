from __future__ import annotations

from pathlib import Path
import os
import subprocess
from collections.abc import Mapping


def git_root(start: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    return Path(proc.stdout.strip()).resolve() if proc.returncode == 0 else None


def discover_maven_command(project: Path, platform: str | None = None,
                           env: Mapping[str, str] | None = None) -> str:
    """Resolve Maven from M2_HOME, then the project wrapper, then PATH."""
    platform = platform or os.name
    env = os.environ if env is None else env
    maven_home = env.get("M2_HOME")
    if maven_home:
        executable = Path(maven_home) / "bin" / ("mvn.cmd" if platform == "nt" else "mvn")
        if executable.is_file():
            return str(executable)
    candidates = ("mvnw.cmd",) if platform == "nt" else ("mvnw",)
    for name in candidates:
        wrapper = project / name
        if wrapper.is_file():
            return str(wrapper)
    return "mvn"


def discover(start: Path) -> dict:
    start = start.resolve()
    discovered_git_root = git_root(start)
    root = discovered_git_root or start
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
    if containing_start:
        project = max(containing_start, key=lambda path: len(path.parts))
    else:
        pairs = [(candidate, path) for candidate in projects for path in requirements
                 if path.is_relative_to(candidate)]
        project = min(pairs, key=lambda pair: (
            len(pair[1].relative_to(pair[0]).parts), str(pair[0]),
        ))[0] if pairs else projects[0]
    local_requirements = [path for path in requirements if path.is_relative_to(project)]
    requirement = (min(local_requirements,
                       key=lambda path: (len(path.relative_to(project).parts), str(path)))
                   if local_requirements else requirements[0])
    pom = next(candidate for candidate in poms if candidate.parent == project)
    return {
        "root": str(root), "project": str(project), "requirement": str(requirement),
        "pom": str(pom), "build": discover_maven_command(project),
        "git_managed": discovered_git_root is not None,
        "candidates": {"requirements": len(requirements), "poms": len(poms)},
    }
