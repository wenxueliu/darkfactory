# 技能定制指南 (Customization)

> **初次接触？** 先看 [quickstart.md](quickstart.md) 和 [concepts.md](concepts.md)。本文说明如何自定义 sw-lint-checker 和 sw-deployer 的行为，包括新增语言检查器、覆盖内置部署器等。

---

## 通用模式：ABC + 自动发现 + Local 覆盖

`sw-lint-checker` 和 `sw-deployer` 使用相同的可扩展架构，支持业务方在不修改框架代码的前提下自定义行为：

```
ABC 基类（定义契约）
    → 内置实现（框架提供，开箱即用）
    → checkers_local/ 或 deployers_local/（业务方自定义，优先级最高）
```

**核心机制（两阶段自动发现）：**

1. 框架自动扫描 `*_local/` 目录，加载所有非 `_` 开头的 `.py` 文件
2. 标记 local 模块中已覆盖的语言/target，排除同名的内置模块
3. 合并两阶段结果（local 优先）

这一机制意味着：**只要将自定义模块放入 `*_local/` 目录，无需修改任何框架文件**。

| Skill | ABC | Local 目录 | 统一入口 |
|-------|-----|-----------|---------|
| `sw-lint-checker` | `LintChecker` (`checkers/base.py`) | `checkers_local/` | `lint_runner.py` |
| `sw-deployer` | `Deployer` (`deployers/base.py`) | `deployers_local/` | `deploy_runner.py` |

---

## 1. 自定义 sw-lint-checker

### 1.1 架构速览

```
sw-lint-checker/
├── lint_runner.py                 # 统一入口：自动发现 + 按语言匹配 + 执行 + 输出
├── checkers/                      # 内置检查器
│   ├── __init__.py               # 自动发现逻辑（local 优先）
│   ├── base.py                   # LintChecker ABC + CheckResult/FixResult
│   ├── python_checker.py         # Python: ruff check + ruff format
│   ├── javascript_checker.py     # JavaScript: eslint + prettier
│   ├── typescript_checker.py     # TypeScript: eslint + tsc --noEmit
│   ├── go_checker.py             # Go: golangci-lint + gofmt + go vet
│   ├── shell_checker.py          # Shell: shellcheck + shfmt
│   ├── markdown_checker.py       # Markdown: markdownlint
│   ├── css_checker.py            # CSS: stylelint + prettier
│   ├── dockerfile_checker.py     # Dockerfile: hadolint
│   ├── yaml_checker.py           # YAML: yamllint
│   ├── toml_checker.py           # TOML: taplo
│   └── json_checker.py           # JSON: prettier + jsonlint
└── checkers_local/               # 【业务方】自定义检查器放在这里
    └── _example.py               # 模板示例（不会自动加载）
```

### 1.2 内置检查器一览

| 语言 | 检查器类 | 工具 | handles() 匹配 |
|------|---------|------|---------------|
| python | `PythonChecker` | ruff check + ruff format | `.py` |
| javascript | `JavaScriptChecker` | eslint + prettier | `.js`, `.jsx`, `.mjs` |
| typescript | `TypeScriptChecker` | eslint + tsc --noEmit | `.ts`, `.tsx` |
| go | `GoChecker` | golangci-lint + gofmt + go vet | `.go` |
| shell | `ShellChecker` | shellcheck + shfmt | `.sh`, `.bash`, `.zsh` |
| markdown | `MarkdownChecker` | markdownlint | `.md` |
| css | `CssChecker` | stylelint + prettier | `.css`, `.scss`, `.less` |
| dockerfile | `DockerfileChecker` | hadolint | `Dockerfile*` |
| yaml | `YamlChecker` | yamllint | `.yaml`, `.yml` |
| toml | `TomlChecker` | taplo | `.toml` |
| json | `JsonChecker` | prettier + jsonlint | `.json` |

### 1.3 场景：替换内置检查器（如用 flake8 替代 ruff）

团队要求 Python 代码使用 flake8 做规范检查，而不是默认的 ruff。

#### 实现步骤

在 `checkers_local/` 中创建自定义检查器（以 `checkers_local/_example.py` 为模板）：

```python
# checkers_local/python_checker.py
from checkers.python_checker import PythonChecker
from checkers.base import Severity


class Flake8PythonChecker(PythonChecker):
    """Custom Python checker: flake8 instead of ruff."""

    # 覆写工具标识
    tool_name = "flake8"

    # 覆写工具可用性检查
    def is_available(self) -> bool:
        from checkers.base import tool_is_available
        return tool_is_available("flake8")

    def install_hint(self) -> str:
        return "pip install flake8"

    # 覆写检查命令——用 flake8 替代 ruff
    def _check_cmd(self, files: list[str]) -> list[str]:
        cfg = self.get_config()
        cmd = ["flake8"]
        if cfg.get("config"):
            cmd += ["--config", cfg["config"]]
        return cmd + files

    # flake8 没有 auto-fix
    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        return []

    # 自定义严重级别映射
    @staticmethod
    def severity_map() -> dict[str, Severity]:
        return {
            "E": Severity.P0,  # 语法错误
            "F": Severity.P0,  # pyflakes 问题（提升为 P0）
            "W": Severity.P1,  # 警告
            "N": Severity.P2,  # 命名规范
        }
```

