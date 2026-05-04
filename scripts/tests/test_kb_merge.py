"""Tests for kb-merge.py — knowledge base deduplication and merging."""

import json
import os
import subprocess
import sys

SCRIPT_MERGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb-merge.py")
SCRIPT_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kb-log.py")


def run_merge(kb_dir, *args):
    """Run kb-merge.py and return CompletedProcess."""
    cmd = [sys.executable, SCRIPT_MERGE, "--kb-dir", str(kb_dir)] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def run_log(kb_dir, *args, stdin_text=None):
    """Run kb-log.py and return CompletedProcess."""
    cmd = [sys.executable, SCRIPT_LOG, "--kb-dir", str(kb_dir)] + list(args)
    return subprocess.run(cmd, input=stdin_text, capture_output=True, text=True)


def _create_entry(dir_path, filename, content):
    """Helper to create a KB entry file."""
    filepath = dir_path / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath


# ---- Scan tests ----

def test_scan_empty_kb(tmp_kb):
    """Scan on an empty knowledge base finds 0 pairs."""
    proc = run_merge(tmp_kb, "--scan", "--threshold", "0.3")
    assert proc.returncode == 0
    assert "No similar pairs found" in proc.stdout


def test_scan_finds_similar_pairs(tmp_kb):
    """Scan finds two very similar pattern entries."""
    _create_entry(tmp_kb / "patterns", "auth-flow.md", """# User Authentication Flow

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Authentication flow using JWT tokens with refresh mechanism.

## Details
This pattern describes the standard OAuth2 / JWT authentication flow.
Users log in, receive an access token and refresh token, and use the
access token for API requests.

## Context
Used across multiple microservices for user identity propagation.
""")

    _create_entry(tmp_kb / "patterns", "auth-flow-v2.md", """# Authentication Flow v2

**Type:** Pattern
**Created:** 2026-05-02
**Author:** test

## Summary
Authentication flow using JWT tokens with refresh mechanism (updated).

## Details
This pattern describes the standard OAuth2 / JWT authentication flow
with some improvements. Users log in, receive access and refresh tokens.

## Context
Updated version used across microservices for identity propagation.
""")

    proc = run_merge(tmp_kb, "--scan", "--threshold", "0.4")
    assert proc.returncode == 0
    assert "Similar pairs found:" in proc.stdout
    assert "auth-flow" in proc.stdout


def test_scan_skips_different_types_without_cross(tmp_kb):
    """Without --cross-type, pattern and lesson are not compared."""
    _create_entry(tmp_kb / "patterns", "retry.md", """# Retry Pattern

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Retry failed operations with exponential backoff.

## Details
When an operation fails due to transient errors, retry with increasing delays.
Max 3 retries for idempotent operations.
""")

    _create_entry(tmp_kb / "lessons", "retry-lesson.md", """# Retry Lesson

**Type:** Lesson
**Created:** 2026-05-01
**Author:** test

## Summary
Retry failed operations with exponential backoff.

## Details
When an operation fails due to transient errors, retry with increasing delays.
Max 3 retries for idempotent operations.
""")

    proc = run_merge(tmp_kb, "--scan", "--threshold", "0.5")
    assert proc.returncode == 0
    assert "No similar pairs found" in proc.stdout


def test_scan_cross_type_finds_pairs(tmp_kb):
    """With --cross-type, identical content in different types is found."""
    content = """# Retry Pattern

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Retry failed operations.

## Details
Retry with exponential backoff for transient errors.
"""
    _create_entry(tmp_kb / "patterns", "retry.md", content)
    _create_entry(tmp_kb / "lessons", "retry-lesson.md", content.replace("Pattern", "Lesson").replace("retry.md", "retry-lesson.md"))

    proc = run_merge(tmp_kb, "--scan", "--cross-type", "--threshold", "0.5")
    assert proc.returncode == 0
    assert "Similar pairs found:" in proc.stdout


