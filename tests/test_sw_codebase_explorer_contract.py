from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sw-codebase-explorer" / "SKILL.md"
PROTOCOL = ROOT / "skills" / "sw-codebase-explorer" / "references" / "codegraph-protocol.md"
SEARCH_PATTERNS = ROOT / "skills" / "sw-codebase-explorer" / "references" / "search-patterns.md"
FAILURE_RECOVERY = ROOT / "skills" / "sw-codebase-explorer" / "references" / "failure-recovery.md"
RESULT_FORMAT = ROOT / "skills" / "sw-codebase-explorer" / "references" / "result-format.md"


def _frontmatter(text: str) -> dict:
    return yaml.safe_load(text.split("---", 2)[1])


def test_explorer_declares_codegraph_as_required_backend() -> None:
    content = SKILL.read_text(encoding="utf-8")
    frontmatter = _frontmatter(content)
    metadata = frontmatter["metadata"]

    assert metadata["version"] == "2.1.0"
    assert metadata["external_dependencies"] == [
        {
            "name": "codegraph",
            "version": ">=0.9.9",
            "type": "TOOL",
            "required": True,
            "purpose": "indexed symbol, file-structure, dependency, call-graph, and impact queries",
        }
    ]


def test_explorer_requires_index_status_and_graph_evidence() -> None:
    content = SKILL.read_text(encoding="utf-8")
    protocol = PROTOCOL.read_text(encoding="utf-8")
    result_format = RESULT_FORMAT.read_text(encoding="utf-8")

    assert "codegraph status --json {project_root}" in content
    assert "return `BLOCKED`" in content
    assert "do not silently use grep, LSP, AST" in content
    assert "codegraph status --json {project_root}" in protocol
    assert "codegraph query --json" in protocol
    assert "codegraph callers --json" in protocol
    assert "codegraph impact --json" in protocol
    assert "nodes:" in protocol
    assert "edges:" in protocol
    assert "<evidence>" in result_format
    assert "<gaps>" in result_format


def test_explorer_references_use_codegraph_query_dimensions() -> None:
    search_patterns = SEARCH_PATTERNS.read_text(encoding="utf-8")
    failure_recovery = FAILURE_RECOVERY.read_text(encoding="utf-8")

    for query in ("query", "files", "callers", "callees", "impact", "affected"):
        assert f"codegraph {query}" in search_patterns or f"`{query}`" in search_patterns
    assert "不执行 fallback" in search_patterns
    assert "不使用 grep/LSP/AST/glob 补全" in failure_recovery
    assert "codegraph init/index/sync" in failure_recovery
