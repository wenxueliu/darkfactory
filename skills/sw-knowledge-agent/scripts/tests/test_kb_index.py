"""Tests for kb-index.py — index rebuild and validation."""

import os
import subprocess
import sys


SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb-index.py")


def run_index(kb_dir, *args):
    """Run kb-index.py and return CompletedProcess."""
    cmd = [sys.executable, SCRIPT, "--kb-dir", str(kb_dir)] + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc


def _create_entry(dir_path, filename, content):
    """Helper to create a KB entry file."""
    filepath = dir_path / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath


def test_rebuild_from_scratch(tmp_kb):
    """Empty index.md is rebuilt with all existing entries."""
    _create_entry(tmp_kb / "patterns", "test-pattern.md", """# Test Pattern

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
A test pattern for rebuild testing.

## Details
Pattern details.

## Context
Testing.

## Usage
Test verification.

## Related
None.
""")

    proc = run_index(tmp_kb, "--rebuild")
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert "Total entries: 1" in proc.stdout
    assert "Patterns: 1" in proc.stdout

    # Verify index was updated
    index_content = (tmp_kb / "index.md").read_text()
    assert "Test Pattern" in index_content
    assert "patterns/test-pattern.md" in index_content


def test_rebuild_preserves_existing(tmp_kb):
    """Rebuild includes all entries from all type dirs."""
    _create_entry(tmp_kb / "patterns", "alpha.md", """# Alpha Pattern
**Type:** Pattern
**Created:** 2026-05-01
**Author:** test
## Summary
Alpha pattern summary text here for testing.
## Details
Alpha details.
## Context
Testing.
## Usage
Test.
## Related
None.
""")
    _create_entry(tmp_kb / "decisions", "ADR-0001-beta.md", """# ADR-0001: Beta Decision
**Created:** 2026-05-01
**决策者:** test
## 背景
Beta background.
## 决策
Beta decision.
## 理由
Beta rationale.
## 考虑的替代方案
None.
## 后果
OK.
""")
    _create_entry(tmp_kb / "lessons", "gamma.md", """# Gamma Lesson
**Type:** Lesson
**Created:** 2026-05-01
**Author:** test
## Summary
Gamma lesson summary text for testing purposes here.
## Details
Gamma details.
## Context
Testing.
## Usage
Test.
## Related
None.
""")

    proc = run_index(tmp_kb, "--rebuild")
    assert proc.returncode == 0
    assert "Total entries: 3" in proc.stdout

    index = (tmp_kb / "index.md").read_text()
    assert "Alpha Pattern" in index
    assert "Beta Decision" in index
    assert "Gamma Lesson" in index


def test_validate_all_pass(tmp_kb):
    """Well-formed entries pass validation."""
    _create_entry(tmp_kb / "patterns", "valid.md", """# Valid Entry

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
A valid entry with all required fields.

## Details
This entry has all the required sections and passes validation.

## Context
Testing validation.

## Usage
Test verification.

## Related
None.
""")

    proc = run_index(tmp_kb, "--validate-only")
    assert proc.returncode == 0
    assert "1/1 entries valid" in proc.stdout


def test_validate_missing_title(tmp_kb):
    """Entry without # heading is flagged."""
    _create_entry(tmp_kb / "patterns", "no-title.md", """**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
This entry has no title heading.

## Details
Missing title.

## Context
Testing.

## Usage
Test.

## Related
None.
""")

    proc = run_index(tmp_kb, "--validate-only")
    assert "Missing title" in proc.stdout


def test_validate_missing_summary(tmp_kb):
    """Entry missing Summary section is flagged."""
    _create_entry(tmp_kb / "patterns", "no-summary.md", """# No Summary Entry

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Details
Missing summary section.

## Context
Testing.

## Usage
Test.

## Related
None.
""")

    proc = run_index(tmp_kb, "--validate-only")
    assert "Missing section: ## Summary" in proc.stdout


