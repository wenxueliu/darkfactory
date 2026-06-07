"""Tests for hooks/ideation-gate.py — ideation enforcement logic.

Run with:
    cd /home/chengnanfeng/code/harness/services/multiagents/hooks
    python3 -m pytest tests/test_ideation_gate.py -v
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Load ideation-gate.py as a module (file has hyphen, not importable directly)
HOOKS_DIR = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "ideation_gate", HOOKS_DIR / "ideation-gate.py"
)
ideation_gate = importlib.util.module_from_spec(_spec)
sys.modules["ideation_gate"] = ideation_gate
_spec.loader.exec_module(ideation_gate)


# --- parse_yaml_ideation_status tests ---

def test_parse_missing_tracker():
    with tempfile.TemporaryDirectory() as tmp:
        is_done, rid, errors = ideation_gate.parse_yaml_ideation_status(
            os.path.join(tmp, "nope.yaml")
        )
        assert is_done is False
        assert rid is None
        assert any("not found" in e for e in errors)


def test_parse_malformed_yaml():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "tracker.yaml"
        p.write_text("this: is: not: valid: yaml: ::", encoding="utf-8")
        is_done, rid, errors = ideation_gate.parse_yaml_ideation_status(str(p))
        assert is_done is False
        assert any("YAML" in e for e in errors)


def test_parse_done_with_requirements_list():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "tracker.yaml"
        p.write_text("""
requirements:
  - id: REQ-001
    phases:
      ideation:
        status: done
  - id: REQ-002
    phases:
      ideation:
        status: in_progress
""", encoding="utf-8")
        is_done, rid, errors = ideation_gate.parse_yaml_ideation_status(str(p))
        assert is_done is True
        assert rid == "REQ-001"
        assert errors == []


def test_parse_not_done():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "tracker.yaml"
        p.write_text("""
requirements:
  - id: REQ-003
    phases:
      ideation:
        status: in_progress
""", encoding="utf-8")
        is_done, rid, errors = ideation_gate.parse_yaml_ideation_status(str(p))
        assert is_done is False
        assert rid == "REQ-003"
        assert errors == []


def test_parse_singleton_schema():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "tracker.yaml"
        p.write_text("""
id: REQ-007
phases:
  ideation:
    status: done
""", encoding="utf-8")
        is_done, rid, errors = ideation_gate.parse_yaml_ideation_status(str(p))
        assert is_done is True
        assert rid == "REQ-007"


def test_parse_flat_dict_schema():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "tracker.yaml"
        p.write_text("""
REQ-010:
  phases:
    ideation:
      status: done
""", encoding="utf-8")
        is_done, rid, errors = ideation_gate.parse_yaml_ideation_status(str(p))
        assert is_done is True
        assert rid == "REQ-010"


# --- validate_spec_content tests ---

def _write_valid_spec(project_root, req_id="REQ-100"):
    spec_dir = Path(project_root) / "_context" / "memory" / "sw-shared" / "requirements"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec = spec_dir / f"{req_id}.md"
    spec.write_text(f"""# {req_id} Test Spec

## 问题陈述

This is a sufficiently long problem statement that explains the issue in
detail with concrete measurable signals and the affected user population.

## 用户故事

As a user I want to do X so that Y is achieved, and this provides business
value because of the following reason that we are documenting.

## 验收标准

- AC1: Given X, when Y, then Z measurable result with specific threshold
- AC2: Given error condition, when handled, then specific error returned
- AC3: Performance: response < 200ms under 100 RPS concurrent load

## 非功能需求

Security: HTTPS only, JWT auth, no PII in logs.
Performance: < 200ms P99 latency, supports 1000 RPS.
Availability: 99.9% uptime SLA.

## 约束

- Must work on Linux/macOS/Windows
- Python 3.11+
- No new external services

## 风险与假设

- Risk 1: Database migration could fail; mitigation: feature flag + rollback
- Risk 2: Performance regression; mitigation: load test before merge
- Assumption 1: User has modern browser
- Assumption 2: Auth provider is reliable
- Assumption 3: Network is stable
""", encoding="utf-8")
    return spec


def test_validate_spec_valid():
    with tempfile.TemporaryDirectory() as tmp:
        _write_valid_spec(tmp)
        errors = ideation_gate.validate_spec_content(tmp, "REQ-100")
        assert errors == []


def test_validate_spec_missing_file():
    with tempfile.TemporaryDirectory() as tmp:
        errors = ideation_gate.validate_spec_content(tmp, "REQ-MISSING")
        assert any("Spec file not found" in e for e in errors)


def test_validate_spec_missing_sections():
    with tempfile.TemporaryDirectory() as tmp:
        spec_dir = Path(tmp) / "_context" / "memory" / "sw-shared" / "requirements"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "REQ-X.md").write_text("""