**完成后**，`lint_runner.py` 会自动发现 `Flake8PythonChecker`，并因其 `language = "python"` 与内置 `PythonChecker` 冲突而优先使用它。

### 1.4 场景：添加新语言的支持

团队引入了一种新语言（如 Rust），需要为其添加 lint 检查。

#### 实现步骤

在 `checkers_local/` 中创建新的检查器类：

```python
# checkers_local/rust_checker.py
from checkers.base import (
    LintChecker, LintError, Severity,
    CheckResult, FixResult, run_tool, tool_is_available,
)


class RustChecker(LintChecker):
    """Rust lint checker using clippy + rustfmt."""

    # -- 身份标识 --
    language = "rust"
    tool_name = "clippy"

    # -- 文件匹配 --
    @classmethod
    def handles(cls, file_path: str) -> bool:
        return file_path.endswith(".rs")

    # -- 工具可用性 --
    def is_available(self) -> bool:
        return tool_is_available("cargo")

    def install_hint(self) -> str:
        return "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"

    # -- 检查命令 --
    def _check_cmd(self, files: list[str]) -> list[str]:
        # clippy 在工作区级别运行，不需要传文件列表
        return ["cargo", "clippy", "--", "-D", "warnings"]

    def _fix_cmds(self, files: list[str]) -> list[list[str]]:
        return [["cargo", "fmt"]]

    # -- 核心方法 --
    def check(self, files: list[str]) -> CheckResult:
        if not self.is_available():
            return CheckResult(
                language=self.language, tool_name=self.tool_name,
                exit_code=0, tool_missing=True, install_hint=self.install_hint(),
            )
        exit_code, stdout, stderr = run_tool(self._check_cmd(files))
        errors = self._parse_output(stdout + stderr)
        return CheckResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=exit_code, errors=errors,
            raw_output=stdout + "\n" + stderr,
        )

    def auto_fix(self, files: list[str]) -> FixResult:
        exit_code, stdout, stderr = run_tool(["cargo", "fmt"])
        # 修复后重新检查
        check_result = self.check(files)
        return FixResult(
            language=self.language, tool_name=self.tool_name,
            exit_code=exit_code, fixed_count=0,  # rustfmt 不报告修复数量
            remaining_errors=check_result.errors,
        )

    @staticmethod
    def severity_map() -> dict[str, Severity]:
        return {"error": Severity.P0, "warning": Severity.P1}

    @staticmethod
    def auto_fixable_rules() -> set[str]:
        return {"rustfmt"}

    def _parse_output(self, output: str) -> list[LintError]:
        """解析 clippy 输出为 LintError 列表。"""
        errors = []
        for line in output.splitlines():
            if "warning" in line.lower() and "--> " not in line:
                errors.append(LintError(
                    file="src/", line=0, rule="clippy::warning",
                    message=line, severity=Severity.P1,
                ))
        return errors
```

**完成后**，`lint_runner.py` 会自动发现 `RustChecker`，并将其加入可用的检查器列表。

### 1.5 其他常用自定义场景

| 场景 | 实现方式 | 示例 |
|------|---------|------|
| 调整规则严重级别 | 覆写 `severity_map()` | 将 Python `F401` 从 P2 改为 P1 |
| 添加自定义文件扩展名 | 覆写 `handles()` | 让 PythonChecker 也处理 `.jinja2` |
| 添加额外检查步骤 | 在 `_fix_cmds()` 中追加命令 | 先 eslint --fix，再 prettier --write |
| 替换使用的工具 | 覆写 `_check_cmd()` 和 `_fix_cmds()` | 用 pylint 替代 ruff |
| 传递自定义配置 | 覆写 `get_config()` | 传入 `.pylintrc` 路径 |

---

## 2. 自定义 sw-deployer

### 2.1 架构速览

```
sw-deployer/
├── deploy_runner.py                 # 统一入口：--target 匹配 → 执行 → 输出
├── deployers/                       # 内置部署器
│   ├── __init__.py                 # 自动发现逻辑（local 优先）
│   ├── base.py                     # Deployer ABC + PackageInfo + DeployResult
│   ├── direct_deployer.py          # 直接启动进程（test 环境默认）
│   ├── docker_deployer.py          # Docker 容器（production 环境默认）
│   └── k8s_deployer.py             # Kubernetes（production 环境默认）
└── deployers_local/                # 【业务方】自定义部署器放在这里
    └── _example.py                 # 模板示例（不会自动加载）
```

