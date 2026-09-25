from pathlib import Path

import pytest

from document_contracts import DefinitionResolver, DocumentValidator, ResourceRoot


ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("skill", "document_type", "variants"),
    [
        ("sw-requirements-clarifier", "requirements", ["default", "fintech", "ecommerce", "internal-tools"]),
        ("sw-feature-designer", "feature-design", ["default"]),
        ("sw-service-designer", "service-design", ["default", "backend", "frontend", "bff", "data-pipeline"]),
        ("sw-e2e-designer", "e2e", ["default"]),
        ("sw-strategic-planner", "plan", ["default"]),
        ("sw-document-project", "project-overview", ["default"]),
        ("sw-document-project", "project-index", ["default"]),
        ("sw-document-project", "source-tree", ["default"]),
        ("sw-document-project", "deep-dive", ["default"]),
    ],
)
def test_every_builtin_definition_is_self_contained(
    skill: str, document_type: str, variants: list[str]
) -> None:
    root = ROOT / "skills" / skill / "references" / "document-definitions"
    resolver = DefinitionResolver([ResourceRoot("skill", root)])

    for variant in variants:
        definition = resolver.resolve(document_type, variant)
        result = DocumentValidator().validate_template(definition)
        assert result.passed, f"{skill}/{document_type}/{variant}: {result.findings}"
