"""Command line entry point for document contract operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import ResourceRoot
from .resolver import DefinitionResolver
from .validation import DocumentValidator


def _root(value: str) -> ResourceRoot:
    if "=" not in value:
        raise argparse.ArgumentTypeError("root must use SCOPE=PATH, for example project=./_context/templates")
    scope, path = value.split("=", 1)
    if not scope or not path:
        raise argparse.ArgumentTypeError("root must use SCOPE=PATH")
    return ResourceRoot(scope, Path(path).resolve())


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m document_contracts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    resolve_parser = subparsers.add_parser("resolve")
    resolve_parser.add_argument("--document-type", required=True)
    resolve_parser.add_argument("--variant", default="default")
    resolve_parser.add_argument("--root", action="append", type=_root, required=True)

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--document-type", required=True)
    validate_parser.add_argument("--variant", default="default")
    validate_parser.add_argument("--document", type=Path, required=True)
    validate_parser.add_argument("--root", action="append", type=_root, required=True)

    args = parser.parse_args()
    definition = DefinitionResolver(args.root).resolve(args.document_type, args.variant)
    if args.command == "resolve":
        print(
            json.dumps(
                {
                    "document_type": definition.document_type,
                    "variant": definition.variant,
                    "contract": definition.contract,
                    "version": definition.version,
                    "resources": {
                        name: {
                            "scope": selection.scope,
                            "path": str(selection.path) if selection.path else None,
                            "disabled": selection.disabled,
                        }
                        for name, selection in definition.resources.items()
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    result = DocumentValidator().validate(definition, args.document)
    print(
        json.dumps(
            {
                "passed": result.passed,
                "validator": str(result.validator_source) if result.validator_source else None,
                "gate": str(result.gate_source) if result.gate_source else None,
                "findings": [finding.__dict__ for finding in result.findings],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