# Partial spec
## 问题陈述
This is a long enough problem statement that passes the 50 char threshold.
""", encoding="utf-8")
        errors = ideation_gate.validate_spec_content(tmp, "REQ-X")
        assert any("missing mandatory sections" in e for e in errors)


def test_validate_spec_too_short_section():
    with tempfile.TemporaryDirectory() as tmp:
        spec_dir = Path(tmp) / "_context" / "memory" / "sw-shared" / "requirements"
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "REQ-Y.md").write_text("""
# Spec
## 问题陈述
Long enough problem statement that passes the 50 char threshold easily.
## 用户故事
Short
## 验收标准
""", encoding="utf-8")
        errors = ideation_gate.validate_spec_content(tmp, "REQ-Y")
        assert any("too-short" in e for e in errors)


# --- check_ideation_completed (full integration) ---

def test_check_done_with_valid_spec():
    with tempfile.TemporaryDirectory() as tmp:
        _write_valid_spec(tmp, "REQ-DONE")
        # Write tracker
        (Path(tmp) / "_context" / "memory" / "sw-shared").mkdir(parents=True, exist_ok=True)
        (Path(tmp) / "_context" / "memory" / "sw-shared" / "requirements-tracker.yaml").write_text("""
requirements:
  - id: REQ-DONE
    phases:
      ideation:
        status: done
""", encoding="utf-8")
        is_done, errors, rid = ideation_gate.check_ideation_completed(tmp)
        assert is_done is True
        assert errors == []
        assert rid == "REQ-DONE"


def test_check_done_but_spec_missing():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "_context" / "memory" / "sw-shared").mkdir(parents=True, exist_ok=True)
        (Path(tmp) / "_context" / "memory" / "sw-shared" / "requirements-tracker.yaml").write_text("""
requirements:
  - id: REQ-NOSPEC
    phases:
      ideation:
        status: done
""", encoding="utf-8")
        is_done, errors, rid = ideation_gate.check_ideation_completed(tmp)
        assert is_done is False
        assert rid == "REQ-NOSPEC"
        assert any("Spec file not found" in e for e in errors)


def test_check_not_done():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "_context" / "memory" / "sw-shared").mkdir(parents=True, exist_ok=True)
        (Path(tmp) / "_context" / "memory" / "sw-shared" / "requirements-tracker.yaml").write_text("""
requirements:
  - id: REQ-WIP
    phases:
      ideation:
        status: in_progress
""", encoding="utf-8")
        is_done, errors, _ = ideation_gate.check_ideation_completed(tmp)
        assert is_done is False


# --- is_source_code_file tests ---

def test_is_source_code_file_python():
    assert ideation_gate.is_source_code_file("/foo/bar.py") is True


def test_is_source_code_file_test_exempt():
    assert ideation_gate.is_source_code_file("/foo/test_bar.py") is False
    assert ideation_gate.is_source_code_file("/foo/test_foo.py") is False


def test_is_source_code_file_md_exempt():
    assert ideation_gate.is_source_code_file("/foo/notes.md") is False


def test_is_source_code_file_yaml_exempt():
    assert ideation_gate.is_source_code_file("/foo/config.yaml") is False


def test_is_source_code_file_javascript():
    assert ideation_gate.is_source_code_file("/foo/app.tsx") is True


# --- is_implementation_agent tests ---

def test_is_implementation_agent_tdd():
    assert ideation_gate.is_implementation_agent({
        "subagent_type": "sw-tdd-agent",
        "description": "implement feature"
    }) is True


def test_is_implementation_agent_explorer():
    assert ideation_gate.is_implementation_agent({
        "subagent_type": "sw-codebase-explorer",
        "description": "find usages"
    }) is False


def test_is_implementation_agent_via_description():
    assert ideation_gate.is_implementation_agent({
        "description": "delegate to sw-plan-executor for fan-out"
    }) is True
