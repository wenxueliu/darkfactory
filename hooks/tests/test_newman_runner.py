"""Tests for sw-integration-tester/scripts/newman_runner.py — newman orchestration.

Run with:
    cd /home/chengnanfeng/code/harness/services/multiagents
    python3 -m pytest hooks/tests/test_newman_runner.py -v
"""
import importlib.util
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent / "skills" / "sw-integration-tester" / "scripts"
_spec = importlib.util.spec_from_file_location("newman_runner", SCRIPT_DIR / "newman_runner.py")
nr = importlib.util.module_from_spec(_spec)
sys.modules["newman_runner"] = nr
_spec.loader.exec_module(nr)


# --- detect_project_root ---

def test_detect_project_root_with_context(tmp_path, monkeypatch):
    (tmp_path / "_context").mkdir()
    root = nr.detect_project_root(str(tmp_path))
    assert root.resolve() == tmp_path.resolve()


def test_detect_project_root_no_markers(tmp_path, monkeypatch):
    root = nr.detect_project_root(str(tmp_path))
    # It may discover an enclosing repository marker (for example /tmp/.git
    # in the managed test environment), but must return an ancestor.
    assert root.resolve() in (tmp_path.resolve(), *tmp_path.resolve().parents)


# --- resolve_paths ---

def test_resolve_paths(tmp_path):
    paths = nr.resolve_paths("REQ-001", tmp_path, "user-service")
    assert str(paths["collection"]).endswith(
        "knowledge/designs/REQ-001/services/user-service/tests/collection.json"
    )
    assert str(paths["env"]).endswith(
        "knowledge/designs/REQ-001/services/user-service/tests/environment.json"
    )
    assert str(paths["data"]).endswith(
        "knowledge/designs/REQ-001/services/user-service/tests/data.json"
    )
    assert str(paths["report"]).endswith(
        "knowledge/designs/REQ-001/services/user-service/tests/report.xml"
    )
    assert str(paths["results_yaml"]).endswith(
        "knowledge/requirements/REQ-001/test-results.yaml"
    )


def test_resolve_all_paths_reads_manifest(tmp_path):
    manifest_dir = tmp_path / "knowledge" / "designs" / "REQ-001"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.yaml").write_text(
        """api_test_artifacts:
  - service_id: user-service
    collection: services/user-service/tests/collection.json
    environment: services/user-service/tests/environment.json
    data: NOT_CREATED
    report: services/user-service/tests/report.xml
""",
        encoding="utf-8",
    )
    paths, err = nr.resolve_all_paths("REQ-001", tmp_path)
    assert err == ""
    assert len(paths) == 1
    assert paths[0]["service_id"] == "user-service"
    assert paths[0]["data"].name == "data.json"


# --- pre_check ---

def test_pre_check_missing_collection(tmp_path):
    paths = {
        "collection": tmp_path / "missing.json",
        "env": tmp_path / "env.json",
    }
    ok, err = nr.pre_check(paths)
    assert ok is False
    assert "Collection not found" in err
    assert "service-designer" in err


def test_pre_check_missing_env(tmp_path):
    paths = {
        "collection": tmp_path / "coll.json",
        "env": tmp_path / "missing-env.json",
    }
    paths["collection"].touch()
    ok, err = nr.pre_check(paths)
    assert ok is False
    assert "Environment file not found" in err


def test_pre_check_both_present(tmp_path):
    paths = {
        "collection": tmp_path / "coll.json",
        "env": tmp_path / "env.json",
    }
    paths["collection"].touch()
    paths["env"].touch()
    ok, err = nr.pre_check(paths)
    assert ok is True
    assert err == ""


# --- parse_junit_xml ---

def _write_junit(path: Path, total: int, failures: int, errors: int, skipped: int = 0):
    """Build a minimal JUnit XML that matches newman's structure."""
    fail_xml = ""
    for i in range(failures):
        fail_xml += f'<testcase name="tc-fail-{i}" classname="TestSuite">'
        fail_xml += f'<failure type="AssertionFailure" message="Expected 200 got 500">assertion at line {i}</failure>'
        fail_xml += '</testcase>'
    err_xml = ""
    for i in range(errors):
        err_xml += f'<testcase name="tc-err-{i}" classname="TestSuite">'
        err_xml += f'<error type="RuntimeError" message="Connection refused">stack trace here</error>'
        err_xml += '</testcase>'
    pass_xml = ""
    pass_count = total - failures - errors - skipped
    for i in range(pass_count):
        pass_xml += f'<testcase name="tc-pass-{i}" classname="TestSuite"></testcase>'
    skip_xml = ""
    for i in range(skipped):
        skip_xml += f'<testcase name="tc-skip-{i}" classname="TestSuite"><skipped/></testcase>'

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuices>
  <testsuite name="NewmanTests" tests="{total}" failures="{failures}" errors="{errors}" skipped="{skipped}">
    {pass_xml}{fail_xml}{err_xml}{skip_xml}
  </testsuite>
