"""Kubernetes-based deployer — 通过 kubectl 部署到 K8s 集群。

适用于:
- 生产环境
- K8s 集群部署
- 支持 Deployment / Service / ConfigMap 等资源

业务方需在 ``deployers_local/`` 中覆写 ``_build_manifests()``
以生成符合自身 CI/CD 规范的 K8s YAML。
"""

from __future__ import annotations

import json
import tempfile
import time

from .base import Deployer, DeployResult, PackageInfo, run_command, tool_is_available


class K8sDeployer(Deployer):
    """Deploy to Kubernetes via ``kubectl apply``."""

    target = "production"
    method = "k8s"

    _namespace: str = "default"
    _release_name: str = ""

    # -- customisation points (override in subclass) ---------------------

    def _build_manifests(self, package: PackageInfo) -> str:
        """Build K8s YAML manifests and return them as a string.

        **Override this in your local deployer** to generate manifests
        from your Helm chart, Kustomize, or custom template engine.
        """
        port = package.extra.get("port", "8080")
        replicas = package.extra.get("replicas", "1")
        image = package.extra.get("image", f"{package.name}:{package.version or 'latest'}")

        return f"""---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {package.name}
  namespace: {self._namespace}
  labels:
    app: {package.name}
    version: "{package.version}"
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {package.name}
  template:
    metadata:
      labels:
        app: {package.name}
        version: "{package.version}"
    spec:
      containers:
      - name: {package.name}
        image: {image}
        ports:
        - containerPort: {port}
        env:
        - name: PORT
          value: "{port}"
---
apiVersion: v1
kind: Service
metadata:
  name: {package.name}
  namespace: {self._namespace}
spec:
  selector:
    app: {package.name}
  ports:
  - port: {port}
    targetPort: {port}
  type: ClusterIP
"""

    def _get_endpoint(self, package: PackageInfo) -> str:
        """Return the service endpoint after deploy.  Override for Ingress/LB."""
        return (f"http://{package.name}.{self._namespace}.svc.cluster.local:"
                f"{package.extra.get('port', '8080')}")

    # -- core operations -------------------------------------------------

    def deploy(self, package: PackageInfo) -> DeployResult:
        t0 = time.time()

        if not tool_is_available("kubectl"):
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                error="kubectl not found on PATH",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        self._namespace = package.extra.get("namespace", "default")
        self._release_name = package.name

        # Generate manifests
        manifests = self._build_manifests(package)

        # Apply
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(manifests)
            manifest_path = f.name

        try:
            exit_code, stdout, stderr = run_command(
                ["kubectl", "apply", "-f", manifest_path],
                timeout=120,
            )
        finally:
            import os
            os.unlink(manifest_path)

        if exit_code != 0:
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                error=stderr or f"kubectl apply failed (exit {exit_code})",
                logs=stdout + "\n" + stderr,
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        # Wait for rollout
        roll_exit, roll_out, roll_err = run_command(
            ["kubectl", "rollout", "status", f"deployment/{package.name}",
             "-n", self._namespace, "--timeout=120s"],
            timeout=150,
        )

        endpoint = self._get_endpoint(package)
        return DeployResult(
            status="SUCCESS" if roll_exit == 0 else "FAILED",
            target=self.target,
            method=self.method,
            endpoint=endpoint,
            message=roll_out.strip() or "Deployed",
            logs=stdout + "\n" + roll_out,
            error=roll_err if roll_exit != 0 else "",
            elapsed_ms=int((time.time() - t0) * 1000),
        )

    def verify(self, endpoint: str = "", timeout: int = 30) -> DeployResult:
        t0 = time.time()

        # Check pod status
        exit_code, stdout, _ = run_command(
            ["kubectl", "get", "pods", "-n", self._namespace,
             "-l", f"app={self._release_name}",
             "-o", "json"],
            timeout=10,
        )
        if exit_code != 0:
            return DeployResult(
                status="FAILED",
                target=self.target,
                method=self.method,
                error="Failed to query pods",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        try:
            pod_data = json.loads(stdout)
            for item in pod_data.get("items", []):
                phase = item.get("status", {}).get("phase", "")
                if phase not in ("Running", "Succeeded"):
                    return DeployResult(
                        status="FAILED",
                        target=self.target,
                        method=self.method,
                        error=f"Pod phase: {phase}",
                        elapsed_ms=int((time.time() - t0) * 1000),
                    )
        except json.JSONDecodeError:
            pass

        return DeployResult(
            status="SUCCESS",
            target=self.target,
            method=self.method,
            endpoint=endpoint,
            message="All pods running",
            elapsed_ms=int((time.time() - t0) * 1000),
        )

    def rollback(self, package: PackageInfo | None = None) -> DeployResult:
        t0 = time.time()

        if not self._release_name:
            return DeployResult(
                status="SUCCESS",
                target=self.target,
                method=self.method,
                message="Nothing to rollback",
                elapsed_ms=int((time.time() - t0) * 1000),
            )

        # Delete the deployment and service
        exit_code, stdout, stderr = run_command(
            ["kubectl", "delete", "deployment", self._release_name,
             "-n", self._namespace, "--ignore-not-found"],
            timeout=30,
        )
        run_command(
            ["kubectl", "delete", "service", self._release_name,
             "-n", self._namespace, "--ignore-not-found"],
            timeout=30,
        )

        name = self._release_name
        self._release_name = ""

        return DeployResult(
            status="SUCCESS",
            target=self.target,
            method=self.method,
            message=f"Deleted deployment and service ({name})",
            logs=stdout,
            error=stderr if exit_code != 0 else "",
            elapsed_ms=int((time.time() - t0) * 1000),
        )
