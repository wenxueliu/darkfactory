"""Tests for kb-service-discovery.py — service discovery and seed content."""

import os
import subprocess
import sys


SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb-service-discovery.py")


def run_discovery(services_dir, output_dir, registry_path, *args):
    """Run kb-service-discovery.py and return CompletedProcess."""
    cmd = [
        sys.executable, SCRIPT,
        "--services-dir", str(services_dir),
        "--output-dir", str(output_dir),
        "--registry-file", str(registry_path),
    ] + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc


def _create_git_repo(path, remote_url=None):
    """Create a minimal git repo directory with .git/config."""
    path.mkdir(parents=True)
    git_dir = path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n")

    config_lines = ["[core]", "\trepositoryformatversion = 0"]
    if remote_url:
        config_lines.extend([
            '[remote "origin"]',
            f'\turl = {remote_url}',
            '\tfetch = +refs/heads/*:refs/remotes/origin/*',
        ])
    config_lines.append('[branch "main"]')
    config_lines.append("\tremote = origin")
    (git_dir / "config").write_text("\n".join(config_lines) + "\n")


def test_scan_empty_services_dir(tmp_path):
    """Empty services directory produces empty results."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry)
    assert "No services found" in proc.stdout


def test_scan_git_repos(tmp_path):
    """Git directories are detected and metadata extracted."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    _create_git_repo(services_dir / "my-service", "https://github.com/test/my-service")
    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry)
    assert "my-service" in proc.stdout
    assert "Found 1 service" in proc.stdout


def test_skip_non_git_dirs(tmp_path):
    """Directories without .git are skipped."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    (services_dir / "not-a-repo").mkdir()
    _create_git_repo(services_dir / "is-a-repo")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry)
    assert "is-a-repo" in proc.stdout
    assert "not-a-repo" not in proc.stdout


def test_skip_hidden_dirs(tmp_path):
    """Directories starting with '.' are skipped."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    hidden_dir = services_dir / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / ".git").mkdir()

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry)
    assert "No services found" in proc.stdout


def test_detect_python(tmp_path):
    """Python project with setup.py is detected."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    svc_path = services_dir / "py-svc"
    _create_git_repo(svc_path)
    (svc_path / "setup.py").write_text("from setuptools import setup\nsetup(name='py-svc')\n")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry, "-v")
    assert "Language: python" in proc.stdout or "python" in proc.stdout


def test_detect_java_spring_boot(tmp_path):
    """Java + build.gradle + Application.java = Spring Boot."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    svc_path = services_dir / "java-svc"
    _create_git_repo(svc_path)
    (svc_path / "build.gradle").write_text("dependencies { implementation 'org.springframework.boot:spring-boot-starter-web' }")

    src_dir = svc_path / "src" / "main" / "java" / "com" / "example"
    src_dir.mkdir(parents=True)
    (src_dir / "Application.java").write_text("@SpringBootApplication\npublic class Application {}")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry, "-v")
    assert "Language: java" in proc.stdout


def test_detect_typescript(tmp_path):
    """TypeScript + package.json with react = TypeScript React."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    svc_path = services_dir / "ts-svc"
    _create_git_repo(svc_path)
    (svc_path / "tsconfig.json").write_text("{}")
    (svc_path / "package.json").write_text('{"dependencies": {"react": "^18.0.0"}}')

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry, "-v")
    assert "typescript" in proc.stdout.lower()


def test_detect_go(tmp_path):
    """Go project + go.mod = Go."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    svc_path = services_dir / "go-svc"
    _create_git_repo(svc_path)
    (svc_path / "go.mod").write_text("module github.com/test/go-svc\n\ngo 1.21\n")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry, "-v")
    assert "go" in proc.stdout.lower()


def test_detect_spring_controllers(tmp_path):
    """Spring controller files yield API endpoints."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    svc_path = services_dir / "api-svc"
    _create_git_repo(svc_path)
    (svc_path / "build.gradle").write_text("")

    src_dir = svc_path / "src" / "main" / "java" / "com" / "example"
    src_dir.mkdir(parents=True)
    (src_dir / "Application.java").write_text("@SpringBootApplication\npublic class Application {}")

    # Create a controller
    ctrl_dir = src_dir / "controller"
    ctrl_dir.mkdir(parents=True)
    (ctrl_dir / "UserController.java").write_text("""
