#!/usr/bin/env python3
"""Service discovery — scan services/ directory, detect tech stacks, generate knowledge.

Implements the 3-step process from hw-knowledge-agent/references/service-discovery.md:
  Step 1: Service inventory scan
  Step 2: Tech stack detection
  Step 3: API and data detection

Outputs:
  - service-registry.yaml (machine-readable metadata)
  - knowledge-base/services/{id}/overview.md
  - knowledge-base/services/{id}/api-endpoints.md
  - knowledge-base/services/{id}/db-schema.md

Usage:
    kb-service-discovery.py --probe --verbose
    kb-service-discovery.py --verbose
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
_HARNESS_ROOT = os.path.dirname(os.path.dirname(_PROJECT_ROOT))
_DEFAULT_SERVICES_DIR = os.path.join(_HARNESS_ROOT, "services")
_DEFAULT_KB_DIR = os.path.join(_PROJECT_ROOT, "_bmad", "memory", "hw-shared", "knowledge-base")
_DEFAULT_REGISTRY_PATH = os.path.join(_PROJECT_ROOT, "_bmad", "memory", "hw-shared", "service-registry.yaml")

SKIP_DIRS = {".", "..", ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
             ".pytest_cache", ".mypy_cache", ".tox", "dist", "build", ".next", ".turbo"}

DEFAULT_PORTS = {
    "java": 8080, "javascript": 3000, "typescript": 3000,
    "python": 8000, "go": 8080, "rust": 8080, "unknown": 0,
}


def discover_script_dirs():
    """Return (services_dir, kb_dir, registry_path) from script location."""
    return _DEFAULT_SERVICES_DIR, _DEFAULT_KB_DIR, _DEFAULT_REGISTRY_PATH


def step1_service_inventory(services_dir):
    """Scan services/ for git repos and extract metadata."""
    services = []
    if not os.path.isdir(services_dir):
        print(f"Warning: Services directory not found: {services_dir}", file=sys.stderr)
        return services

    for entry in sorted(os.listdir(services_dir)):
        service_path = os.path.join(services_dir, entry)
        if not os.path.isdir(service_path) or entry.startswith("."):
            continue

        git_dir = os.path.join(service_path, ".git")
        if not os.path.isdir(git_dir):
            continue

        info = {
            "service_id": entry,
            "display_name": entry.replace("_", " ").replace("-", " ").title(),
            "repo_remote": "",
            "base_branch": "main",
            "current_branch": "",
            "latest_commit": "",
            "has_uncommitted_changes": False,
            "warnings": [],
        }

        # Extract git remote URL
        git_config = os.path.join(git_dir, "config")
        if os.path.exists(git_config):
            try:
                with open(git_config, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                m = re.search(r'\[remote\s+"([^"]+)"\]\s*\n\s*url\s*=\s*(.+)', content)
                if m:
                    info["repo_remote"] = m.group(2).strip()
                # Detect base branch from init.defaultbranch or remote HEAD
                m2 = re.search(r'\[branch\s+"([^"]+)"\]', content)
                if m2:
                    info["current_branch"] = m2.group(1)
            except OSError:
                pass

        # Read HEAD to get current branch
        head_path = os.path.join(git_dir, "HEAD")
        if os.path.exists(head_path):
            try:
                with open(head_path, encoding="utf-8") as f:
                    ref = f.read().strip()
                    if ref.startswith("ref: refs/heads/"):
                        info["current_branch"] = ref.replace("ref: refs/heads/", "")
            except OSError:
                pass

        # Check for uncommitted changes (simplified: check if index exists)
        index_path = os.path.join(git_dir, "index")
        if os.path.exists(index_path):
            info["has_uncommitted_changes"] = False  # Cannot determine without git command

        services.append(info)

    return services


def _list_files(service_path):
    """List all non-ignored files in a service directory as a set of relative paths."""
    files = set()
    for root, dirs, fnames in os.walk(service_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in fnames:
            if not f.startswith("."):
                files.add(os.path.relpath(os.path.join(root, f), service_path))
    return files


def step2_tech_stack_detection(service_path, info):
    """Detect language, framework, build tool from project files."""
    files = _list_files(service_path)
    info["language"] = "unknown"
    info["framework"] = "unknown"
    info["build_tool"] = ""
    info["language_version"] = ""
    info["build_command"] = ""
    info["test_command"] = ""
    info["start_command"] = ""
    info["port"] = 0

    # Java / Gradle
    if "build.gradle" in files or "build.gradle.kts" in files:
        info["language"] = "java"
        info["build_tool"] = "gradle"
        info["build_command"] = "./gradlew build -x test"
        info["test_command"] = "./gradlew test"
        has_spring = any("Application.java" in f for f in files)
        if has_spring:
            info["framework"] = "spring-boot"
            info["start_command"] = "./gradlew bootRun"
        else:
            info["start_command"] = "java -jar build/libs/*.jar"
        info["port"] = 8080
        return info

    # Java / Maven
    if "pom.xml" in files:
        info["language"] = "java"
        info["build_tool"] = "maven"
        info["build_command"] = "mvn install -DskipTests"
        info["test_command"] = "mvn test"
        has_spring = any("Application.java" in f for f in files)
        if has_spring:
            info["framework"] = "spring-boot"
            info["start_command"] = "mvn spring-boot:run"
        else:
            info["start_command"] = "java -jar target/*.jar"
        info["port"] = 8080
        return info

    # TypeScript / JavaScript
    if "package.json" in files:
        pkg_path = os.path.join(service_path, "package.json")
        try:
            with open(pkg_path, encoding="utf-8") as f:
                pkg = json.load(f)
        except (OSError, json.JSONDecodeError):
            pkg = {}

        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        if "tsconfig.json" in files:
            info["language"] = "typescript"
        elif any(f.endswith(".ts") or f.endswith(".tsx") for f in list(files)[:200]):
            info["language"] = "typescript"
        else:
            info["language"] = "javascript"

        info["build_tool"] = "npm"
        info["build_command"] = "npm run build" if "build" in pkg.get("scripts", {}) else "npm install"
        info["test_command"] = "npm test" if "test" in pkg.get("scripts", {}) else ""

        if "next" in deps:
            info["framework"] = "next.js"
            info["start_command"] = "npm run dev"
            info["port"] = 3000
        elif "react" in deps:
            info["framework"] = "react"
            info["start_command"] = "npm run dev" if "dev" in pkg.get("scripts", {}) else "npm start"
            info["port"] = 3000
        elif "express" in deps:
            info["framework"] = "express"
            info["start_command"] = "node server.js" if "server.js" in files else "npm start"
            info["port"] = 3000

        if "vite" in deps:
            info["build_tool"] = "vite"
        return info

    # Python
    if "setup.py" in files or "setup.cfg" in files or "pyproject.toml" in files:
        info["language"] = "python"
        info["build_tool"] = "pip"
        info["build_command"] = "pip install -e ."
        info["test_command"] = "pytest"

        if "setup.py" in files:
            try:
                with open(os.path.join(service_path, "setup.py"), encoding="utf-8") as f:
                    content = f.read()
                m = re.search(r'name\s*=\s*["\'](.+?)["\']', content)
                if m:
                    info["display_name"] = m.group(1)
            except OSError:
                pass

        # FastAPI / Flask / Django detection
        for f in files:
            if f.endswith(".py") and "Application" not in f:
                try:
                    with open(os.path.join(service_path, f), encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    if "fastapi" in content.lower() or "FastAPI" in content:
                        info["framework"] = "fastapi"
                        info["start_command"] = "uvicorn main:app --reload"
                        info["port"] = 8000
                        break
                except OSError:
                    pass

        if info["framework"] == "unknown":
            info["framework"] = "python-stdlib"
            info["start_command"] = "python -m <module>"
            info["port"] = 8000

        return info

    # Python (simple: just requirements.txt or Python files)
    if "requirements.txt" in files or any(f.endswith(".py") for f in list(files)[:100]):
        info["language"] = "python"
        info["framework"] = "python-stdlib"
        info["build_tool"] = "pip"
        info["build_command"] = "pip install -r requirements.txt" if "requirements.txt" in files else ""
        info["test_command"] = "pytest"
        info["start_command"] = "python -m <module>"
        info["port"] = 8000

        for f in files:
            if f.endswith(".py"):
                try:
                    with open(os.path.join(service_path, f), encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    if "fastapi" in content.lower() or "FastAPI" in content:
                        info["framework"] = "fastapi"
                        info["start_command"] = "uvicorn main:app --reload"
                        break
                except OSError:
                    pass
        return info

    # Go
    if "go.mod" in files:
        info["language"] = "go"
        info["build_tool"] = "go"
        info["build_command"] = "go build ./..."
        info["test_command"] = "go test ./..."
        info["start_command"] = "go run ."

        # Try to detect framework
        for f in files:
            if f.endswith(".go"):
                try:
                    with open(os.path.join(service_path, f), encoding="utf-8", errors="ignore") as fh:
                        content = fh.read()
                    if '"github.com/gin-gonic/gin"' in content:
                        info["framework"] = "gin"
                        break
                except OSError:
                    pass

        info["port"] = 8080
        return info

    # Rust
    if "Cargo.toml" in files:
        info["language"] = "rust"
        info["build_tool"] = "cargo"
        info["build_command"] = "cargo build"
        info["test_command"] = "cargo test"
        info["start_command"] = "cargo run"
        info["port"] = 8080

        # Try to detect framework
        try:
            with open(os.path.join(service_path, "Cargo.toml"), encoding="utf-8") as f:
                content = f.read()
            if "actix-web" in content:
                info["framework"] = "actix-web"
            elif "axum" in content:
                info["framework"] = "axum"
            elif "rocket" in content:
                info["framework"] = "rocket"
        except OSError:
            pass
        return info

    info["warnings"].append("LANGUAGE_UNKNOWN")
    return info


def step3_api_data_detection(service_path, info):
    """Detect API endpoints, database schemas, infrastructure deps, port."""
    info["apis"] = []
    info["owns_data"] = []
    info["depends_on_infra"] = []
    info["depends_on_services"] = []
    info["depended_by_services"] = []

    language = info["language"]

    # --- Port detection ---
    port = _detect_port(service_path, info)
    info["port"] = port

    # --- API endpoint detection ---
    if language in ("java",) and info.get("framework") == "spring-boot":
        info["apis"] = _detect_spring_endpoints(service_path)
    elif language in ("javascript", "typescript"):
        info["apis"] = _detect_js_endpoints(service_path)
    elif language == "python" and info.get("framework") == "fastapi":
        info["apis"] = _detect_fastapi_endpoints(service_path)
    elif language == "python":
        info["apis"] = _detect_python_endpoints(service_path)
    elif language == "go" and info.get("framework") == "gin":
        info["apis"] = _detect_gin_endpoints(service_path)

    if not info["apis"]:
        info["warnings"].append("NO_ENDPOINTS_FOUND")

    # --- Database schema detection ---
    info["owns_data"] = _detect_db_schemas(service_path, language)

    # --- Infrastructure deps ---
    info["depends_on_infra"] = _detect_infra_deps(service_path, language)

    # --- Cross-service dependency detection ---
    info["depends_on_services"] = _detect_cross_service_deps(service_path)

    return info


def _detect_port(service_path, info):
    """Detect service port from configuration files."""
    language = info["language"]

    # Spring Boot application.yml/properties
    yml_paths = [
        os.path.join(service_path, "src/main/resources/application.yml"),
        os.path.join(service_path, "src/main/resources/application.yaml"),
    ]
    for yml_path in yml_paths:
        if os.path.exists(yml_path):
            try:
                with open(yml_path, encoding="utf-8") as f:
                    content = f.read()
                m = re.search(r'(?:server:\s*\n\s+port:\s*|port:\s*)(\d+)', content)
                if m:
                    return int(m.group(1))
            except OSError:
                pass

    props_path = os.path.join(service_path, "src/main/resources/application.properties")
    if os.path.exists(props_path):
        try:
            with open(props_path, encoding="utf-8") as f:
                content = f.read()
            m = re.search(r'server\.port\s*=\s*(\d+)', content)
            if m:
                return int(m.group(1))
        except OSError:
            pass

    # Node.js: package.json or .env
    pkg_path = os.path.join(service_path, "package.json")
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, encoding="utf-8") as f:
                pkg = json.load(f)
            if "config" in pkg and "port" in pkg["config"]:
                return int(pkg["config"]["port"])
        except (OSError, json.JSONDecodeError, ValueError):
            pass

    env_path = os.path.join(service_path, ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, encoding="utf-8") as f:
                for line in f:
                    m = re.match(r'^PORT\s*=\s*(\d+)', line.strip())
                    if m:
                        return int(m.group(1))
        except OSError:
            pass

    # Dockerfile EXPOSE
    dockerfile = os.path.join(service_path, "Dockerfile")
    if os.path.exists(dockerfile):
        try:
            with open(dockerfile, encoding="utf-8") as f:
                for line in f:
                    m = re.match(r'^EXPOSE\s+(\d+)', line.strip())
                    if m:
                        return int(m.group(1))
        except OSError:
            pass

    # Default fallback
    return DEFAULT_PORTS.get(language, 0)


def _detect_spring_endpoints(service_path):
    """Detect Spring Boot REST endpoints."""
    apis = []
    for root, dirs, files in os.walk(service_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if not (f.endswith("Controller.java") or f.endswith("Resource.java")):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue

            # RequestMapping prefix on class
            prefix_m = re.search(r'@RequestMapping\(["\']([^"\']*)["\']', content)
            prefix = prefix_m.group(1) if prefix_m else ""

            for pat, method in [
                (r'@GetMapping\(["\']([^"\']*)["\']', "GET"),
                (r'@PostMapping\(["\']([^"\']*)["\']', "POST"),
                (r'@PutMapping\(["\']([^"\']*)["\']', "PUT"),
                (r'@DeleteMapping\(["\']([^"\']*)["\']', "DELETE"),
                (r'@PatchMapping\(["\']([^"\']*)["\']', "PATCH"),
            ]:
                for m in re.finditer(pat, content):
                    apis.append({
                        "method": method,
                        "path": prefix + m.group(1),
                        "source": os.path.basename(filepath),
                    })
    return apis


def _detect_js_endpoints(service_path):
    """Detect Express/Next.js endpoints."""
    apis = []
    for root, dirs, files in os.walk(service_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if not f.endswith((".js", ".ts", ".mjs")):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue

            # Express: app.get/post/put/delete('/path', ...), router.get/post/...
            for m in re.finditer(r'(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']*)["\']', content):
                method = m.group(1).upper()
                path = m.group(2)
                if path:
                    apis.append({
                        "method": method,
                        "path": path,
                        "source": os.path.basename(filepath),
                    })
    return apis


def _detect_fastapi_endpoints(service_path):
    """Detect FastAPI endpoints."""
    apis = []
    for root, dirs, files in os.walk(service_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if not f.endswith(".py"):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue

            for pat, method in [
                (r'@app\.get\(["\']([^"\']*)["\']', "GET"),
                (r'@app\.post\(["\']([^"\']*)["\']', "POST"),
                (r'@app\.put\(["\']([^"\']*)["\']', "PUT"),
                (r'@app\.delete\(["\']([^"\']*)["\']', "DELETE"),
                (r'@app\.patch\(["\']([^"\']*)["\']', "PATCH"),
                (r'@router\.get\(["\']([^"\']*)["\']', "GET"),
                (r'@router\.post\(["\']([^"\']*)["\']', "POST"),
                (r'@router\.put\(["\']([^"\']*)["\']', "PUT"),
            ]:
                for m in re.finditer(pat, content):
                    apis.append({
                        "method": method,
                        "path": m.group(1),
                        "source": os.path.basename(filepath),
                    })
    return apis


def _detect_python_endpoints(service_path):
    """Detect stdlib HTTP server endpoints."""
    apis = []
    for root, dirs, files in os.walk(service_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if not f.endswith(".py"):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue

            # Match "/api/..." paths in Python source
            for m in re.finditer(r'(?:path|route)\s*==?\s*["\']([^"\']+)["\']', content):
                path = m.group(1)
                if path.startswith("/api/") or path.startswith("/"):
                    apis.append({
                        "method": "GET",
                        "path": path,
                        "source": os.path.basename(filepath),
                    })

            # HTTP method handler patterns: self._list_workflows, self._get_workflow, etc.
            for m in re.finditer(r'path\s*\.(?:startswith|__eq__)\("([^"]+)"\)', content):
                path = m.group(1)
                if path.startswith("/"):
                    apis.append({
                        "method": "GET",
                        "path": path,
                        "source": os.path.basename(filepath),
                    })

    # Deduplicate by (method, path)
    seen = set()
    unique = []
    for api in apis:
        key = (api["method"], api["path"])
        if key not in seen:
            seen.add(key)
            unique.append(api)
    return unique


def _detect_gin_endpoints(service_path):
    """Detect Gin framework endpoints in Go."""
    apis = []
    for root, dirs, files in os.walk(service_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if not f.endswith(".go"):
                continue
            filepath = os.path.join(root, f)
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue

            for m in re.finditer(r'\.(GET|POST|PUT|DELETE|PATCH)\(["\']([^"\']*)["\']', content):
                apis.append({
                    "method": m.group(1),
                    "path": m.group(2),
                    "source": os.path.basename(filepath),
                })
    return apis


def _detect_db_schemas(service_path, language):
    """Detect database migration files and extract table schemas."""
    schemas = []

    # Flyway
    for root, dirs, files in os.walk(service_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            if re.match(r'^V\d+__.*\.sql$', fname) or re.match(r'^V\d+\.\d+__.*\.sql$', fname):
                schemas.append({
                    "type": "flyway",
                    "file": os.path.relpath(os.path.join(root, fname), service_path),
                })

    # Prisma
    prisma_paths = [
        os.path.join(service_path, "prisma", "schema.prisma"),
        os.path.join(service_path, "prisma", "schema"),
    ]
    for pp in prisma_paths:
        if os.path.isfile(pp):
            schemas.append({"type": "prisma", "file": os.path.relpath(pp, service_path)})

    # SQLAlchemy / Django models
    for root, dirs, files in os.walk(service_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if "models.py" in files:
            schemas.append({
                "type": "sqlalchemy-or-django",
                "file": os.path.relpath(os.path.join(root, "models.py"), service_path),
            })
            break

    if not schemas:
        return [{"type": "NO_MIGRATIONS_FOUND", "file": ""}]

    return schemas


def _detect_infra_deps(service_path, language):
    """Detect infrastructure dependencies from project files."""
    deps = []

    # Read dependency files
    dep_content = ""
    for dep_file in ["build.gradle", "build.gradle.kts", "pom.xml", "requirements.txt",
                     "setup.py", "pyproject.toml", "go.mod", "Cargo.toml"]:
        df_path = os.path.join(service_path, dep_file)
        if os.path.exists(df_path):
            try:
                with open(df_path, encoding="utf-8", errors="ignore") as f:
                    dep_content += f.read() + "\n"
            except OSError:
                pass

    if "package.json" in os.listdir(service_path):
        try:
            with open(os.path.join(service_path, "package.json"), encoding="utf-8") as f:
                dep_content += json.dumps(json.load(f)) + "\n"
        except (OSError, json.JSONDecodeError):
            pass

    dl = dep_content.lower()

    infra_patterns = [
        (r'postgresql|psycopg|pg[^a-zA-Z]|\.postgres', "PostgreSQL"),
        (r'mysql|mariadb', "MySQL"),
        (r'redis|jedis|lettuce|ioredis', "Redis"),
        (r'kafka|spring-kafka|kafkajs|confluent', "Kafka"),
        (r'mongodb|mongo-client|mongoose|pymongo', "MongoDB"),
        (r's3|aws-sdk|boto3|aws-java-sdk-s3|minio', "S3/MinIO"),
        (r'elasticsearch|opensearch|elastic', "Elasticsearch"),
        (r'rabbitmq|amqp|amqplib', "RabbitMQ"),
    ]

    for pattern, name in infra_patterns:
        if re.search(pattern, dl):
            deps.append({"type": name.lower(), "name": name})

    return deps


def _detect_cross_service_deps(service_path):
    """Detect cross-service dependencies by searching for URL references."""
    deps = []
    found_services = set()

    for root, dirs, files in os.walk(service_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            if not fname.endswith((".py", ".js", ".ts", ".java", ".go", ".rs",
                                    ".yml", ".yaml", ".properties", ".env", ".json")):
                continue
            filepath = os.path.join(root, fname)
            try:
                with open(filepath, encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue

            # Look for service URL patterns
            url_patterns = [
                r'(?:SERVICE[_\w]*URL|service_url|service\.url|baseUrl|base_url|endpoint)\s*[:=]\s*["\']?([^"\'\\s\n]+)',
                r'["\']?(https?://[a-zA-Z][a-zA-Z0-9-]*)(?:[-.]service)?(?::\d+)?(?:/[^"\'\\s\n]*)?["\']?',
            ]
            for pat in url_patterns:
                for m in re.finditer(pat, content):
                    url = m.group(1)
                    # Extract potential service name from URL
                    svc_m = re.search(r'(?:https?://)?([a-zA-Z][a-zA-Z0-9-]*?)(?:[-.]service|\.[a-z]+)?(?::\d+)?(?:/|$)', url)
                    if svc_m:
                        candidate = svc_m.group(1)
                        if candidate not in found_services and candidate not in ("localhost", "127", "0", "api", "www", "http", "https"):
                            found_services.add(candidate)

    return sorted(found_services)


def _yaml_value(v, indent=0):
    """Serialize a value to YAML string (stdlib only, subset of YAML)."""
    prefix = "  " * indent

    if v is None:
        return "null"
    elif isinstance(v, bool):
        return "true" if v else "false"
    elif isinstance(v, int):
        return str(v)
    elif isinstance(v, float):
        return str(v)
    elif isinstance(v, str):
        if any(c in v for c in ['"', "'", ":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", "-", "<", ">", "=", "!", "%", "@", "`"]):
            return f'"{v}"'
        return v if v else '""'
    elif isinstance(v, list):
        if not v:
            return "[]"
        lines = []
        for item in v:
            if isinstance(item, dict):
                lines.append(f"{prefix}-")
                lines.append(_yaml_value(item, indent + 1))
            else:
                lines.append(f"{prefix}- {_yaml_value(item, indent)}")
        return "\n".join(lines)
    elif isinstance(v, dict):
        if not v:
            return "{}"
        lines = []
        for k, val in v.items():
            if isinstance(val, (dict, list)):
                lines.append(f"{prefix}{k}:")
                lines.append(_yaml_value(val, indent + 1))
            else:
                lines.append(f"{prefix}{k}: {_yaml_value(val, indent)}")
        return "\n".join(lines)
    else:
        return str(v)


def _to_yaml(data):
    """Top-level entry point for YAML serialization."""
    return _yaml_value(data, 0)


def generate_registry_yaml(services, output_path):
    """Generate service-registry.yaml from discovered services."""
    timestamp = datetime.now(timezone.utc).isoformat()

    registry = {
        "auto_generated": True,
        "generated_at": timestamp,
        "generated_by": "kb-service-discovery.py",
        "services": {},
    }

    for svc in services:
        svc_id = svc["service_id"]
        registry["services"][svc_id] = {
            "display_name": svc.get("display_name", svc_id),
            "repo_remote": svc.get("repo_remote", ""),
            "current_branch": svc.get("current_branch", ""),
            "language": svc.get("language", "unknown"),
            "framework": svc.get("framework", "unknown"),
            "build_tool": svc.get("build_tool", ""),
            "build_command": svc.get("build_command", ""),
            "test_command": svc.get("test_command", ""),
            "start_command": svc.get("start_command", ""),
            "port": svc.get("port", 0),
            "apis": svc.get("apis", []),
            "owns_data": svc.get("owns_data", []),
            "depends_on_infra": svc.get("depends_on_infra", []),
            "depends_on_services": svc.get("depends_on_services", []),
            "depended_by_services": svc.get("depended_by_services", []),
            "knowledge_path": f"services/{svc_id}/overview.md",
            "warnings": svc.get("warnings", []),
        }

    # Compute dependency graph
    all_ids = {s["service_id"] for s in services}
    for svc_id, svc_data in registry["services"].items():
        dependents = []
        for other_id, other_data in registry["services"].items():
            if other_id != svc_id and svc_id in other_data.get("depends_on_services", []):
                dependents.append(other_id)
        svc_data["depended_by_services"] = dependents

    # Build YAML manually
    lines = [
        "# Auto-generated by hw-knowledge-agent service-discovery",
        "# DO NOT EDIT MANUALLY",
        "",
        f"# Generated: {timestamp}",
        "",
    ]

    for svc_id in sorted(registry["services"].keys()):
        svc = registry["services"][svc_id]
        lines.append(f"{svc_id}:")
        lines.append(f"  display_name: {_yaml_value(svc['display_name'], 0)}")
        lines.append(f"  repo_remote: {_yaml_value(svc['repo_remote'], 0)}")
        lines.append(f"  current_branch: {_yaml_value(svc['current_branch'], 0)}")
        lines.append(f"  language: {svc['language']}")
        lines.append(f"  framework: {svc['framework']}")
        lines.append(f"  build_tool: {_yaml_value(svc['build_tool'], 0)}")
        lines.append(f"  build_command: {_yaml_value(svc['build_command'], 0)}")
        lines.append(f"  test_command: {_yaml_value(svc['test_command'], 0)}")
        lines.append(f"  start_command: {_yaml_value(svc['start_command'], 0)}")
        lines.append(f"  port: {svc['port']}")
        lines.append(f"  knowledge_path: {svc['knowledge_path']}")

        if svc["apis"]:
            lines.append("  apis:")
            for api in svc["apis"]:
                lines.append(f"    - method: {api['method']}")
                lines.append(f"      path: {_yaml_value(api['path'], 0)}")
                lines.append(f"      source: {_yaml_value(api['source'], 0)}")

        if svc["owns_data"]:
            lines.append("  owns_data:")
            for data in svc["owns_data"]:
                lines.append(f"    - type: {data['type']}")
                lines.append(f"      file: {_yaml_value(data.get('file', ''), 0)}")

        if svc["depends_on_infra"]:
            lines.append("  depends_on_infra:")
            for infra in svc["depends_on_infra"]:
                lines.append(f"    - {infra['type']}")

        if svc["depends_on_services"]:
            lines.append("  depends_on_services:")
            for dep in svc["depends_on_services"]:
                lines.append(f"    - {dep}")

        lines.append("  depended_by_services:")
        if svc["depended_by_services"]:
            for dep in svc["depended_by_services"]:
                lines.append(f"    - {dep}")
        else:
            lines.append("    []")

        if svc["warnings"]:
            lines.append("  warnings:")
            for w in svc["warnings"]:
                lines.append(f"    - {w}")

        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def generate_overview_md(service_info, output_dir):
    """Generate overview.md for a service."""
    svc_id = service_info["service_id"]
    os.makedirs(output_dir, exist_ok=True)

    api_count = len(service_info.get("apis", []))
    data_count = len(service_info.get("owns_data", []))
    infra_count = len(service_info.get("depends_on_infra", []))
    svc_deps = service_info.get("depends_on_services", [])

    lines = [
        f"# {service_info.get('display_name', svc_id)} — 服务概览",
        "",
        "<!-- Auto-generated by hw-knowledge-agent service-discovery -->",
        "<!-- DO NOT EDIT MANUALLY -->",
        "",
        f"**Service ID:** `{svc_id}`",
        f"**Language:** {service_info.get('language', 'unknown')}",
        f"**Framework:** {service_info.get('framework', 'unknown')}",
    ]

    if service_info.get("repo_remote"):
        lines.append(f"**Repository:** {service_info['repo_remote']}")
    if service_info.get("current_branch"):
        lines.append(f"**Branch:** {service_info['current_branch']}")
    if service_info.get("port"):
        lines.append(f"**Port:** {service_info.get('port')}")

    lines.extend([
        "",
        "## 职责",
        "",
    ])

    # Try to detect from README
    readme_path = os.path.join(_DEFAULT_SERVICES_DIR, svc_id, "README.md")
    has_readme = False
    if os.path.exists(readme_path):
        try:
            with open(readme_path, encoding="utf-8") as f:
                readme = f.read()
            # Extract first paragraph after the title
            lines_found = readme.split("\n")
            desc_lines = []
            in_desc = False
            for l in lines_found:
                if l.startswith("# ") or l.startswith("## "):
                    if in_desc:
                        break
                    if l.startswith("# "):
                        in_desc = True
                    continue
                if in_desc and l.strip():
                    desc_lines.append(l.strip())
                    if len(" ".join(desc_lines)) > 200:
                        break
            if desc_lines:
                lines.append(" ".join(desc_lines))
                has_readme = True
        except OSError:
            pass

    if not has_readme:
        lines.append("_NEEDS_MANUAL — 从 README 未检测到服务描述_")

    # API Endpoints
    lines.extend([
        "",
        "## API Endpoints",
        "",
    ])
    if service_info.get("apis"):
        lines.append("| Method | Path | Source |")
        lines.append("|--------|------|--------|")
        for api in service_info["apis"]:
            lines.append(f"| {api['method']} | `{api['path']}` | {api['source']} |")
    else:
        lines.append("_No API endpoints detected._")

    # Database
    lines.extend([
        "",
        "## Database",
        "",
    ])
    if service_info.get("owns_data"):
        for data in service_info["owns_data"]:
            if data["type"] == "NO_MIGRATIONS_FOUND":
                lines.append("_NO_MIGRATIONS_FOUND — 未检测到数据库迁移文件_")
            else:
                lines.append(f"- **{data['type']}**: `{data.get('file', 'N/A')}`")
    else:
        lines.append("_No database schemas detected._")

    # Infrastructure Dependencies
    lines.extend([
        "",
        "## Infrastructure Dependencies",
        "",
    ])
    if infra_count > 0:
        for infra in service_info["depends_on_infra"]:
            lines.append(f"- {infra['name']}")
    else:
        lines.append("_No infrastructure dependencies detected._")

    # Service Dependencies
    lines.extend([
        "",
        "## Service Dependencies",
        "",
    ])
    if svc_deps:
        lines.append("**Depends on:**")
        for dep in svc_deps:
            lines.append(f"- `{dep}`")
    else:
        lines.append("**Depends on:** _None detected_")

    depended = service_info.get("depended_by_services", [])
    if depended:
        lines.append("")
        lines.append("**Depended by:**")
        for dep in depended:
            lines.append(f"- `{dep}`")
    else:
        lines.append("**Depended by:** _None detected_")

    # Warnings
    if service_info.get("warnings"):
        lines.extend([
            "",
            "## Detection Warnings",
            "",
        ])
        for w in service_info["warnings"]:
            lines.append(f"- `{w}`")

    lines.append("")

    filepath = os.path.join(output_dir, "overview.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_api_endpoints_md(service_info, output_dir):
    """Generate api-endpoints.md for a service."""
    os.makedirs(output_dir, exist_ok=True)
    svc_id = service_info["service_id"]

    lines = [
        f"# {service_info.get('display_name', svc_id)} — API Endpoints",
        "",
        "<!-- Auto-generated by hw-knowledge-agent service-discovery -->",
        "<!-- DO NOT EDIT MANUALLY -->",
        "",
    ]

    if not service_info.get("apis"):
        lines.append("_No API endpoints detected._")
        lines.append("")
    else:
        # Group by source file
        by_source = {}
        for api in service_info["apis"]:
            src = api["source"]
            if src not in by_source:
                by_source[src] = []
            by_source[src].append(api)

        for source in sorted(by_source.keys()):
            lines.append(f"## {source}")
            lines.append("")
            lines.append("| Method | Path |")
            lines.append("|--------|------|")
            for api in sorted(by_source[source], key=lambda a: (a["path"], a["method"])):
                lines.append(f"| {api['method']} | `{api['path']}` |")
            lines.append("")

    filepath = os.path.join(output_dir, "api-endpoints.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_db_schema_md(service_info, output_dir):
    """Generate db-schema.md for a service."""
    os.makedirs(output_dir, exist_ok=True)
    svc_id = service_info["service_id"]

    lines = [
        f"# {service_info.get('display_name', svc_id)} — Database Schema",
        "",
        "<!-- Auto-generated by hw-knowledge-agent service-discovery -->",
        "<!-- DO NOT EDIT MANUALLY -->",
        "",
    ]

    data_items = service_info.get("owns_data", [])
    if not data_items:
        lines.append("_No database schemas detected._")
    elif len(data_items) == 1 and data_items[0]["type"] == "NO_MIGRATIONS_FOUND":
        lines.append("_NO_MIGRATIONS_FOUND — 未检测到数据库迁移文件_")
    else:
        for data in data_items:
            lines.append(f"## {data['type']}")
            lines.append("")
            lines.append(f"**Source:** `{data.get('file', 'N/A')}`")
            lines.append("")
            lines.append("_Schema details require manual documentation or DDL extraction._")
            lines.append("")

    lines.append("")

    filepath = os.path.join(output_dir, "db-schema.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(
        description="Discover services and generate seed knowledge.",
    )
    parser.add_argument("--services-dir", help="Services directory to scan")
    parser.add_argument("--output-dir", help="Output directory for knowledge files")
    parser.add_argument("--probe", action="store_true", help="Preview without writing")
    parser.add_argument("--registry-file", help="Output path for service-registry.yaml")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    services_dir = args.services_dir or _DEFAULT_SERVICES_DIR
    kb_dir = args.output_dir or _DEFAULT_KB_DIR
    registry_path = args.registry_file or _DEFAULT_REGISTRY_PATH

    if not os.path.isdir(services_dir):
        print(f"Error: Services directory not found: {services_dir}", file=sys.stderr)
        sys.exit(1)

    # Step 1: Inventory
    if args.verbose:
        print(f"Step 1: Scanning services in {services_dir}...")
    services = step1_service_inventory(services_dir)

    if not services:
        print("No services found (no git repos under services/).")
        return

    print(f"Found {len(services)} service(s): {', '.join(s['service_id'] for s in services)}")

    # Step 2 & 3: Detection for each service
    for svc_info in services:
        svc_path = os.path.join(services_dir, svc_info["service_id"])
        if args.verbose:
            print(f"\n  Processing {svc_info['service_id']}...")

        svc_info = step2_tech_stack_detection(svc_path, svc_info)
        if args.verbose:
            print(f"    Language: {svc_info['language']}, Framework: {svc_info['framework']}")

        svc_info = step3_api_data_detection(svc_path, svc_info)
        if args.verbose:
            print(f"    APIs: {len(svc_info.get('apis', []))} endpoints")
            print(f"    Data: {len(svc_info.get('owns_data', []))} schemas")
            print(f"    Infra deps: {len(svc_info.get('depends_on_infra', []))}")
            if svc_info.get("warnings"):
                print(f"    Warnings: {', '.join(svc_info['warnings'])}")

    # Compute depended_by (cross-service)
    all_ids = {s["service_id"] for s in services}
    for svc_info in services:
        svc_info["depended_by_services"] = []
    for svc_info in services:
        svc_id = svc_info["service_id"]
        for other in services:
            if other["service_id"] != svc_id and svc_id in other.get("depends_on_services", []):
                svc_info["depended_by_services"].append(other["service_id"])

    # Probe mode
    if args.probe:
        print("\n[Probe Mode] Would generate:")
        print(f"  - {registry_path}")
        for svc_info in services:
            svc_out = os.path.join(kb_dir, "services", svc_info["service_id"])
            print(f"  - {svc_out}/overview.md")
            print(f"  - {svc_out}/api-endpoints.md")
            print(f"  - {svc_out}/db-schema.md")
        return

    # Generate outputs
    print("\nGenerating knowledge files...")

    # Service registry
    generate_registry_yaml(services, registry_path)
    print(f"  Created: {registry_path}")

    # Per-service knowledge files
    for svc_info in services:
        svc_out = os.path.join(kb_dir, "services", svc_info["service_id"])
        generate_overview_md(svc_info, svc_out)
        generate_api_endpoints_md(svc_info, svc_out)
        generate_db_schema_md(svc_info, svc_out)
        print(f"  Created: {svc_out}/overview.md")
        print(f"  Created: {svc_out}/api-endpoints.md")
        print(f"  Created: {svc_out}/db-schema.md")

    print(f"\nDone. {len(services)} service(s) documented.")


if __name__ == "__main__":
    main()
