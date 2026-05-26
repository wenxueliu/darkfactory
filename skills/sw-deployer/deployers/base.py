"""Base class and dataclasses for environment-specific deployers.

参照 ``sw-lint-checker/checkers/base.py`` 的设计模式:
- ABC 定义部署器契约
- dataclass 封装部署参数和结果
- 子类通过覆写属性/方法实现不同环境/不同部署方式的适配

用法:
    deployer = TestDeployer()
    result = deployer.deploy(PackageInfo(path="./build/app.tar.gz"))
    if result.status == "SUCCESS":
        health = deployer.verify(result.endpoint)
"""

from __future__ import annotations

import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# Enums and dataclasses
# ---------------------------------------------------------------------------

class DeployStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass
class PackageInfo:
    """Description of the artifact to deploy."""

    path: str = ""                          # 安装包路径（tar.gz / dir / binary）
    name: str = ""                          # 服务名
    version: str = ""                       # 版本号
    env_vars: dict[str, str] = field(default_factory=dict)   # 部署时注入的环境变量
    extra: dict = field(default_factory=dict)                 # 业务自定义字段


@dataclass
class DeployResult:
    """Result of a deploy/verify/rollback operation."""

    status: str = ""                        # "SUCCESS" | "FAILED" | "TIMEOUT"
    target: str = ""                        # 目标环境
    method: str = ""                        # 部署方式: "direct" | "docker" | "k8s"
    endpoint: str = ""                      # 部署后可访问的 URL
    pid: int | None = None                  # 进程 ID（direct 模式）
    container_id: str = ""                  # 容器 ID（docker 模式）
    message: str = ""                       # 人类可读的结果描述
    logs: str = ""                          # 部署过程日志
    error: str = ""                         # 失败时的错误信息
    elapsed_ms: int = 0                     # 耗时（毫秒）


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def run_command(cmd: list[str], timeout: int = 300,
                env: dict | None = None) -> tuple[int, str, str]:
    """Run a shell command and return (exit_code, stdout, stderr)."""
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return -127, "", f"COMMAND_NOT_FOUND: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -124, "", f"TIMEOUT: {' '.join(cmd)} (>{timeout}s)"


def tool_is_available(name: str) -> bool:
    """Check whether *name* is on PATH."""
    return shutil.which(name) is not None


def wait_for_health(url: str, timeout: int = 30, interval: float = 1.0) -> bool:
    """Poll *url* until it returns 2xx, or *timeout* seconds elapse."""
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(url, timeout=2)
            if 200 <= resp.status < 300:
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class Deployer(ABC):
    """Abstract base for an environment-specific deployer.

    To add a new deployment target or method:
        1. Subclass ``Deployer``.
        2. Set ``target`` class attribute (e.g. ``"test"``, ``"production"``).
        3. Implement ``deploy()``, ``verify()``, ``rollback()``.

    The runner matches ``--target test`` → the first Deployer subclass whose
    ``target`` equals ``"test"``.

    **Business customization — subclass and override:**
        - ``deploy()`` — the core deployment logic.
        - ``verify()`` — post-deploy health check.
        - ``rollback()`` — revert a failed deployment.
        - ``handles()`` — custom matching logic (default: match by ``target``).

    Place custom subclasses in ``deployers_local/`` — they are discovered
    first and take priority over built-in deployers for the same target.
    """

    # -- identity (override in subclass) --------------------------------

    target: str = ""        # "test" | "production" | "staging" | ...

    # -- matching (override if needed) ----------------------------------

    @classmethod
    def handles(cls, target: str, method: str = "") -> bool:
        """Return True if this deployer should handle the given *target*
        and optional *method*.  Default: match by ``target`` only."""
        return cls.target == target

    # -- core operations (must implement) -------------------------------

    @abstractmethod
    def deploy(self, package: PackageInfo) -> DeployResult:
        """Deploy *package* to the target environment.

        This is the main entry point.  Implement the full deployment
        logic: upload artifact, start service, configure networking, etc.
        """
        ...

    @abstractmethod
    def verify(self, endpoint: str = "",
               timeout: int = 30) -> DeployResult:
        """Verify the deployment is healthy.

        Typically checks: HTTP health endpoint, process alive, port open, etc.
        """
        ...

    @abstractmethod
    def rollback(self, package: PackageInfo | None = None) -> DeployResult:
        """Rollback a failed deployment.

        Stop the deployed service, clean up resources, restore previous state.
        """
        ...

    # -- helpers ---------------------------------------------------------

    def run(self, cmd: list[str], timeout: int = 300,
            env: dict | None = None) -> tuple[int, str, str]:
        """Thin wrapper around ``run_command`` for convenience."""
        return run_command(cmd, timeout=timeout, env=env)