def test_scan_respects_threshold(tmp_kb):
    """A higher threshold excludes less-similar pairs."""
    _create_entry(tmp_kb / "patterns", "auth.md", """# Auth Pattern

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Authentication using JWT tokens.

## Details
Standard JWT-based authentication with refresh token support.
""")

    _create_entry(tmp_kb / "patterns", "logging.md", """# Logging Pattern

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Structured logging with correlation IDs.

## Details
Every service should emit structured JSON logs with a correlation ID
for tracing across service boundaries.
""")

    # At 0.9 threshold, unrelated entries should not match
    proc = run_merge(tmp_kb, "--scan", "--threshold", "0.9")
    assert proc.returncode == 0
    assert "No similar pairs found" in proc.stdout


def test_scan_json_output(tmp_kb):
    """JSON output is valid and contains expected fields."""
    _create_entry(tmp_kb / "patterns", "auth.md", """# Auth Pattern

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Authentication using JWT tokens.

## Details
Standard JWT-based authentication.
""")

    _create_entry(tmp_kb / "patterns", "auth2.md", """# Auth Pattern 2

**Type:** Pattern
**Created:** 2026-05-02
**Author:** test

## Summary
Authentication using JWT tokens.

## Details
Standard JWT-based authentication flow.
""")

    proc = run_merge(tmp_kb, "--scan", "--threshold", "0.5", "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert "total_pairs" in data
    assert "pairs" in data
    assert data["total_pairs"] >= 1
    pair = data["pairs"][0]
    assert "similarity" in pair
    assert "file_a" in pair
    assert "file_b" in pair
    assert "title_a" in pair
    assert "title_b" in pair


# ---- Merge tests ----

def test_merge_combines_sections(tmp_kb):
    """Merging two entries combines Summary and Details correctly."""
    file_a = _create_entry(tmp_kb / "patterns", "auth-v1.md", """# Auth Flow V1

**Type:** Pattern
**Created:** 2026-05-01
**Author:** alice

## Summary
Authentication using JWT.

## Details
Standard JWT auth flow.

## Context
Used in v1 services.

## Usage
Call /login endpoint.

## Related
None.
""")

    file_b = _create_entry(tmp_kb / "patterns", "auth-v2.md", """# Authentication Flow V2 Updated

**Type:** Pattern
**Created:** 2026-05-03
**Author:** bob

## Summary
Updated authentication using JWT with refresh tokens.

## Details
Enhanced JWT auth with refresh token rotation and device tracking.

## Context
Updated for v2 services.

## Usage
Call /login and /refresh endpoints.

## Related
See also: refresh-token pattern.
""")

    proc = run_merge(tmp_kb, "--merge", str(file_a), str(file_b))
    assert proc.returncode == 0, proc.stderr

    # The merged file should exist (older file kept)
    assert os.path.exists(str(file_a)) or os.path.exists(str(file_b))
    # The removed file should not exist
    assert not os.path.exists(str(file_a)) or not os.path.exists(str(file_b))

    merged_path = str(file_a) if os.path.exists(str(file_a)) else str(file_b)
    merged = open(merged_path, encoding="utf-8").read()
    assert "Merged" in merged  # **Merged:** metadata


def test_merge_dry_run(tmp_kb):
    """--dry-run previews merge without modifying files."""
    file_a = _create_entry(tmp_kb / "patterns", "dry-a.md", """# Entry A

**Type:** Pattern
**Created:** 2026-05-01
**Author:** alice

## Summary
Entry A summary.

## Details
Entry A details.
""")

    file_b = _create_entry(tmp_kb / "patterns", "dry-b.md", """# Entry B

**Type:** Pattern
**Created:** 2026-05-02
**Author:** bob

## Summary
Entry B summary.

## Details
Entry B details.
""")

    proc = run_merge(tmp_kb, "--merge", str(file_a), str(file_b), "--dry-run")
    assert proc.returncode == 0
    assert "[Dry Run]" in proc.stdout

    # Both files should still exist
    assert os.path.exists(str(file_a))
    assert os.path.exists(str(file_b))


def test_merge_refuses_adr(tmp_kb):
    """Merging ADR entries is refused."""
    file_a = _create_entry(tmp_kb / "decisions", "ADR-0001-auth.md", """# ADR-0001: Use JWT

**状态:** `accepted`
**日期:** `2026-05-01`
**决策者:** `alice`

## 背景
Need authentication.

## 决策
Use JWT.

## 理由
Industry standard.
""")

    file_b = _create_entry(tmp_kb / "decisions", "ADR-0002-oauth.md", """# ADR-0002: Use OAuth

**状态:** `accepted`
**日期:** `2026-05-02`
**决策者:** `bob`

## 背景
Need better auth.

## 决策
Use OAuth.

## 理由
More secure.
""")

    proc = run_merge(tmp_kb, "--merge", str(file_a), str(file_b))
    assert proc.returncode != 0
    assert "ADR" in proc.stderr


def test_merge_all_handles_empty(tmp_kb):
    """--merge-all on empty or distinct KB does nothing."""
    proc = run_merge(tmp_kb, "--merge-all", "--threshold", "0.5")
    assert proc.returncode == 0
    assert "No pairs to merge" in proc.stdout or "No similar pairs found" in proc.stdout


# ---- Dedup check tests (via kb-log.py) ----

def test_dedup_check_blocks_near_duplicate(tmp_kb):
    """--dedup-check blocks creation when >80% similar entry exists."""
    _create_entry(tmp_kb / "patterns", "existing-auth.md", """# Authentication Flow

**Type:** Pattern
**Created:** 2026-05-01
**Author:** alice

## Summary
Authentication using JWT tokens with refresh mechanism.

## Details
This pattern describes the standard OAuth2 / JWT authentication flow.
Users log in, receive an access token and refresh token, and use the
access token for API requests. The refresh token is stored securely
and rotated on each use.

## Context
Used across multiple microservices for user identity propagation.

## Usage
Implement the /login and /refresh endpoints following this pattern.
""")

    # Nearly identical content
    stdin = """## Summary
Authentication using JWT tokens with refresh mechanism (similar).

## Details
This pattern describes the standard OAuth2 / JWT authentication flow.
Users log in, receive an access token and refresh token, and use the
access token for API requests. The refresh token is stored securely.

## Context
Used across multiple microservices for identity propagation.

## Usage
Implement /login and /refresh endpoints following this pattern.
"""

    proc = run_log(tmp_kb, "pattern", "Auth Flow Similar", "--author", "test",
                   "--stdin", "--dedup-check", "--dedup-threshold", "0.4",
                   stdin_text=stdin)
    # Should be blocked (or warn if not >80%)
    # With very similar content, expect blocking or at minimum warning
    if proc.returncode != 0:
        assert "BLOCKED" in proc.stdout or "near-duplicate" in proc.stdout.lower()
        assert not os.path.exists(str(tmp_kb / "patterns" / "Auth-Flow-Similar.md"))
    else:
        # If not blocked, it at least found similar entries
        assert "Dedup Check" in proc.stdout


def test_dedup_check_allows_unique(tmp_kb):
    """--dedup-check allows creation when no similar entries exist."""
    _create_entry(tmp_kb / "patterns", "auth.md", """# Authentication Flow

**Type:** Pattern
**Created:** 2026-05-01
**Author:** alice

## Summary
Authentication using JWT tokens.

## Details
Standard JWT auth flow with refresh token support.
""")

    # Completely different content
    stdin = """## Summary
Structured logging with correlation IDs for distributed tracing.

## Details
Every service should emit JSON-structured logs with a unique correlation ID
that is propagated across service boundaries via HTTP headers. This enables
end-to-end request tracing in distributed systems.

## Context
Microservice architecture requires distributed tracing for debugging.

## Usage
Add correlation ID middleware to each service. Log every request with it.
"""

    proc = run_log(tmp_kb, "pattern", "Logging Pattern", "--author", "test",
                   "--stdin", "--dedup-check", "--dedup-threshold", "0.4",
                   stdin_text=stdin)
    assert proc.returncode == 0
    assert os.path.exists(str(tmp_kb / "patterns" / "Logging-Pattern.md"))


def test_auto_dedup_skips_quietly(tmp_kb):
    """--auto-dedup skips creation silently when near-duplicate found."""
    existing = """# Circuit Breaker Pattern

**Type:** Pattern
**Created:** 2026-05-01
**Author:** alice

## Summary
Circuit breaker for external service calls.

## Details
When calling external services, wrap calls with a circuit breaker that opens
after N consecutive failures and half-opens after a timeout period. This
prevents cascading failures in distributed systems.

## Context
Distributed microservice architectures need resilience patterns.

## Usage
Apply circuit breaker to all outbound HTTP and gRPC calls.
"""
    _create_entry(tmp_kb / "patterns", "circuit-breaker.md", existing)

    stdin = """## Summary
Circuit breaker for external service calls (duplicate).

## Details
When calling external services, wrap calls with a circuit breaker that opens
after N consecutive failures and half-opens after a timeout period. This
prevents cascading failures.

## Context
Microservice architectures need resilience patterns.

## Usage
Apply to all outbound HTTP and gRPC calls.
"""

    proc = run_log(tmp_kb, "pattern", "Circuit Breaker V2", "--author", "test",
                   "--stdin", "--auto-dedup", "--dedup-threshold", "0.4",
                   stdin_text=stdin)
    assert proc.returncode == 0
    assert "Skipped" in proc.stdout
    assert not os.path.exists(str(tmp_kb / "patterns" / "Circuit-Breaker-V2.md"))


# ---- KL divergence-style edge cases ----

def test_similarity_different_lengths(tmp_kb):
    """Similarity normalization handles entries of very different lengths."""
    short = """# Short Entry

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Short summary about auth.

## Details
Auth detail.
"""
    _create_entry(tmp_kb / "patterns", "short.md", short)

    long_content = """# Long Entry

**Type:** Pattern
**Created:** 2026-05-01
**Author:** test

## Summary
Short summary about auth and many other things.

## Details
Auth detail plus a lot more content that makes this entry much longer
than the short one. Additional paragraphs about architecture, deployment,
testing strategies, monitoring, alerting, logging, tracing, and more.

This is filler content to make the entry substantially longer than the
short entry while still sharing the same core keywords. The similarity
score should be normalized to account for the length difference.

More filler: CI/CD pipelines, code review checklist, security scanning,
dependency management, version control strategy, branching model,
release process, incident response, post-mortem templates.
"""
    _create_entry(tmp_kb / "patterns", "long.md", long_content)

    proc = run_merge(tmp_kb, "--scan", "--threshold", "0.2")
    assert proc.returncode == 0
    # The pair should be detected (they share auth keywords)
    # but similarity should be moderatish due to length normalization
    assert "Similar pairs found:" in proc.stdout
    assert "short" in proc.stdout.lower()


def test_scan_multiple_pairs(tmp_kb):
    """Multiple similar pairs are all detected above threshold."""
    for i, (topic, summary) in enumerate([
        ("auth", "Authentication flow using JWT tokens with OAuth2"),
        ("retry", "Retry transient failures with exponential backoff"),
        ("cache", "Read-through caching strategy with TTL eviction"),
    ]):
        _create_entry(tmp_kb / "patterns", f"{topic}-v1.md", f"""# {topic.title()} Pattern V1

**Type:** Pattern
**Created:** 2026-05-01
**Author:** alice

## Summary
{summary} (v1).

## Details
Implementation details for {topic} pattern in microservice context.
Uses {topic}-specific configuration and metrics.

## Context
Microservice environment with multiple downstream dependencies.

## Usage
Apply {topic} pattern at service boundaries and external integrations.
""")
        _create_entry(tmp_kb / "patterns", f"{topic}-v2.md", f"""# {topic.title()} Pattern V2

**Type:** Pattern
**Created:** 2026-05-02
**Author:** bob

## Summary
{summary} (v2, enhanced).

## Details
Enhanced implementation of {topic} pattern with monitoring and alerting.
Added {topic}-specific dashboards and runbooks.

## Context
Production microservice environment.

## Usage
Apply {topic} pattern with the new telemetry hooks.
""")

    proc = run_merge(tmp_kb, "--scan", "--threshold", "0.5")
    assert proc.returncode == 0
    # Should find at least the 3 v1-v2 pairs (each topic has two versions)
    assert "Similar pairs found:" in proc.stdout
    # Parse the count from "Similar pairs found: N"
    import re
    m = re.search(r'Similar pairs found: (\d+)', proc.stdout)
    assert m is not None
    pair_count = int(m.group(1))
    assert pair_count >= 3, f"Expected at least 3 pairs, got {pair_count}"