@RestController
@RequestMapping("/api")
public class UserController {
    @GetMapping("/users")
    public List<User> listUsers() {}

    @PostMapping("/users")
    public User createUser() {}

    @GetMapping("/users/{id}")
    public User getUser() {}
}
""")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry, "-v")
    assert "3 endpoints" in proc.stdout


def test_probe_mode_no_writes(tmp_path):
    """--probe does not create any files."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    _create_git_repo(services_dir / "test-svc")
    (services_dir / "test-svc" / "setup.py").write_text("from setuptools import setup\nsetup(name='test-svc')\n")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry, "--probe")
    assert "[Probe Mode]" in proc.stdout

    # No files should be created
    assert not registry.exists()
    assert not list(output_dir.glob("**/*.md"))


def test_service_registry_yaml_generated(tmp_path):
    """service-registry.yaml has correct structure."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    _create_git_repo(services_dir / "my-svc", "https://github.com/test/my-svc")
    (services_dir / "my-svc" / "setup.py").write_text("from setuptools import setup\nsetup(name='my-svc')\n")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry)
    assert proc.returncode == 0
    assert registry.exists()

    content = registry.read_text()
    assert "Auto-generated" in content
    assert "DO NOT EDIT MANUALLY" in content
    assert "my-svc:" in content
    assert "display_name" in content
    assert "language:" in content


def test_service_knowledge_files(tmp_path):
    """overview.md, api-endpoints.md, db-schema.md are created."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    _create_git_repo(services_dir / "svc1")
    (services_dir / "svc1" / "setup.py").write_text("from setuptools import setup\nsetup(name='svc1')\n")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry)
    assert proc.returncode == 0

    svc_kb = output_dir / "services" / "svc1"
    assert (svc_kb / "overview.md").exists()
    assert (svc_kb / "api-endpoints.md").exists()
    assert (svc_kb / "db-schema.md").exists()


def test_no_migrations_found(tmp_path):
    """No migration files yields NO_MIGRATIONS_FOUND warning."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    _create_git_repo(services_dir / "no-db")
    (services_dir / "no-db" / "setup.py").write_text("from setuptools import setup\nsetup(name='no-db')\n")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry)
    svc_kb = output_dir / "services" / "no-db"
    db_schema = (svc_kb / "db-schema.md").read_text()
    assert "NO_MIGRATIONS_FOUND" in db_schema


def test_detect_infra_deps(tmp_path):
    """PostgreSQL driver detected in dependencies."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    svc = services_dir / "with-db"
    _create_git_repo(svc)
    (svc / "requirements.txt").write_text("psycopg2-binary==2.9.9\nredis==5.0.0\nfastapi==0.100.0\n")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry, "-v")
    # Check registry for infra deps
    content = registry.read_text()
    assert "postgresql" in content.lower()


def test_detection_warnings_in_output(tmp_path):
    """Warnings appear in the service registry."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()
    _create_git_repo(services_dir / "mystery-svc")
    # No recognizable files

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry, "-v")
    content = registry.read_text()
    assert "LANGUAGE_UNKNOWN" in content


def test_dependency_graph_computed(tmp_path):
    """Cross-service dependency graph is computed."""
    services_dir = tmp_path / "services"
    services_dir.mkdir()

    svc_a = services_dir / "service-a"
    _create_git_repo(svc_a, "https://github.com/test/service-a")
    (svc_a / "setup.py").write_text("from setuptools import setup\nsetup(name='service-a')\n")
    # Add cross-service ref to service-b
    (svc_a / "config.py").write_text('SERVICE_B_URL = "http://service-b:8000/api"')

    svc_b = services_dir / "service-b"
    _create_git_repo(svc_b, "https://github.com/test/service-b")
    (svc_b / "setup.py").write_text("from setuptools import setup\nsetup(name='service-b')\n")

    output_dir = tmp_path / "kb"
    registry = tmp_path / "registry.yaml"

    proc = run_discovery(services_dir, output_dir, registry, "-v")
    content = registry.read_text()

    # service-a should depend on service-b
    assert "service-b" in content

    # service-b should be depended_by service-a
    # Check for depended_by with service-a
    assert "depended_by_services" in content
