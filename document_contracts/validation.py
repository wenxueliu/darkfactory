"""Markdown parsing and declarative document validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from .errors import InvalidResourceError
from .models import DocumentDefinition, Finding, ValidationResult


_FRONTMATTER = re.compile(r"\A[ \t\r\n]*---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
_SECTION_MARKER = re.compile(r"<!--\s*section-id:\s*([A-Za-z0-9_.-]+)\s*-->")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Section:
    identifier: str
    title: str
    content: str
    explicit: bool


@dataclass(frozen=True)
class ParsedMarkdown:
    frontmatter: dict[str, Any]
    sections: tuple[Section, ...]
    raw: str

    def find_section(self, spec: Any) -> Section | None:
        if isinstance(spec, str):
            wanted_id = spec
        elif isinstance(spec, dict):
            wanted_id = str(spec.get("id", ""))
        else:
            return None

        wanted = _normalise(wanted_id)
        for section in self.sections:
            if wanted == _normalise(section.identifier):
                return section
        return None


def parse_markdown(text: str) -> ParsedMarkdown:
    frontmatter: dict[str, Any] = {}
    body = text
    match = _FRONTMATTER.match(text)
    if match:
        loaded = yaml.safe_load(match.group(1)) or {}
        if not isinstance(loaded, dict):
            raise ValueError("Markdown frontmatter must be a mapping")
        frontmatter = loaded
        body = text[match.end() :]

    markers = list(_SECTION_MARKER.finditer(body))
    sections: list[Section] = []
    if markers:
        for index, marker in enumerate(markers):
            end = markers[index + 1].start() if index + 1 < len(markers) else len(body)
            content = body[marker.end() : end].strip()
            title_match = _HEADING.search(content)
            title = title_match.group(2).strip() if title_match else marker.group(1)
            sections.append(Section(marker.group(1), title, content, explicit=True))
    # Stable section IDs are mandatory. Headings remain presentation only.
    return ParsedMarkdown(frontmatter, tuple(sections), text)


class DocumentValidator:
    """Run validator and gate rules declared by a resolved definition."""

    def validate(
        self,
        definition: DocumentDefinition,
        document: str | Path,
        *,
        include_gate: bool = True,
    ) -> ValidationResult:
        text = Path(document).read_text(encoding="utf-8") if isinstance(document, Path) else document
        parsed = parse_markdown(text)
        findings: list[Finding] = []
        self._validate_identity(definition, parsed, findings)
        validator_source = self._run_resource(
            definition, "validator", parsed, findings, default_severity="error"
        )
        gate_source = (
            self._run_resource(definition, "gate", parsed, findings, default_severity="error")
            if include_gate
            else None
        )
        return ValidationResult(tuple(findings), validator_source, gate_source)

    def validate_template(self, definition: DocumentDefinition) -> ValidationResult:
        """Validate a definition template against its declared structure."""
        selection = definition.resource("template")
        if selection is None or selection.disabled or selection.path is None:
            raise InvalidResourceError(
                f"Definition has no usable template: {definition.document_type}/{definition.variant}"
            )
        parsed = parse_markdown(selection.path.read_text(encoding="utf-8"))
        findings: list[Finding] = []
        self._validate_identity(definition, parsed, findings)
        for name in ("validator", "gate"):
            self._run_resource(
                definition,
                name,
                parsed,
                findings,
                default_severity="error",
                structural_only=True,
            )
        return ValidationResult(
            tuple(findings),
            self._resource_path(definition, "validator"),
            self._resource_path(definition, "gate"),
        )

    @staticmethod
    def _resource_path(definition: DocumentDefinition, name: str) -> Path | None:
        selection = definition.resource(name)
        if selection is None or selection.disabled:
            return None
        return selection.path

    @staticmethod
    def _validate_identity(
        definition: DocumentDefinition,
        document: ParsedMarkdown,
        findings: list[Finding],
    ) -> None:
        expected = {
            "document_type": definition.document_type,
            "contract": definition.contract,
            "contract_version": definition.version,
        }
        for field, value in expected.items():
            actual = document.frontmatter.get(field)
            if actual is None:
                findings.append(
                    Finding("document.identity.required", "error", f"Missing document identity field: {field}")
                )
            elif str(actual) != str(value):
                findings.append(
                    Finding(
                        "document.identity.mismatch",
                        "error",
                        f"Document identity mismatch for {field}: expected {value}, got {actual}",
                    )
                )

    def _run_resource(
        self,
        definition: DocumentDefinition,
        name: str,
        document: ParsedMarkdown,
        findings: list[Finding],
        default_severity: str,
        structural_only: bool = False,
    ) -> Path | None:
        selection = definition.resource(name)
        if selection is None or selection.disabled:
            return None
        if selection.path is None:
            return None
        if selection.path.suffix.lower() not in {".yaml", ".yml"}:
            findings.append(
                Finding(
                    f"{name}.unsupported_format",
                    "warning",
                    f"{name} resource is not executable YAML; it was not evaluated: {selection.path}",
                    str(selection.path),
                )
            )
            return selection.path

        try:
            config = yaml.safe_load(selection.path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise InvalidResourceError(f"Cannot read {name} resource {selection.path}: {exc}") from exc
        rules = config.get("rules", []) if isinstance(config, dict) else []
        if not isinstance(rules, list):
            raise InvalidResourceError(f"{name} rules must be a list: {selection.path}")
        for rule in rules:
            if structural_only:
                if not isinstance(rule, dict):
                    raise InvalidResourceError(f"Rules must be mappings: {selection.path}")
                if rule.get("type") != "required_sections":
                    continue
            self._run_rule(rule, document, findings, default_severity, selection.path)
        return selection.path

    def _run_rule(
        self,
        rule: Any,
        document: ParsedMarkdown,
        findings: list[Finding],
        default_severity: str,
        source: Path,
    ) -> None:
        if not isinstance(rule, dict):
            raise InvalidResourceError(f"Rules must be mappings: {source}")
        rule_id = str(rule.get("id", "unnamed-rule"))
        severity = str(rule.get("severity", default_severity))
        rule_type = rule.get("type")

        if rule_type == "required_frontmatter":
            missing = [
                str(field)
                for field in rule.get("fields", [])
                if field not in document.frontmatter or document.frontmatter[field] in (None, "")
            ]
            if missing:
                findings.append(
                    Finding(rule_id, severity, f"Missing required frontmatter: {', '.join(missing)}", str(source))
                )
            return

        if rule_type == "required_sections":
            missing = [spec for spec in rule.get("sections", []) if document.find_section(spec) is None]
            if missing:
                labels = [spec if isinstance(spec, str) else spec.get("id", "unknown") for spec in missing]
                findings.append(
                    Finding(rule_id, severity, f"Missing required sections: {', '.join(labels)}", str(source))
                )
            return

        if rule_type == "non_empty_sections":
            empty = [
                spec
                for spec in rule.get("sections", [])
                if (section := document.find_section(spec)) is None or not section.content.strip()
            ]
            if empty:
                labels = [spec if isinstance(spec, str) else spec.get("id", "unknown") for spec in empty]
                findings.append(
                    Finding(rule_id, severity, f"Empty required sections: {', '.join(labels)}", str(source))
                )
            return

        if rule_type == "min_section_length":
            minimum = int(rule.get("minimum", 0))
            too_short: list[str] = []
            for spec in rule.get("sections", []):
                section = document.find_section(spec)
                if section is None:
                    continue
                if len(section.content.strip()) < minimum:
                    label = spec if isinstance(spec, str) else spec.get("id", "unknown")
                    too_short.append(f"{label} ({len(section.content.strip())} chars)")
            if too_short:
                findings.append(
                    Finding(
                        rule_id,
                        severity,
                        f"Sections shorter than {minimum} characters: {', '.join(too_short)}",
                        str(source),
                    )
                )
            return

        if rule_type == "contains":
            pattern = str(rule.get("pattern", ""))
            target = document.raw if rule.get("target", "document") == "document" else "\n".join(
                section.content for section in document.sections
            )
            if not re.search(pattern, target, re.MULTILINE):
                findings.append(
                    Finding(rule_id, severity, f"Required pattern not found: {pattern}", str(source))
                )
            return

        if rule_type == "no_placeholders":
            pattern = str(rule.get("pattern", r"\{[^{}\n]+\}"))
            matches = re.findall(pattern, document.raw)
            if matches:
                findings.append(
                    Finding(rule_id, severity, f"Unresolved placeholders found: {', '.join(matches[:5])}", str(source))
                )
            return

        raise InvalidResourceError(f"Unsupported rule type {rule_type!r} in {source}")


def _normalise(value: str) -> str:
    return value.strip().lower()