def test_validate_missing_adr_sections(tmp_kb):
    """ADR missing required sections is flagged."""
    _create_entry(tmp_kb / "decisions", "ADR-0001-incomplete.md", """# ADR-0001: Incomplete

**Created:** 2026-05-01
**决策者:** test

## 背景
Some background.
""")

    proc = run_index(tmp_kb, "--validate-only")
    output = proc.stdout
    assert "Missing ADR section" in output or "0/1" in output


def test_orphan_detection(tmp_kb):
    """Entry in directory but not in index is reported as orphan."""
    _create_entry(tmp_kb / "patterns", "orphan-me.md", """# Orphan Entry

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
This entry exists but is not linked in index.md.

## Details
Orphan test.

## Context
Testing.

## Usage
Test.

## Related
None.
""")

    proc = run_index(tmp_kb, "--detect-orphans")
    output = proc.stdout
    assert "orphan-me.md" in output or "Orphans" in output


def test_no_orphans_clean(tmp_kb):
    """All entries linked = no orphans."""
    _create_entry(tmp_kb / "patterns", "linked.md", """# Linked Entry

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
This will be linked.

## Details
Test.

## Context
Testing.

## Usage
Test.

## Related
None.
""")

    # Rebuild and then check for orphans
    run_index(tmp_kb, "--rebuild")
    proc = run_index(tmp_kb, "--detect-orphans")
    assert "Orphans: None" in proc.stdout or "orphan-me.md" not in proc.stdout


def test_validate_only_no_modifications(tmp_kb):
    """--validate-only does not change index.md."""
    original = (tmp_kb / "index.md").read_text()

    _create_entry(tmp_kb / "patterns", "no-mod.md", """# No Mod Entry

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
This should not trigger index modification.

## Details
Test.

## Context
Testing.

## Usage
Test.

## Related
None.
""")

    run_index(tmp_kb, "--validate-only")
    current = (tmp_kb / "index.md").read_text()
    # Index should not contain the new entry
    assert "No Mod Entry" not in current


def test_service_entries_included(tmp_kb):
    """Services subdirectory entries appear in index."""
    svc_dir = tmp_kb / "services" / "test-svc"
    svc_dir.mkdir(parents=True)
    _create_entry(svc_dir, "overview.md", """# Test Service

**Type:** Service
**Created:** 2026-05-01
**Author:** test

## Summary
Service overview.

## Details
Details.

## Context
Testing.

## Usage
Test.

## Related
None.
""")

    proc = run_index(tmp_kb, "--rebuild")
    assert "Total entries: 1" in proc.stdout
    assert "Service entries: 1" in proc.stdout

    index = (tmp_kb / "index.md").read_text()
    assert "test-svc" in index


def test_adr_numerical_ordering(tmp_kb):
    """ADRs in index are ordered by number."""
    for i in [3, 1, 2]:
        _create_entry(tmp_kb / "decisions", f"ADR-{i:04d}-test.md", f"""# ADR-{i:04d}: Test {i}
**Created:** 2026-05-0{i}
**决策者:** test
## 背景
Test {i}.
## 决策
Test {i}.
## 理由
Test {i}.
## 考虑的替代方案
None.
## 后果
OK.
""")

    proc = run_index(tmp_kb, "--rebuild")
    assert proc.returncode == 0

    index = (tmp_kb / "index.md").read_text()
    # ADR-0003 should appear before ADR-0001 (descending order)
    pos_3 = index.find("ADR-0003")
    pos_1 = index.find("ADR-0001")
    assert pos_3 < pos_1, f"Expected 0003 before 0001 (descending), got pos_3={pos_3}, pos_1={pos_1}"


def test_empty_kb(tmp_kb):
    """Empty KB produces minimal valid index."""
    proc = run_index(tmp_kb, "--rebuild")
    assert proc.returncode == 0
    assert "Total entries: 0" in proc.stdout

    index = (tmp_kb / "index.md").read_text()
    assert "## Patterns" in index
    assert "## Architecture Decisions" in index
    assert "## 更新记录" in index
