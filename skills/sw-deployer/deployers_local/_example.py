"""Example custom deployer — copy this file and rename it (remove the leading
underscore) to create a local deployer override.

Local deployers are auto-discovered and take priority over built-in deployers
for the same target.  For example, naming this file ``test_deployer.py``
(with ``target = "test"``) will replace the built-in ``DirectDeployer``.

Business customization examples:
    - Use Docker Compose for test environment instead of direct process
    - Use Helm instead of raw ``kubectl apply`` for production
    - Add a ``staging`` target with its own deployment logic
"""

from __future__ import annotations

from deployers.base import Deployer, DeployResult, PackageInfo


class ExampleDeployer(Deployer):
    """Custom deployer — rename and adjust for your business."""

    target = "example"    # "test" | "production" | "staging" | ...
    method = "custom"

    def deploy(self, package: PackageInfo) -> DeployResult:
        # Implement your deployment logic here.
        # Examples:
        #   - docker-compose up
        #   - helm upgrade --install
        #   - scp + ssh remote start
        #   - cloud SDK (aws / gcloud / az CLI)
        return DeployResult(
            status="SUCCESS",
            target=self.target,
            method=self.method,
            message=f"Deployed {package.name} (override me)",
        )

    def verify(self, endpoint: str = "", timeout: int = 30) -> DeployResult:
        # Implement health check logic.
        return DeployResult(
            status="SUCCESS",
            target=self.target,
            method=self.method,
            endpoint=endpoint,
            message="Health check passed",
        )

    def rollback(self, package: PackageInfo | None = None) -> DeployResult:
        # Implement rollback logic.
        return DeployResult(
            status="SUCCESS",
            target=self.target,
            method=self.method,
            message="Rollback complete",
        )