</testsuices>
"""
    # Note: testsuites (typo'd to be like real newman output is "testsuites" not "testsuices" — fix below)
    content = content.replace("testsuices", "testsuites")
    path.write_text(content, encoding="utf-8")


def test_parse_junit_all_pass(tmp_path):
    report = tmp_path / "report.xml"
    _write_junit(report, total=5, failures=0, errors=0)
    summary = nr.parse_junit_xml(report)
    assert summary["total"] == 5
    assert summary["passed"] == 5
    assert summary["failed"] == 0
    assert summary["errored"] == 0
    assert summary["failures"] == []


def test_parse_junit_with_failures(tmp_path):
    report = tmp_path / "report.xml"
    _write_junit(report, total=5, failures=2, errors=0)
    summary = nr.parse_junit_xml(report)
    assert summary["total"] == 5
    assert summary["passed"] == 3
    assert summary["failed"] == 2
    assert len(summary["failures"]) == 2


def test_parse_junit_with_errors(tmp_path):
    report = tmp_path / "report.xml"
    _write_junit(report, total=4, failures=0, errors=1, skipped=1)
    summary = nr.parse_junit_xml(report)
    assert summary["total"] == 4
    assert summary["passed"] == 2
    assert summary["errored"] == 1
    assert summary["skipped"] == 1
    # Error is captured in failures list
    assert len(summary["failures"]) == 1
    assert summary["failures"][0]["type"] == "error"


def test_parse_junit_missing_file(tmp_path):
    summary = nr.parse_junit_xml(tmp_path / "missing.xml")
    assert "parse_error" in summary


def test_parse_junit_malformed(tmp_path):
    report = tmp_path / "report.xml"
    report.write_text("not <valid> xml at all", encoding="utf-8")
    summary = nr.parse_junit_xml(report)
    assert "parse_error" in summary


# --- append_to_test_results_yaml ---

def test_append_creates_file(tmp_path):
    paths = {"results_yaml": tmp_path / "test-results.yaml"}
    summary = {
        "total": 5, "passed": 5, "failed": 0, "errored": 0, "skipped": 0,
        "newman_exit_code": 0, "status": "PASS",
    }
    ok, err = nr.append_to_test_results_yaml(paths, "REQ-100", summary)
    assert ok is True
    assert err == ""
    content = paths["results_yaml"].read_text(encoding="utf-8")
    assert "api_tests:" in content
    assert "REQ-100" in content
    assert "status: PASS" in content


def test_append_is_idempotent(tmp_path):
    paths = {"results_yaml": tmp_path / "test-results.yaml"}
    summary = {
        "total": 5, "passed": 5, "failed": 0, "errored": 0, "skipped": 0,
        "newman_exit_code": 0, "status": "PASS",
    }
    nr.append_to_test_results_yaml(paths, "REQ-100", summary)
    summary["failed"] = 1
    summary["status"] = "FAIL"
    nr.append_to_test_results_yaml(paths, "REQ-100", summary)
    content = paths["results_yaml"].read_text(encoding="utf-8")
    # Should only appear once (replacement, not duplication)
    assert content.count("requirement_id: REQ-100") == 1
    assert "status: FAIL" in content
    assert "status: PASS" not in content


def test_append_preserves_existing_sections(tmp_path):
    paths = {"results_yaml": tmp_path / "test-results.yaml"}
    paths["results_yaml"].write_text("""# Existing results
integration_tests:
  - id: IT-1
    result: PASS
""", encoding="utf-8")
    summary = {
        "total": 1, "passed": 1, "failed": 0, "errored": 0, "skipped": 0,
        "newman_exit_code": 0, "status": "PASS",
    }
    nr.append_to_test_results_yaml(paths, "REQ-200", summary)
    content = paths["results_yaml"].read_text(encoding="utf-8")
    assert "integration_tests:" in content
    assert "api_tests:" in content
    assert "REQ-200" in content


# --- main() exit code logic ---

def test_main_precheck_failure_exits_2(tmp_path, capsys, monkeypatch):
    # Create project root with .git but no test files
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "newman_runner.py",
        "--requirement-id", "REQ-MISSING",
        "--project-root", str(tmp_path),
        "--json",
    ])
    rc = nr.main()
    captured = capsys.readouterr()
    assert rc == 2
    assert "PRECHECK_FAILED" in captured.out


def test_main_newman_missing_exits_3(tmp_path, capsys, monkeypatch):
    # Create files but no newman binary
    (tmp_path / ".git").mkdir()
    tests_dir = tmp_path / "knowledge" / "designs" / "R1" / "services" / "user-service" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "collection.json").touch()
    (tests_dir / "environment.json").touch()
    (tmp_path / "knowledge" / "designs" / "R1" / "manifest.yaml").write_text(
        """api_test_artifacts:
  - service_id: user-service
    collection: services/user-service/tests/collection.json
    environment: services/user-service/tests/environment.json
""",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", [
        "newman_runner.py",
        "--requirement-id", "R1",
        "--project-root", str(tmp_path),
        "--json",
    ])
    # Force shutil.which to return None
    with patch("shutil.which", return_value=None):
        rc = nr.main()
    captured = capsys.readouterr()
    assert rc == 3
    assert "NEWMAN_MISSING" in captured.out
