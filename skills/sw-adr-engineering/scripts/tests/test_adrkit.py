"""Unit tests for adrkit (stdlib unittest; run with PYTHONPATH=src)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from adrkit import deps  # noqa: E402
from adrkit.check import check_adrs  # noqa: E402
from adrkit.gen import (  # noqa: E402
    Change,
    GenerationError,
    assess,
    call_llm,
    generate,
    scaffold,
    slugify,
)
from adrkit.index import regenerate  # noqa: E402
from adrkit.init import initialize  # noqa: E402
from adrkit.model import load_adrs, render_index  # noqa: E402

BODY = """\
## Context and Problem Statement

We need a reliable store.

## Decision Drivers

- reliability

## Considered Options

- PostgreSQL
- MySQL

## Decision Outcome

Chosen option: "PostgreSQL", because reliability.

### Consequences

* Good, because reliable.

### Confirmation

Integration tests.

## More Information

None.
"""


def write_adr(
    adr_dir: Path,
    filename: str,
    title: str = "Use PostgreSQL",
    status: str = "accepted",
    extra_frontmatter: str = "",
    body: str = BODY,
) -> Path:
    adr_dir.mkdir(parents=True, exist_ok=True)
    path = adr_dir / filename
    path.write_text(
        "---\n"
        f"status: {status}\n"
        "date: 2026-01-02\n"
        "decision-makers: [alice]\n"
        f"{extra_frontmatter}"
        "---\n\n"
        f"# {title}\n\n"
        f"{body}",
        encoding="utf-8",
    )
    return path


GOOD_ADR = """\
SLUG: use-postgres
---
status: accepted
date: 2026-01-01
decision-makers: []
consulted: []
informed: []
---

# Use PostgreSQL

## Context and Problem Statement

We need a database.

## Decision Drivers

- reliability

## Considered Options

- PostgreSQL
- MySQL

## Decision Outcome

Chosen option: "PostgreSQL", because reliability.

### Consequences

* Good, because reliable.

### Confirmation

Integration tests.

## More Information

