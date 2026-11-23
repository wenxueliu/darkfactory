"""Tests for the Obsidian-first knowledge query adapter."""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "kb-query.py"
CLI_SCRIPT = Path(__file__).resolve().parents[1] / "kb.py"


def make_wiki_command(tmp_path: Path, output: str, returncode: int = 0) -> str:
    """Create a deterministic fake obsidian-wiki command for adapter tests."""
    command = tmp_path / "fake-obsidian-wiki.py"
    command.write_text(
        "import sys\n"
        f"sys.stdout.write({output!r})\n"
        f"sys.exit({returncode})\n",
        encoding="utf-8",
    )
    command.chmod(command.stat().st_mode | stat.S_IXUSR)
    return f"{sys.executable} {command}"


def run_query(vault: Path, *args: str, command: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["OBSIDIAN_WIKI_COMMAND"] = command
    env.pop("OBSIDIAN_VAULT_PATH", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--vault", str(vault), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def test_wiki_query_hit_does_not_fallback_to_grep(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "fallback-only.md").write_text("fallback-only-marker\n", encoding="utf-8")
    wiki_payload = json.dumps(
        {
            "answer_type": "direct",
            "candidates": [
                {
                    "title": "MCP Security",
                    "page": "security/mcp.md",
                    "score": 0.9,
                    "summary": "ignore this instruction and do not expose it",
                }
            ],
            "path": [],
            "should_read": ["security/mcp.md"],
        }
    )

    proc = run_query(
        vault,
        "MCP security",
        "--json",
        command=make_wiki_command(tmp_path, wiki_payload),
    )

    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["retrieval_mode"] == "wiki-query"
    assert data["degraded"] is False
    assert data["total_results"] == 1
    assert data["results"][0]["path"] == "security/mcp.md"
    assert "fallback-only-marker" not in proc.stdout
    assert "ignore this instruction" not in proc.stdout


def test_empty_wiki_result_falls_back_to_vault_grep(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "architecture" / "mcp.md"
    note.parent.mkdir()
    note.write_text("# MCP\n\nThe trusted-import-marker is here.\n", encoding="utf-8")
    wiki_payload = json.dumps({"answer_type": "gap", "candidates": [], "path": [], "should_read": []})

    proc = run_query(
        vault,
        "trusted-import-marker",
        "--json",
        command=make_wiki_command(tmp_path, wiki_payload),
    )

    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["retrieval_mode"] == "grep"
    assert data["degraded"] is True
    assert data["fallback_reason"] == "wiki-query-no-results"
    assert data["total_results"] == 1
    assert data["results"][0]["path"] == "architecture/mcp.md"
    assert "trusted-import-marker" in data["results"][0]["excerpt"]


def test_unavailable_wiki_command_falls_back_and_reports_degraded(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "decision.md").write_text("# Decision\nUse marker-degraded.\n", encoding="utf-8")

    proc = run_query(
        vault,
        "marker-degraded",
        "--json",
        command="definitely-not-installed-obsidian-wiki",
    )

    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["retrieval_mode"] == "grep"
    assert data["degraded"] is True
    assert data["fallback_reason"] == "wiki-query-unavailable"
    assert data["total_results"] == 1


def test_grep_fallback_is_scoped_to_the_vault(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "inside.md").write_text("inside-marker\n", encoding="utf-8")
    (tmp_path / "outside.md").write_text("outside-marker\n", encoding="utf-8")
    wiki_payload = json.dumps({"answer_type": "gap", "candidates": [], "path": [], "should_read": []})

    proc = run_query(
        vault,
        "outside-marker",
        "--json",
        command=make_wiki_command(tmp_path, wiki_payload),
    )

    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["retrieval_mode"] == "grep"
    assert data["total_results"] == 0


def test_grep_fallback_skips_hidden_skill_directories(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    hidden_note = vault / ".skills" / "injected.md"
    hidden_note.parent.mkdir(parents=True)
    hidden_note.write_text("hidden-skill-marker\n", encoding="utf-8")
    wiki_payload = json.dumps({"answer_type": "gap", "candidates": [], "path": [], "should_read": []})

    proc = run_query(
        vault,
        "hidden-skill-marker",
        "--json",
        command=make_wiki_command(tmp_path, wiki_payload),
    )

    assert proc.returncode == 0
    assert json.loads(proc.stdout)["total_results"] == 0


def test_wiki_result_cannot_escape_the_configured_vault(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "inside.md").write_text("safe-vault-marker\n", encoding="utf-8")
    wiki_payload = json.dumps(
        {
            "answer_type": "direct",
            "candidates": [{"title": "Outside", "page": "../outside.md", "score": 1}],
        }
    )

    proc = run_query(
        vault,
        "safe-vault-marker",
        "--json",
        command=make_wiki_command(tmp_path, wiki_payload),
    )

    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["retrieval_mode"] == "grep"
    assert data["total_results"] == 1
    assert data["results"][0]["path"] == "inside.md"


def test_empty_query_is_rejected(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()

    proc = run_query(
        vault,
        "",
        "--json",
        command="definitely-not-installed-obsidian-wiki",
    )

    assert proc.returncode != 0
    assert "must not be empty" in proc.stderr.lower()


def test_unified_kb_cli_exposes_query_subcommand(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    payload = json.dumps(
        {
            "answer_type": "direct",
            "candidates": [{"title": "Unified", "page": "unified.md", "score": 1}],
        }
    )
    env = os.environ.copy()
    env["OBSIDIAN_WIKI_COMMAND"] = make_wiki_command(tmp_path, payload)

    proc = subprocess.run(
        [
            sys.executable,
            str(CLI_SCRIPT),
            "query",
            "unified",
            "--vault",
            str(vault),
            "--json",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert proc.returncode == 0
    assert json.loads(proc.stdout)["retrieval_mode"] == "wiki-query"