### 2.2 内置部署器一览

| 部署器 | target | method | 核心行为 |
|--------|--------|--------|---------|
| `DirectDeployer` | `test` | `direct` | 在当前环境直接启动进程 |
| `DockerDeployer` | `production` | `docker` | 构建并运行 Docker 容器 |
| `K8sDeployer` | `production` | `k8s` | 部署到 Kubernetes 集群 |

> **注意：** `DockerDeployer` 和 `K8sDeployer` 的 target 都是 `"production"`。
> 匹配时按发现顺序返回第一个。如需用 k8s 替代 docker 作为 production 部署器，
> 请在 `deployers_local/` 中创建覆盖（见下文 2.4 节）。

### 2.3 场景：覆盖内置部署器（用 Docker Compose 替代 DirectDeployer）

测试环境使用 Docker Compose 替代默认的直接进程启动。

#### 实现步骤

在 `deployers_local/` 中创建自定义部署器（以 `deployers_local/_example.py` 为模板）：

```python
# deployers_local/test_deployer.py
from deployers.base import Deployer, DeployResult, PackageInfo, run_command


class DockerComposeTestDeployer(Deployer):
    target = "test"
    method = "docker-compose"

    def deploy(self, package: PackageInfo) -> DeployResult:
        compose_file = package.extra.get("compose_file", "docker-compose.test.yml")
        exit_code, stdout, stderr = run_command(
            ["docker-compose", "-f", compose_file, "up", "-d", "--build"],
            timeout=120,
        )
        if exit_code != 0:
            return DeployResult(
                status="FAILED", target=self.target,
                method=self.method, error=stderr,
            )
        return DeployResult(
            status="SUCCESS", target=self.target,
            method=self.method, message="Docker Compose 部署完成",
            logs=stdout,
        )

    def verify(self, endpoint: str = "", timeout: int = 30) -> DeployResult:
        from deployers.base import wait_for_health
        healthy = wait_for_health(endpoint, timeout=timeout) if endpoint else True
        return DeployResult(
            status="SUCCESS" if healthy else "FAILED",
            target=self.target, method=self.method,
            endpoint=endpoint,
            message="Health check passed" if healthy else "Health check failed",
        )

    def rollback(self, package: PackageInfo | None = None) -> DeployResult:
        exit_code, stdout, stderr = run_command(["docker-compose", "down", "-v"])
        return DeployResult(
            status="SUCCESS" if exit_code == 0 else "FAILED",
            target=self.target, method=self.method,
            message="Rollback complete" if exit_code == 0 else f"Rollback failed: {stderr}",
        )
```

**完成后**，`deploy_runner.py --target test` 会自动匹配到 `DockerComposeTestDeployer`，因其 `target = "test"` 与内置 `DirectDeployer` 冲突而优先使用。

### 2.4 场景：新增部署目标（如 staging 环境）

团队有一个预发布环境（staging），需要自己的部署逻辑。

#### 实现步骤

在 `deployers_local/` 中创建新部署器：

```python
# deployers_local/staging_deployer.py
from deployers.base import Deployer, DeployResult, PackageInfo, run_command


class StagingDeployer(Deployer):
    target = "staging"
    method = "docker"

    def deploy(self, package: PackageInfo) -> DeployResult:
        # 自定义 staging 部署逻辑
        image = package.extra.get("image", f"{package.name}:{package.version}")
        port = package.extra.get("port", "8080")
        exit_code, stdout, stderr = run_command([
            "docker", "run", "-d", "--name", f"{package.name}-staging",
            "-p", f"{port}:{port}",
            image,
        ], timeout=120)
        # ...

    def verify(self, endpoint: str = "", timeout: int = 30) -> DeployResult:
        # ...

    def rollback(self, package: PackageInfo | None = None) -> DeployResult:
        # ...
```

**完成后**，`deploy_runner.py --target staging` 即可匹配到 `StagingDeployer`。

### 2.5 场景：生产环境用 Helm 替代 K8sDeployer

团队使用 Helm 管理 Kubernetes 部署，需要覆盖内置的 `K8sDeployer`。

