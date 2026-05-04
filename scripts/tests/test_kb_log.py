"""Tests for kb-log.py — knowledge entry writer."""

import json
import os
import subprocess
import sys


SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb-log.py")


def run_log(kb_dir, *args, stdin_text=None):
    """Run kb-log.py and return CompletedProcess."""
    cmd = [sys.executable, SCRIPT, "--kb-dir", str(kb_dir)] + list(args)
    proc = subprocess.run(
        cmd, capture_output=True, text=True,
        input=stdin_text,
    )
    return proc


def test_create_pattern(tmp_kb):
    """Create a pattern entry and verify it exists."""
    proc = run_log(tmp_kb, "pattern", "Circuit Breaker", "--stdin", stdin_text="""## Summary
A resilience pattern that prevents cascading failures.

## Details
Open circuit after N failures, half-open for probing.

## Context
Microservice architecture needs resilience patterns.

## Usage
Wrap external service calls with circuit breaker.

## Related
Retry Pattern, Bulkhead Pattern
""")
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert "Created pattern" in proc.stdout

    # Verify file exists
    entry_path = tmp_kb / "patterns" / "Circuit-Breaker.md"
    assert entry_path.exists()
    content = entry_path.read_text()
    assert "# Circuit Breaker" in content
    assert "**Type:** Pattern" in content
    assert "## Summary" in content


