#!/usr/bin/env python3
"""Build deterministic local Maven repositories for MiniMax M2.7 evaluations."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess


POM = """<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion><groupId>eval</groupId><artifactId>{name}</artifactId><version>1</version>
  <properties><maven.compiler.release>8</maven.compiler.release><project.build.sourceEncoding>UTF-8</project.build.sourceEncoding></properties>
  <dependencies><dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId><version>5.10.2</version><scope>test</scope></dependency></dependencies>
  <build><plugins>
    <plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-compiler-plugin</artifactId><version>3.13.0</version></plugin>
    <plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-surefire-plugin</artifactId><version>3.2.5</version></plugin>
  </plugins></build>
</project>\n"""

SERVICE = """package eval;
public class UserService { public String name(long id) { return "user-" + id; } }
"""
CONTROLLER = """package eval;
public class UserController {
  private final UserService service;
  public UserController(UserService service) { this.service = service; }
  public String show(long id) { return service.name(id); }
}
"""
TEST = """package eval;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
class UserControllerTest {
  @Test void existingBehavior() { assertEquals("user-1", new UserController(new UserService()).show(1)); }
}
"""


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def make_repo(base: Path, name: str, requirement: str, dirty: bool = False, skipped: bool = False) -> Path:
    root = base / name
    root.mkdir(parents=True)
    pom = POM.format(name=name)
    if skipped:
        pom = pom.replace("</properties>", "<skipTests>true</skipTests><skipTest>true</skipTest></properties>")
    write(root / "pom.xml", pom)
    write(root / "requirement.md", requirement + "\n")
    write(root / "src/main/java/eval/UserService.java", SERVICE)
    write(root / "src/main/java/eval/UserController.java", CONTROLLER)
    write(root / "src/test/java/eval/UserControllerTest.java", TEST)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.name=works-eval", "-c", "user.email=works@example.invalid", "commit", "-qm", "fixture"],
        cwd=root, check=True,
    )
    if dirty:
        write(root / "user-owned.txt", "do not overwrite\n")
    return root


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    base = Path(args.output).resolve()
    base.mkdir(parents=True, exist_ok=True)
    make_repo(base, "service-boundary", "Add /users/{id}/label by reusing UserService. Never inject UserMapper into the controller.")
    make_repo(base, "dirty-worktree", "Change the displayed user label to uppercase.", dirty=True)
    make_repo(base, "invalid-red", "Return 'missing' for id zero. The first attempted test has a broken fixture and must not count as Red.")
    make_repo(base, "skip-tests", "Add a user label prefix with strict test-first evidence.", skipped=True)
    print(base)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