```python
# deployers_local/production_deployer.py
from deployers.base import Deployer, DeployResult, PackageInfo, run_command


class HelmProductionDeployer(Deployer):
    target = "production"
    method = "helm"

    def deploy(self, package: PackageInfo) -> DeployResult:
        chart = package.extra.get("helm_chart", f"./charts/{package.name}")
        ns = package.extra.get("namespace", "default")
        release = package.extra.get("helm_release", package.name)
        exit_code, stdout, stderr = run_command([
            "helm", "upgrade", "--install", release, chart,
            "-n", ns,
            "--set", f"image.tag={package.version}",
            "--wait",
        ], timeout=300)
        # ...

    def verify(self, endpoint: str = "", timeout: int = 30) -> DeployResult:
        from deployers.base import wait_for_health
        healthy = wait_for_health(endpoint, timeout=timeout)
        return DeployResult(
            status="SUCCESS" if healthy else "FAILED",
            target=self.target, method=self.method,
            message="Helm deploy healthy" if healthy else "Helm deploy unhealthy",
        )

    def rollback(self, package: PackageInfo | None = None) -> DeployResult:
        # helm rollback
        release = package.extra.get("helm_release", package.name) if package else ""
        exit_code, stdout, stderr = run_command(
            ["helm", "rollback", release] if release else ["helm", "list"],
            timeout=120,
        )
        return DeployResult(
            status="SUCCESS" if exit_code == 0 else "FAILED",
            target=self.target, method=self.method,
            message="Helm rollback complete" if exit_code == 0 else stderr,
        )
```

**完成后**，`HelmProductionDeployer` 的 `target = "production"` 与内置 `DockerDeployer` 和 `K8sDeployer` 冲突，自动获得优先权。

### 2.6 常用自定义场景一览

| 场景 | 实现方式 | 文件名示例 |
|------|---------|-----------|
| 测试环境用 Docker Compose | 新建 target=`"test"` 的 Deployer | `deployers_local/test_deployer.py` |
| 生产环境用 Helm | 新建 target=`"production"` 的 Deployer | `deployers_local/production_deployer.py` |
| 新增 staging 环境 | 新建 target=`"staging"` 的 Deployer | `deployers_local/staging_deployer.py` |
| 自定义生产部署 | 新建 target=`"production"` 的 Deployer | `deployers_local/prod_custom_deployer.py` |
| 部署前执行数据库迁移 | 在 `deploy()` 中先调用迁移命令 | 集成到现有部署器中 |

---

## 3. 验证自定义结果

### 3.1 验证 lint 自定义

```bash
# 查看当前生效的检查器列表（local 优先）
python skills/sw-lint-checker/lint_runner.py --help

# 运行检查
python skills/sw-lint-checker/lint_runner.py --auto-fix --json

# 也可通过 --files 指定特定文件测试
python skills/sw-lint-checker/lint_runner.py --files src/main.py --json
```

### 3.2 验证部署自定义

```bash
# 查看所有可用部署器（local 标有 "local" 标记）
python skills/sw-deployer/deploy_runner.py --list

# 预期输出：
#   TARGET           CLASS                            METHOD       SOURCE
#   --------------------------------------------------------------------------
#   test             DockerComposeTestDeployer        docker-compose local
#   production       DockerDeployer                   docker         built-in
#   staging          StagingDeployer                  docker         local

# 测试部署
python skills/sw-deployer/deploy_runner.py --target test --package ./build/app --json
```

---

## 4. 补充说明

### 4.1 文件命名规则

`*_local/` 目录中的文件需要遵循：
- **只会加载** 不以 `_` 开头的 `.py` 文件（`_example.py` 不会加载）
- **加载顺序** 按文件名排序，多个自定义模块的优先级按 `handles()`/`target` 去重

### 4.2 不修改框架文件

自定义过程中不需要修改 `checkers/`、`deployers/` 或 `lint_runner.py`/`deploy_runner.py` 中的任何框架代码。所有自定义都放在 `*_local/` 目录中。

### 4.3 源码参考

| 文件 | 说明 |
|------|------|
| `checkers/base.py` | `LintChecker` ABC 定义，所有自定义检查器需阅读 |
| `checkers/__init__.py` | 自动发现逻辑，理解 local 优先机制 |
| `checkers_local/_example.py` | 自定义检查器模板，可直接复制修改 |
| `deployers/base.py` | `Deployer` ABC 定义，自定义部署器必读 |
| `deployers/__init__.py` | 自动发现逻辑，理解 local 优先机制 |
| `deployers_local/_example.py` | 自定义部署器模板，可直接复制修改 |

---

## 相关文档

| 想了解... | 看这里 |
|----------|--------|
| sw-lint-checker 完整参考 | [SKILL.md](../skills/sw-lint-checker/SKILL.md) |
| sw-deployer 完整参考 | [SKILL.md](../skills/sw-deployer/SKILL.md) |
| 配置参考（business_domain 等） | [configuration.md](configuration.md) |
| Agent 架构总览 | [architecture.md](architecture.md) |
| 常见问题 | [faq.md](faq.md) |
