"""Tests for kb-search.py — knowledge base search."""

import json
import os
import subprocess
import sys


SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb-search.py")


def run_search(kb_dir, *args):
    """Run kb-search.py and return CompletedProcess."""
    cmd = [sys.executable, SCRIPT, "--kb-dir", str(kb_dir)] + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc


def _create_entry(dir_path, filename, content):
    """Helper to create a KB entry file."""
    filepath = dir_path / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath


def test_title_match_ranking(tmp_kb):
    """Title matches rank higher than body matches."""
    _create_entry(tmp_kb / "patterns", "auth-flow.md", """# User Authentication Flow

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Authentication flow using JWT tokens.

## Details
This entry has the word "authentication" in the title.
""")

    _create_entry(tmp_kb / "lessons", "generic.md", """# Some Generic Lesson

**Type:** Lesson
**Created:** 2026-05-01
**Author:** test

## Summary
This lesson mentions authentication in the body but not the title.

## Details
Authentication is mentioned here as a secondary reference.
""")

    proc = run_search(tmp_kb, "authentication")
    assert proc.returncode == 0

    # The auth-flow pattern should appear first (higher score due to title match)
    output = proc.stdout
    auth_pos = output.find("Authentication Flow")
    lesson_pos = output.find("Generic Lesson")
    assert auth_pos < lesson_pos, f"Expected auth-flow before generic lesson, got:\n{output}"


def test_type_filter(tmp_kb):
    """--type pattern only returns pattern results."""
    _create_entry(tmp_kb / "patterns", "test-pattern.md", """# Test Pattern
**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
A test pattern entry.

## Details
Pattern details here.

## Context
Testing.

## Usage
Test verification.

## Related
None.
""")

    _create_entry(tmp_kb / "lessons", "test-lesson.md", """# Test Lesson
**Type:** Lesson
**Created:** 2026-05-01
**Author:** test

## Summary
A test lesson entry.

## Details
Lesson details here.

## Context
Testing.

## Usage
Test verification.

## Related
None.
""")

    proc = run_search(tmp_kb, "test", "-t", "pattern")
    output = proc.stdout
    assert "Test Pattern" in output
    assert "Test Lesson" not in output


def test_multiple_type_filter(tmp_kb):
    """-t pattern -t decision returns both types."""
    _create_entry(tmp_kb / "patterns", "pat.md", """# Pattern Entry
**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Pattern with unique word zebraplex.

## Details
Test.

## Context
Test.

## Usage
Test.

## Related
None.
""")
    _create_entry(tmp_kb / "decisions", "ADR-0001-dec.md", """# ADR-0001: Decision Entry
**Created:** 2026-05-01
**决策者:** test

## 背景
Decision with unique word zebraplex.

## 决策
Test.

## 理由
Test.
""")
    _create_entry(tmp_kb / "lessons", "les.md", """# Lesson Entry
**Type:** Lesson
**Created:** 2026-05-01
**Author:** test

## Summary
Lesson with unique word zebraplex.

## Details
Test.

## Context
Test.

## Usage
Test.

## Related
None.
""")

    proc = run_search(tmp_kb, "zebraplex", "-t", "pattern", "-t", "decision")
    output = proc.stdout
    assert "Pattern Entry" in output
    assert "Decision Entry" in output
    assert "Lesson Entry" not in output


def test_empty_query(tmp_kb):
    """Empty query returns error."""
    proc = run_search(tmp_kb, "")
    assert proc.returncode != 0


def test_no_results(tmp_kb):
    """Query with no matches returns empty."""
    proc = run_search(tmp_kb, "xyznonexistent12345")
    assert proc.returncode == 0
    assert "No results found" in proc.stdout or "Found 0 results" in proc.stdout