def test_create_decision_adr(tmp_kb):
    """Create an ADR and verify auto-increment numbering."""
    proc = run_log(tmp_kb, "decision", "Use JWT for Authentication", "--stdin",
                   "--status", "accepted", stdin_text="""## 背景
Need a stateless authentication mechanism.

## 决策
Use JWT tokens with RS256 signing.

## 理由
Stateless, widely supported, enables horizontal scaling.

## 考虑的替代方案
Session-based auth: simpler but stateful.
OAuth2 only: more complex than needed.

## 后果
Added key rotation operational burden.
""")
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert "Created ADR-0001" in proc.stdout

    # Verify file exists with correct naming
    decisions_dir = tmp_kb / "decisions"
    files = list(decisions_dir.glob("ADR-0001-*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "ADR-0001: Use JWT for Authentication" in content
    assert "**状态:** `accepted`" in content


def test_create_decision_sequential_numbers(tmp_kb):
    """Create 3 decisions and verify 0001, 0002, 0003 numbering."""
    for i, title in enumerate(["Decision Alpha", "Decision Beta", "Decision Gamma"], 1):
        proc = run_log(tmp_kb, "decision", title, "--stdin", "--status", "proposed", stdin_text=f"""## 背景
Test decision {i}.

## 决策
Do something {i}.

## 理由
Reasons for decision {i}.

## 考虑的替代方案
None.

## 后果
Consequences of decision {i}.
""")
        assert proc.returncode == 0, f"Decision {i} failed: {proc.stderr}"
        assert f"ADR-{i:04d}" in proc.stdout

    decisions_dir = tmp_kb / "decisions"
    for i in range(1, 4):
        assert any(decisions_dir.glob(f"ADR-{i:04d}-*.md"))


def test_create_lesson(tmp_kb):
    """Create a lesson entry."""
    proc = run_log(tmp_kb, "lesson", "Null Pointer Incident", "--stdin", stdin_text="""## Summary
Deployed without null check on user profile.

## Details
The user profile endpoint crashed when user had no avatar.

## Context
Happened during peak traffic after a deploy.

## Usage
Always add null checks before accessing nested objects.

## Related
Input Validation Pattern
""")
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    assert "Created lesson" in proc.stdout

    lessons_dir = tmp_kb / "lessons"
    entry = lessons_dir / "Null-Pointer-Incident.md"
    assert entry.exists()


def test_create_api_contract(tmp_kb):
    """Create an API contract entry."""
    proc = run_log(tmp_kb, "api", "User Service OpenAPI", "--stdin", stdin_text="""## Summary
RESTful API for user management with CRUD operations.

## Details
Endpoints: GET /users, POST /users, GET /users/{id}, PUT /users/{id}, DELETE /users/{id}

## Context
Core user service API contract.

## Usage
All services that need user data use these endpoints.

## Related
Authentication API, Authorization API
""")
    assert proc.returncode == 0
    api_dir = tmp_kb / "api-contracts"
    entry = api_dir / "User-Service-OpenAPI.md"
    assert entry.exists()


def test_dry_run_no_files_written(tmp_kb):
    """--dry-run prevents file creation."""
    proc = run_log(tmp_kb, "pattern", "Dry Run Test", "--stdin", "--dry-run", stdin_text="""## Summary
Should not be written.

## Details
This should not create any files.

## Context
Testing dry-run mode.

## Usage
Verification only.

## Related
None.
""")
    assert proc.returncode == 0
    assert "[Dry Run]" in proc.stdout
    assert "Would create" in proc.stdout

    # No file should be created
    patterns_dir = tmp_kb / "patterns"
    assert not list(patterns_dir.glob("Dry-Run-Test.md"))


def test_missing_required_fields(tmp_kb):
    """Missing Summary causes validation error."""
    proc = run_log(tmp_kb, "pattern", "Bad Entry", "--stdin", stdin_text="""## Summary

## Details
Some details.

## Context
Some context.

## Usage
Some usage.

## Related
None.
""")
    assert proc.returncode != 0
    assert "Validation Error" in proc.stderr


def test_invalid_type(tmp_kb):
    """Invalid type causes error with valid types listed."""
    proc = run_log(tmp_kb, "invalid_type", "Bad", "--stdin", stdin_text="test")
    assert proc.returncode != 0


def test_stdin_input(tmp_kb):
    """Pipe content via stdin creates correct file."""
    proc = run_log(tmp_kb, "pattern", "Stdin Test", "--stdin", stdin_text="""## Summary
Testing stdin input mode.

## Details
This tests that stdin works correctly for piping content.

## Context
Important for agent usage.

## Usage
Use when kb-log.py is invoked from within an agent.

## Related
None.
""")
    assert proc.returncode == 0
    entry = tmp_kb / "patterns" / "Stdin-Test.md"
    assert entry.exists()
    content = entry.read_text()
    assert "Testing stdin input mode" in content


def test_jsonl_log_appended(tmp_kb):
    """.kb-log.jsonl contains a new entry for each operation."""
    run_log(tmp_kb, "pattern", "Log Test", "--stdin", stdin_text="""## Summary
Testing transaction log.

## Details
Verify that .kb-log.jsonl is appended.

## Context
Transaction logging is important for audit trails.

## Usage
Verification.

## Related
None.
""")

    log_path = tmp_kb / ".kb-log.jsonl"
    assert log_path.exists()

    lines = log_path.read_text().strip().split("\n")
    assert len(lines) >= 1

    entry = json.loads(lines[-1])
    assert entry["action"] == "create"
    assert entry["type"] == "pattern"
    assert entry["title"] == "Log Test"


def test_adr_status_supersedes(tmp_kb):
    """ADR with status and supersedes reference."""
    run_log(tmp_kb, "decision", "First Decision", "--stdin", "--status", "accepted", stdin_text="""## 背景
Initial decision.

## 决策
First approach.

## 理由
It was the right choice at the time.

## 考虑的替代方案
None.

## 后果
Some consequences.
""")
    proc = run_log(tmp_kb, "decision", "Second Decision", "--stdin",
                   "--status", "superseded", "--supersedes", "1", stdin_text="""## 背景
Better approach found.

## 决策
Second approach supersedes first.

## 理由
New technology makes this better.

## 考虑的替代方案
Keep first approach: less work but outdated.

## 后果
Migration cost but better long-term.
""")
    assert proc.returncode == 0
    assert "ADR-0002" in proc.stdout

    decisions_dir = tmp_kb / "decisions"
    files = list(decisions_dir.glob("ADR-0002-*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "**替代:** `ADR-0001`" in content


def test_existing_adr_number_respect(tmp_kb):
    """New ADR starts after highest existing ADR number."""
    # Manually create ADR-0005
    decisions_dir = tmp_kb / "decisions"
    existing_adr = decisions_dir / "ADR-0005-existing.md"
    existing_adr.write_text("# ADR-0005: Existing\n\n**Created:** 2026-01-01\n")

    proc = run_log(tmp_kb, "decision", "New Decision", "--stdin", "--status", "proposed", stdin_text="""## 背景
Test.

## 决策
New decision.

## 理由
Reasons.

## 考虑的替代方案
None.

## 后果
OK.
""")
    assert proc.returncode == 0
    assert "ADR-0006" in proc.stdout


def test_title_from_body_heading(tmp_kb):
    """Title from first heading in body overrides command-line title."""
    proc = run_log(tmp_kb, "pattern", "CLI Title", "--stdin", stdin_text="""# Body Title Override

## Summary
Testing title extraction from body.

## Details
The first # heading in the body should become the title.

## Context
Useful when piping content that already has a title.

## Usage
Let the body define the title.

## Related
None.
""")
    assert proc.returncode == 0
    entry = tmp_kb / "patterns" / "Body-Title-Override.md"
    assert entry.exists()
    content = entry.read_text()
    assert "# Body Title Override" in content