None.
"""


class IndexTests(unittest.TestCase):
    def test_order_and_annotations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp) / "docs" / "adr"
            write_adr(adr_dir, "0002-adopt-madr.md", "Adopt MADR", "accepted")
            write_adr(adr_dir, "0001-use-postgres.md", "Use PostgreSQL", "proposed")
            write_adr(
                adr_dir,
                "0003-extract-notification.md",
                "Extract notification service",
                "superseded by ADR-0002",
            )
            content = render_index(load_adrs(adr_dir))
            lines = content.splitlines()
            self.assertEqual(lines[0], "# Architecture Decision Records")
            self.assertEqual(lines[1], "")
            self.assertEqual(
                lines[2],
                "* [ADR-0001](0001-use-postgres.md) - Use PostgreSQL (proposed)",
            )
            self.assertEqual(
                lines[3],
                "* [ADR-0002](0002-adopt-madr.md) - Adopt MADR",
            )
            self.assertEqual(
                lines[4],
                "* [ADR-0003](0003-extract-notification.md) - Extract notification "
                "service (superseded by ADR-0002)",
            )

    def test_idempotent_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            write_adr(adr_dir, "0001-use-postgres.md")
            self.assertTrue(regenerate(adr_dir, quiet=True))
            first = (adr_dir / "index.md").read_text(encoding="utf-8")
            self.assertFalse(regenerate(adr_dir, quiet=True))
            self.assertEqual(first, (adr_dir / "index.md").read_text(encoding="utf-8"))

    def test_invalid_filename_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            write_adr(adr_dir, "not-an-adr.md")
            content = render_index(load_adrs(adr_dir))
            self.assertNotIn("not-an-adr", content)


class CheckTests(unittest.TestCase):
    def _issues(self, adr_dir: Path):
        return check_adrs(load_adrs(adr_dir), adr_dir)

    def test_clean_repository_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            write_adr(adr_dir, "0001-use-postgres.md")
            write_adr(
                adr_dir,
                "0002-superseded.md",
                "Old approach",
                "superseded by ADR-0003",
            )
            write_adr(
                adr_dir,
                "0003-new-approach.md",
                "New approach",
                "accepted",
                extra_frontmatter="supersedes: [ADR-0002]\n",
            )
            issues = self._issues(adr_dir)
            errors = [issue for issue in issues if issue.level == "error"]
            self.assertEqual(errors, [])

    def test_missing_backlink_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            write_adr(adr_dir, "0001-old.md", "Old", "superseded by ADR-0002")
            write_adr(adr_dir, "0002-new.md", "New", "accepted")
            issues = self._issues(adr_dir)
            self.assertIn(("R2.2", "error"), {(i.rule, i.level) for i in issues})

    def test_missing_target_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            write_adr(adr_dir, "0001-old.md", "Old", "superseded by ADR-0009")
            issues = self._issues(adr_dir)
            self.assertIn(("R2.1", "error"), {(i.rule, i.level) for i in issues})

    def test_cycle_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            write_adr(
                adr_dir,
                "0001-a.md",
                "A",
                "superseded by ADR-0002",
                extra_frontmatter="supersedes: [ADR-0002]\n",
            )
            write_adr(
                adr_dir,
                "0002-b.md",
                "B",
                "superseded by ADR-0001",
                extra_frontmatter="supersedes: [ADR-0001]\n",
            )
            issues = self._issues(adr_dir)
            self.assertIn(("R2.4", "error"), {(i.rule, i.level) for i in issues})

    def test_duplicate_number_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            write_adr(adr_dir, "0001-a.md", "A")
            write_adr(adr_dir, "0001-b.md", "B")
            issues = self._issues(adr_dir)
            self.assertIn(("R1.2", "error"), {(i.rule, i.level) for i in issues})

    def test_unfilled_template_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            (adr_dir / "0001-draft.md").write_text(
                "---\nstatus: proposed\n---\n\n# <!-- short title -->\n\n"
                "## Context and Problem Statement\n\n\n"
                "## Decision Outcome\n\nChosen option: \"\", because\n",
                encoding="utf-8",
            )
            issues = self._issues(adr_dir)
            self.assertIn(("R1.8", "error"), {(i.rule, i.level) for i in issues})

    def test_numbering_gap_is_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            write_adr(adr_dir, "0001-a.md", "A")
            write_adr(adr_dir, "0003-c.md", "C")
            issues = self._issues(adr_dir)
            gap = [issue for issue in issues if issue.rule == "R1.3"]
            self.assertEqual(len(gap), 1)
            self.assertEqual(gap[0].level, "warning")


class InitTests(unittest.TestCase):
    def test_creates_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp) / "docs" / "adr"
            self.assertEqual(initialize(adr_dir, quiet=True), 0)
            template = adr_dir / "template" / "adr-template.md"
            self.assertTrue(template.is_file())
            self.assertIn("## Context and Problem Statement", template.read_text())
            self.assertEqual(initialize(adr_dir, quiet=True), 0)

    def test_refuses_to_overwrite_custom_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp)
            self.assertEqual(initialize(adr_dir, quiet=True), 0)
            template = adr_dir / "template" / "adr-template.md"
            template.write_text("custom", encoding="utf-8")
            self.assertEqual(initialize(adr_dir, quiet=True), 1)
            self.assertEqual(initialize(adr_dir, force=True, quiet=True), 0)
            self.assertNotEqual(template.read_text(), "custom")


class GenTests(unittest.TestCase):
    def test_noise_only_commit_is_skipped(self) -> None:
        signal = assess(
            Change(
                source="commit",
                message="docs: fix typo",
                files=[("M", "docs/readme.md"), ("M", "package-lock.json")],
            )
        )
        self.assertFalse(signal.worth)
        self.assertEqual(signal.score, 0)

    def test_migration_is_worth_an_adr(self) -> None:
        signal = assess(
            Change(
                source="commit",
                message="feat: add tenant id",
                files=[("A", "db/migrations/0007_tenant.sql")],
            )
        )
        self.assertTrue(signal.worth)
        self.assertGreaterEqual(signal.score, 5)

    def test_slugify(self) -> None:
        self.assertEqual(slugify("Use PostgreSQL!"), "use-postgresql")
        self.assertEqual(slugify("迁移到 Rust"), "rust")

    def test_generate_writes_proposed_adr_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp) / "docs" / "adr"
            result = generate(
                Change(source="text", message="Use PostgreSQL"),
                adr_dir,
                Path(tmp),
                llm_fn=lambda _messages, _model: GOOD_ADR,
            )
            self.assertEqual(result.status, "written")
            assert result.path is not None
            self.assertEqual(result.path.name, "0001-use-postgres.md")
            text = result.path.read_text(encoding="utf-8")
            self.assertIn("status: proposed", text)
            self.assertNotIn("status: accepted", text)
            self.assertTrue((adr_dir / "index.md").is_file())

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp) / "docs" / "adr"
            result = generate(
                Change(source="text", message="Use PostgreSQL"),
                adr_dir,
                Path(tmp),
                dry_run=True,
                llm_fn=lambda _messages, _model: GOOD_ADR,
            )
            self.assertEqual(result.status, "preview")
            self.assertFalse((adr_dir / "0001-use-postgres.md").exists())
            self.assertFalse(adr_dir.exists())

    def test_retry_after_invalid_output(self) -> None:
        calls: list[list[dict[str, str]]] = []

        def fake(messages, _model):
            calls.append(messages)
            return "not an ADR" if len(calls) == 1 else GOOD_ADR

        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp) / "docs" / "adr"
            result = generate(
                Change(source="text", message="Use PostgreSQL"),
                adr_dir,
                Path(tmp),
                llm_fn=fake,
            )
            self.assertEqual(result.status, "written")
            self.assertEqual(len(calls), 2)
            self.assertIn("corrected ADR", calls[1][-1]["content"])

    def test_no_llm_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adr_dir = Path(tmp) / "docs" / "adr"
            result = generate(
                Change(source="text", message="Use PostgreSQL"),
                adr_dir,
                Path(tmp),
                no_llm=True,
            )
            self.assertEqual(result.status, "written")
            assert result.path is not None
            self.assertIn("status: proposed", result.path.read_text(encoding="utf-8"))

    def test_scaffold_contains_signal_reasons(self) -> None:
        change = Change(
            source="commit",
            message="feat: add migration",
            files=[("A", "db/migrations/0001.sql")],
        )
        text = scaffold("Add migration", change, assess(change))
        self.assertIn("database migration", text)


class DepsTests(unittest.TestCase):
    def test_registry_names(self) -> None:
        self.assertEqual(
            set(deps.PACKAGES), {"openai", "pyyaml", "adr-drift"}
        )

    def test_unknown_package_raises(self) -> None:
        with self.assertRaises(KeyError):
            deps.available("not-a-package")

    def test_ensure_installs_missing(self) -> None:
        state = {"openai": False}
        calls: list[str] = []

        def availability(_name: str) -> bool:
            return state["openai"]

        def installer(spec: str) -> None:
            calls.append(spec)
            state["openai"] = True

        installed, missing = deps.ensure(
            ["openai"],
            installer=installer,
            availability=availability,
            quiet=True,
        )
        self.assertEqual(installed, ["openai"])
        self.assertEqual(missing, [])
        self.assertEqual(calls, ["openai>=1.0"])

    def test_ensure_reports_missing_without_install(self) -> None:
        installed, missing = deps.ensure(
            ["openai"],
            install=False,
            availability=lambda _name: False,
            quiet=True,
        )
        self.assertEqual(installed, [])
        self.assertEqual(missing, ["openai"])

    def test_ensure_survives_install_failure(self) -> None:
        def installer(_spec: str) -> None:
            raise deps.DependencyError("pip is externally managed")

        installed, missing = deps.ensure(
            ["openai"],
            installer=installer,
            availability=lambda _name: False,
            quiet=True,
        )
        self.assertEqual(installed, [])
        self.assertEqual(missing, ["openai"])

    def test_call_llm_errors_when_openai_cannot_be_installed(self) -> None:
        with patch.dict(sys.modules, {"openai": None}):
            with patch("adrkit.deps.ensure", return_value=([], ["openai"])):
                with patch.dict(
                    "os.environ", {"ADR_LLM_API_KEY": "test-key"}, clear=False
                ):
                    with self.assertRaises(GenerationError):
                        call_llm(
                            [{"role": "user", "content": "hello"}], "model"
                        )


if __name__ == "__main__":
    unittest.main()
