"""Docker-based deployer — 通过 Docker 容器部署。

适用于:
- 测试/生产环境（需要 Docker）
- 微服务容器化部署
- docker run / docker-compose
"""

from __future__ import annotations

import json
import time

from .base import Deployer, DeployResult, PackageInfo, run_command, tool_is_available


class DockerDeployer(Deployer):
    """Deploy by running a Docker container."""

    target = "production"
    method = "docker"

    _container_id: str = ""
    _image: str = ""

    # -- core operations -------------------------------------------------

    def deploy(self, package: PackageInfo) -> DeployResult:
        t0 = time.time()

        if not tool_is_available("docker"):
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                error="docker not found on PATH",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        image = package.extra.get("image", package.name)
        tag = package.extra.get("tag", package.version or "latest")
        full_image = f"{image}:{tag}"
        port = package.extra.get("port", "8080")

        # Build args for docker run
        cmd = [
            "docker", "run", "-d",
            "--name", f"{package.name}-{int(time.time())}",
            "-p", f"{port}:{port}",
        ]
        for k, v in package.env_vars.items():
            cmd.extend(["-e", f"{k}={v}"])
        cmd.append(full_image)

        exit_code, stdout, stderr = run_command(cmd, timeout=120)
        if exit_code != 0:
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                error=stderr or f"docker run failed (exit {exit_code})",
                logs=stdout + "\n" + stderr,
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        container_id = stdout.strip()[:12]
        self._container_id = container_id
        self._image = full_image

        endpoint = f"http://127.0.0.1:{port}"
        return DeployResult(
            status="SUCCESS",
            target=self.target,
            method=self.method,
            endpoint=endpoint,
            container_id=container_id,
            message=f"Container started ({container_id}, image={full_image})",
            logs=stdout,
            elapsed_ms=int((time.time() - t0) * 1000),
        )

    def verify(self, endpoint: str = "", timeout: int = 30) -> DeployResult:
        t0 = time.time()

        # Check container running
        if self._container_id:
            exit_code, stdout, _ = run_command(
                ["docker", "inspect", "-f", "{{.State.Running}}",
                 self._container_id],
                timeout=10,
            )
            if exit_code != 0 or stdout.strip() != "true":
                # Try to get logs
                _, logs, _ = run_command(
                    ["docker", "logs", "--tail", "50", self._container_id],
                    timeout=10,
                )
                return DeployResult(
                    status="FAILED",
                    target=self.target,
                    method=self.method,
                    endpoint=endpoint,
                    container_id=self._container_id,
                    error="Container not running",
                    logs=logs,
                    elapsed_ms=int((time.time() - t0) * 1000),
                )

        # Health check
        if endpoint:
            from .base import wait_for_health
            health_url = f"{endpoint.rstrip('/')}/health"
            ok = wait_for_health(health_url, timeout=timeout)
            if ok:
                return DeployResult(
                    status="SUCCESS",
                    target=self.target,
                    method=self.method,
                    endpoint=endpoint,
                    container_id=self._container_id,
                    message="Health check passed",
                    elapsed_ms=int((time.time() - t0) * 1000),
                )
            else:
                return DeployResult(
                    status="FAILED",
                    target=self.target,
                    method=self.method,
                    endpoint=endpoint,
                    container_id=self._container_id,
                    error=f"Health check timeout ({timeout}s)",
                    elapsed_ms=int((time.time() - t0) * 1000),
                )

        return DeployResult(
            status="SUCCESS",
            target=self.target,
            method=self.method,
            endpoint=endpoint,
            container_id=self._container_id,
            message="Container is running (no health check URL)",
            elapsed_ms=int((time.time() - t0) * 1000),
        )

    def rollback(self, package: PackageInfo | None = None) -> DeployResult:
        t0 = time.time()

        if not self._container_id:
            return DeployResult(
                status="SUCCESS",
                target=self.target,
                method=self.method,
                message="Nothing to rollback",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        # Stop and remove container
        run_command(["docker", "stop", self._container_id], timeout=30)
        run_command(["docker", "rm", self._container_id], timeout=10)

        cid = self._container_id
        self._container_id = ""

        return DeployResult(
            status="SUCCESS",
            target=self.target,
            method=self.method,
            message=f"Container stopped and removed ({cid})",
            elapsed_ms=int((time.time() - t0) * 1000),
        )
