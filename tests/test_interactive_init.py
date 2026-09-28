from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "harness_interactive_init", ROOT / "scripts" / "interactive-init.py"
)
assert SPEC is not None and SPEC.loader is not None
interactive_init = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(interactive_init)


def test_interactive_init_reuses_package_init(monkeypatch, tmp_path: Path) -> None:
    answers = iter(
        [
            "",  # target: supplied as a command-line default
            "",  # source: current checkout
            "",  # platform: supplied as a command-line default
            "",  # business domain
            "",  # language
            "",  # user name
            "",  # reviewers
            "",  # iterations
            "",  # worktree base
            "",  # minimal skills
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    target = tmp_path / "project"
    result = interactive_init.main(
        ["--target", str(target), "--platform", "codex", "--yes"]
    )

    assert result == 0
    assert (target / ".agents" / "skills" / "sw-setup" / "SKILL.md").is_file()
    assert (target / "_context" / "config.yaml").is_file()
    assert (target / ".harness" / "installation.json").is_file()
