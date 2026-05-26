"""Direct-process deployer — 直接在本机启动服务进程。

适用于:
- 本地开发 / 测试环境
- 单机部署
- 快速验证（没有容器/K8s 依赖）
"""

from __future__ import annotations

import os
import signal
import subprocess
import time

from .base import Deployer, DeployResult, PackageInfo, tool_is_available


class DirectDeployer(Deployer):
    """Deploy by starting the service as a subprocess on localhost."""

    target = "test"
    method = "direct"

    _process: subprocess.Popen | None = None

    # -- core operations -------------------------------------------------

    def deploy(self, package: PackageInfo) -> DeployResult:
        t0 = time.time()

        # Resolve the executable from the package
        exe = package.extra.get("executable", "")
        if not exe:
            exe = package.path  # assume path is the binary itself

        if not os.path.exists(exe):
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                error=f"Executable not found: {exe}",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        port = package.extra.get("port", "8080")
        args = package.extra.get("args", "")

        cmd = [exe]
        if args:
            cmd.extend(args.split())

        env = os.environ.copy()
        env.update(package.env_vars)
        env.setdefault("PORT", str(port))

        try:
            self._process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except Exception as e:
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                error=f"Failed to start process: {e}",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        # Brief wait for process to start
        time.sleep(1)

        if self._process.poll() is not None:
            _, stderr = self._process.communicate()
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                error=f"Process exited immediately: {stderr[:500]}",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        endpoint = f"http://127.0.0.1:{port}"
        return DeployResult(
            status="SUCCESS",
            target=self.target,
            method=self.method,
            endpoint=endpoint,
            pid=self._process.pid,
            message=f"Service started (pid={self._process.pid}, port={port})",
            elapsed_ms=int((time.time() - t0) * 1000),
        )

    def verify(self, endpoint: str = "", timeout: int = 30) -> DeployResult:
        t0 = time.time()

        if not endpoint:
            endpoint = "http://127.0.0.1:8080"

        # Check process alive
        if self._process is not None and self._process.poll() is not None:
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                endpoint=endpoint,
                error=f"Process exited with code {self._process.returncode}",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        # Check HTTP health
        from .base import wait_for_health
        health_url = f"{endpoint.rstrip('/')}/health"
        ok = wait_for_health(health_url, timeout=timeout)

        if ok:
            return DeployResult(
                status="SUCCESS",
                target=self.target,
                method=self.method,
                endpoint=endpoint,
                message="Health check passed",
                elapsed_ms=int((time.time() - t0) * 1000),
            )
        else:
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                endpoint=endpoint,
                error=f"Health check timeout ({timeout}s)",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

    def rollback(self, package: PackageInfo | None = None) -> DeployResult:
        t0 = time.time()

        if self._process is None:
            return DeployResult(
                status="SUCCESS",
                target=self.target,
                method=self.method,
                message="Nothing to rollback",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        try:
            self._process.send_signal(signal.SIGTERM)
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        except Exception as e:
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                error=str(e),
                elapsed_ms=int((time.time() - t0) * 1000),
            )
        finally:
            self._process = None

        return DeployResult(
            status="SUCCESS",
            target=self.target,
            method=self.method,
            message="Service stopped",
            elapsed_ms=int((time.time() - t0) * 1000),
        )