def test_json_output(tmp_kb):
    """--json flag produces valid JSON."""
    _create_entry(tmp_kb / "patterns", "json-test.md", """# JSON Test Pattern

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Testing JSON output mode.

## Details
This entry is for testing the --json flag.

## Context
Testing.

## Usage
Test verification.

## Related
None.
""")

    proc = run_search(tmp_kb, "JSON", "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "query" in data
    assert "total_results" in data
    assert "results" in data
    assert data["query"] == "JSON"
    assert len(data["results"]) >= 1


def test_json_structure(tmp_kb):
    """JSON output has correct keys."""
    _create_entry(tmp_kb / "patterns", "struct-test.md", """# Structure Test

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Testing JSON structure fields.

## Details
Check that all fields are present.

## Context
Testing.

## Usage
Test.

## Related
None.
""")

    proc = run_search(tmp_kb, "Structure", "--json")
    data = json.loads(proc.stdout)
    result = data["results"][0]
    for key in ["filename", "relative_path", "type", "title", "score", "excerpt"]:
        assert key in result, f"Missing key: {key}"


def test_score_threshold(tmp_kb):
    """--min-score filters low-scoring results."""
    _create_entry(tmp_kb / "patterns", "high-score.md", """# High Score Pattern Important Title

**Type:** Pattern
**Created:** 2026-05-04
**Author:** test

## Summary
This pattern has the word "important" repeated. important important important important.

## Details
important important important important important.

## Context
Testing score threshold.

## Usage
Test.

## Related
None.
""")
    _create_entry(tmp_kb / "patterns", "low-score.md", """# Other

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
This entry has relevant content only in the body.

## Details
Some other details.

## Context
Testing.

## Usage
Test.

## Related
None.
""")

    proc = run_search(tmp_kb, "important", "--min-score", "15")
    output = proc.stdout
    assert "High Score" in output
    assert "Other" not in output


def test_excerpt_generation(tmp_kb):
    """Excerpt contains query-relevant content."""
    _create_entry(tmp_kb / "patterns", "excerpt-test.md", """# Excerpt Test Pattern

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Testing excerpt generation.

## Details
This entry contains the special keyword "megazord" in the details section, which should be picked up by the excerpt generator.

## Context
Testing.

## Usage
Test.

## Related
None.
""")

    proc = run_search(tmp_kb, "megazord", "--json")
    data = json.loads(proc.stdout)
    result = data["results"][0]
    assert "megazord" in result["excerpt"].lower()


def test_chinese_search(tmp_kb):
    """Chinese query text matches Chinese content."""
    _create_entry(tmp_kb / "patterns", "cn-test.md", """# 用户认证流程

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
实现基于JWT的用户认证流程。

## Details
包含登录、token刷新和登出功能。

## Context
微服务架构需要统一的认证方案。

## Usage
在网关层统一处理认证。

## Related
权限管理
""")

    proc = run_search(tmp_kb, "用户认证")
    output = proc.stdout
    assert "用户认证流程" in output


def test_case_insensitive(tmp_kb):
    """Search is case-insensitive."""
    _create_entry(tmp_kb / "patterns", "case-test.md", """# Case Sensitivity Test

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Testing CASE insensitivity.

## Details
This should match regardless of case.

## Context
Test.

## Usage
Test.

## Related
None.
""")

    proc = run_search(tmp_kb, "case sensitivity")
    assert "Case Sensitivity Test" in proc.stdout

    proc2 = run_search(tmp_kb, "CASE INSENSITIVITY")
    assert "Case Sensitivity Test" in proc2.stdout


def test_search_services_dir(tmp_kb):
    """Services subdirectory is included in search results."""
    svc_dir = tmp_kb / "services" / "test-svc"
    svc_dir.mkdir(parents=True)
    _create_entry(svc_dir, "overview.md", """# Test Service Overview

**Type:** Service
**Created:** 2026-05-01
**Author:** kb-service-discovery

## Summary
A test service with a unique word "flurbozan".

## Details
Service details.
""")

    proc = run_search(tmp_kb, "flurbozan")
    assert "Test Service Overview" in proc.stdout
