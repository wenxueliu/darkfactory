from pathlib import Path

import pytest

from document_contracts import DefinitionResolver, DocumentValidator, ResourceRoot
from document_contracts.errors import InvalidResourceError


def _write_package(root: Path, document_type: str, variant: str, manifest: str, **files: str) -> None:
    package = root / document_type / variant
    package.mkdir(parents=True)
    (package / "manifest.yaml").write_text(manifest, encoding="utf-8")
    for name, content in files.items():
        (package / name).write_text(content, encoding="utf-8")


def test_resolves_each_resource_from_project_user_and_builtin_layers(tmp_path: Path) -> None:
    project = tmp_path / "project"
    user = tmp_path / "user"
    builtin = tmp_path / "builtin"

    _write_package(
        project,
        "requirements",
        "fintech",
        """
document_type: requirements
variant: fintech
contract: sw.requirements
version: '1.0'
resources:
  template: template.md
""",
        **{"template.md": "project template"},
    )
    _write_package(
        user,
        "requirements",
        "default",
        """
document_type: requirements
variant: default
contract: sw.requirements
version: '1.0'
resources:
  validator: validator.yaml
""",
        **{"validator.yaml": "rules: []\n"},
    )
    _write_package(
        builtin,
        "requirements",
        "default",
        """
document_type: requirements
variant: default
contract: sw.requirements
version: '1.0'
resources:
  template: template.md
  gate: gate.yaml
""",
        **{"template.md": "builtin template", "gate.yaml": "rules: []\n"},
    )

    definition = DefinitionResolver(
        [
            ResourceRoot("project", project),
            ResourceRoot("user", user),
            ResourceRoot("skill", builtin),
        ]
    ).resolve("requirements", "fintech")

    assert definition.resource("template").scope == "project"
    assert definition.resource("validator").scope == "user"
    assert definition.resource("gate").scope == "skill"


def test_project_default_resource_beats_user_variant_resource(tmp_path: Path) -> None:
    project = tmp_path / "project"
    user = tmp_path / "user"

    _write_package(
        project,
        "requirements",
        "default",
        """
document_type: requirements
variant: default
contract: sw.requirements
version: '1.0'
resources:
  template: template.md
""",
        **{"template.md": "project default"},
    )
    _write_package(
        user,
        "requirements",
        "fintech",
        """
document_type: requirements
variant: fintech
contract: sw.requirements
version: '1.0'
resources:
  template: template.md
""",
        **{"template.md": "user fintech"},
    )

    definition = DefinitionResolver(
        [ResourceRoot("project", project), ResourceRoot("user", user)]
    ).resolve("requirements", "fintech")

    assert definition.resource("template").path.read_text(encoding="utf-8") == "project default"


def test_disabled_resource_stops_fallback(tmp_path: Path) -> None:
    project = tmp_path / "project"
    builtin = tmp_path / "builtin"
    _write_package(
        project,
        "requirements",
        "default",
        """
document_type: requirements
variant: default
contract: sw.requirements
version: '1.0'
resources:
  template: template.md
  gate:
    mode: disabled
""",
        **{"template.md": "template"},
    )
    _write_package(
        builtin,
        "requirements",
        "default",
        """
document_type: requirements
variant: default
contract: sw.requirements
version: '1.0'
resources:
  gate: gate.yaml
""",
        **{"gate.yaml": "rules: []\n"},
    )

    definition = DefinitionResolver(
        [ResourceRoot("project", project), ResourceRoot("skill", builtin)]
    ).resolve("requirements")

    assert definition.resource("gate").disabled is True
    assert definition.resource("gate").path is None


def test_declared_but_missing_custom_resource_fails_instead_of_falling_back(tmp_path: Path) -> None:
    project = tmp_path / "project"
    builtin = tmp_path / "builtin"
    _write_package(
        project,
        "requirements",
        "default",
        """
document_type: requirements
variant: default
contract: sw.requirements
version: '1.0'
resources:
  template: missing.md
""",
    )
    _write_package(
        builtin,
        "requirements",
        "default",
        """
document_type: requirements
variant: default
contract: sw.requirements
version: '1.0'
resources:
  template: template.md
""",
        **{"template.md": "builtin"},
    )

    with pytest.raises(InvalidResourceError):
        DefinitionResolver(
            [ResourceRoot("project", project), ResourceRoot("skill", builtin)]
        ).resolve("requirements")


def test_validator_supports_stable_section_ids_and_frontmatter(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _write_package(
        root,
        "requirements",
        "default",
        """
document_type: requirements
variant: default
contract: sw.requirements
version: '1.0'
resources:
  template: template.md
  validator: validator.yaml
""",
        **{
            "template.md": "template",
            "validator.yaml": """
rules:
  - id: frontmatter
    type: required_frontmatter
    fields: [document_id]
  - id: sections
    type: required_sections
    sections:
      - id: acceptance_criteria
  - id: content
    type: non_empty_sections
    sections:
      - id: acceptance_criteria
"""
        },
    )
    definition = DefinitionResolver([ResourceRoot("project", root)]).resolve("requirements")

    result = DocumentValidator().validate(
        definition,
        """
---
document_type: requirements
contract: sw.requirements
contract_version: "1.0"
document_id: REQ-001
---

<!-- section-id: acceptance_criteria -->
## 成功条件

- 用户可以完成任务
""",
    )

    assert result.passed
    assert result.findings == ()


def test_validator_does_not_infer_section_ids_from_headings(tmp_path: Path) -> None:
    root = tmp_path / "root"
    _write_package(
        root,
        "requirements",
        "default",
        """
document_type: requirements
variant: default
contract: sw.requirements
version: '1.0'
resources:
  template: template.md
  validator: validator.yaml
""",
        **{
            "template.md": "template",
            "validator.yaml": """
rules:
  - id: sections
    type: required_sections
    sections:
      - id: acceptance_criteria
""",
        },
    )
    definition = DefinitionResolver([ResourceRoot("project", root)]).resolve("requirements")

    result = DocumentValidator().validate(
        definition,
        """
---
document_type: requirements
contract: sw.requirements
contract_version: "1.0"
---

## acceptance_criteria
The heading is presentation only and is not a stable section marker.
""",
    )

    assert not result.passed
    assert "acceptance_criteria" in result.findings[0].message


def test_builtin_requirements_definition_is_resolvable() -> None:
    root = Path("skills/sw-requirements-clarifier/references/document-definitions")
    definition = DefinitionResolver([ResourceRoot("skill", root)]).resolve(
        "requirements", "fintech"
    )

    assert definition.contract == "sw.requirements"
    assert definition.resource("template").path.name == "requirements-spec-template-fintech.md"
    assert definition.resource("gate").path.name == "gate.yaml"
