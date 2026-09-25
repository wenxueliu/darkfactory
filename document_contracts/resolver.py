"""Resolve document definitions across project, user, and built-in roots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .errors import DefinitionNotFoundError, InvalidManifestError, InvalidResourceError
from .models import DocumentDefinition, ResourceRoot, ResourceSelection


RESOURCE_NAMES = ("template", "gate", "validator")


@dataclass(frozen=True)
class _Candidate:
    root: ResourceRoot
    path: Path
    variant: str
    manifest_path: Path
    manifest: dict[str, Any]


class DefinitionResolver:
    """Resolve a document definition using resource-level layered fallback.

    ``roots`` must be ordered from highest to lowest precedence. For each root,
    an exact variant is checked before that root's ``default`` variant.
    """

    def __init__(self, roots: Iterable[ResourceRoot]):
        self.roots = tuple(roots)

    def resolve(
        self,
        document_type: str,
        variant: str = "default",
    ) -> DocumentDefinition:
        candidates = self._candidates(document_type, variant)
        if not candidates:
            searched = ", ".join(str(root.path) for root in self.roots) or "<no roots>"
            raise DefinitionNotFoundError(
                f"No document definition found for {document_type}/{variant}; searched {searched}"
            )

        metadata = candidates[0].manifest
        contract = self._required_string(metadata, "contract", candidates[0].manifest_path)
        version = self._required_string(metadata, "version", candidates[0].manifest_path)
        for candidate in candidates:
            candidate_contract = self._required_string(
                candidate.manifest, "contract", candidate.manifest_path
            )
            candidate_version = self._required_string(
                candidate.manifest, "version", candidate.manifest_path
            )
            if candidate_contract != contract or candidate_version != version:
                raise InvalidManifestError(
                    f"Contract mismatch in {candidate.manifest_path}: "
                    f"expected {contract}@{version}, got {candidate_contract}@{candidate_version}"
                )
        resources: dict[str, ResourceSelection] = {}

        for name in RESOURCE_NAMES:
            selection = self._resolve_resource(name, candidates)
            if selection is not None:
                resources[name] = selection

        template = resources.get("template")
        if template is None or template.disabled or template.path is None:
            raise InvalidManifestError(
                f"Resolved definition has no usable template: {document_type}/{variant}"
            )

        return DocumentDefinition(
            document_type=document_type,
            variant=variant,
            contract=contract,
            version=version,
            resources=resources,
            candidates=tuple(candidate.manifest_path for candidate in candidates),
        )

    def _candidates(self, document_type: str, variant: str) -> list[_Candidate]:
        candidates: list[_Candidate] = []
        for root in self.roots:
            variants = [variant] if variant == "default" else [variant, "default"]
            for candidate_variant in variants:
                package_path = root.path / document_type / candidate_variant
                manifest_path = package_path / "manifest.yaml"
                if not manifest_path.is_file():
                    continue
                manifest = self._load_manifest(manifest_path)
                declared_type = manifest.get("document_type")
                declared_variant = manifest.get("variant")
                if declared_type != document_type or declared_variant != candidate_variant:
                    raise InvalidManifestError(
                        f"Manifest identity mismatch in {manifest_path}: "
                        f"expected {document_type}/{candidate_variant}, "
                        f"got {declared_type}/{declared_variant}"
                    )
                resources = manifest.get("resources")
                if not isinstance(resources, dict):
                    raise InvalidManifestError(
                        f"Manifest resources must be a mapping: {manifest_path}"
                    )
                candidates.append(
                    _Candidate(root, package_path, candidate_variant, manifest_path, manifest)
                )
        return candidates

    @staticmethod
    def _load_manifest(path: Path) -> dict[str, Any]:
        try:
            value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise InvalidManifestError(f"Cannot read manifest {path}: {exc}") from exc
        if not isinstance(value, dict):
            raise InvalidManifestError(f"Manifest must be a mapping: {path}")
        return value

    def _resolve_resource(
        self, name: str, candidates: Iterable[_Candidate]
    ) -> ResourceSelection | None:
        for candidate in candidates:
            resources = candidate.manifest.get("resources", {})
            if not isinstance(resources, dict) or name not in resources:
                continue

            ref = resources[name]
            mode = "replace"
            path_value: str | None
            if isinstance(ref, str):
                path_value = ref
            elif isinstance(ref, dict):
                mode = str(ref.get("mode", "replace"))
                if mode == "disabled":
                    return ResourceSelection(
                        name=name,
                        scope=candidate.root.scope,
                        path=None,
                        package_path=candidate.path,
                        variant=candidate.variant,
                        mode=mode,
                        disabled=True,
                    )
                path_value = ref.get("path")
            else:
                raise InvalidManifestError(
                    f"Resource {name} in {candidate.manifest_path} must be a path or mapping"
                )

            if not path_value:
                raise InvalidManifestError(
                    f"Resource {name} in {candidate.manifest_path} has no path"
                )
            path = (candidate.path / path_value).resolve()
            if not path.is_file():
                raise InvalidResourceError(
                    f"Declared {name} resource does not exist: {path} "
                    f"(from {candidate.manifest_path})"
                )
            return ResourceSelection(
                name=name,
                scope=candidate.root.scope,
                path=path,
                package_path=candidate.path,
                variant=candidate.variant,
                mode=mode,
            )
        return None

    @staticmethod
    def _required_string(mapping: dict[str, Any], key: str, source: Path) -> str:
        value = mapping.get(key)
        if not isinstance(value, str) or not value.strip():
            raise InvalidManifestError(f"Manifest {source} requires a non-empty {key}")
        return value
