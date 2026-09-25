"""Data structures used by the document contract resolver."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResourceRoot:
    """A search root. Roots are supplied in descending precedence order."""

    scope: str
    path: Path


@dataclass(frozen=True)
class ResourceSelection:
    """The resource selected for one definition component."""

    name: str
    scope: str
    path: Path | None
    package_path: Path
    variant: str
    mode: str = "replace"
    disabled: bool = False


@dataclass(frozen=True)
class DocumentDefinition:
    """A resolved document definition assembled from layered resources."""

    document_type: str
    variant: str
    contract: str
    version: str
    resources: dict[str, ResourceSelection] = field(default_factory=dict)
    candidates: tuple[Path, ...] = ()

    def resource(self, name: str) -> ResourceSelection | None:
        return self.resources.get(name)


@dataclass(frozen=True)
class Finding:
    """One validation or gate finding."""

    rule_id: str
    severity: str
    message: str
    source: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    """Combined validator and gate result."""

    findings: tuple[Finding, ...] = ()
    validator_source: Path | None = None
    gate_source: Path | None = None

    @property
    def passed(self) -> bool:
        return not any(finding.severity.lower() in {"error", "fatal", "p0", "p1"} for finding in self.findings)

    @property
    def errors(self) -> tuple[Finding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.severity.lower() in {"error", "fatal", "p0", "p1"}
        )
