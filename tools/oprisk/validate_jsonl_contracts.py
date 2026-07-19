#!/usr/bin/env python3
"""Validate normalized software operational-risk JSONL files against canonical schemas.

Run as a module from the repository root:

    python -m tools.oprisk.validate_jsonl_contracts \
      --contracts-root /path/to/sourceos-spec \
      --target outage_corpus \
      registry/software_oprisk/outage_corpus.seed.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from .schema_registry import SCHEMA_TARGETS

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - import failure is reported to the caller
    Draft202012Validator = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contracts-root", required=True, help="Path to a local checkout of SourceOS-Linux/sourceos-spec")
    parser.add_argument("--target", required=True, choices=sorted(SCHEMA_TARGETS.keys()), help="Schema target to validate against")
    parser.add_argument("paths", nargs="+", help="One or more JSONL files to validate")
    return parser.parse_args()


def load_json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected top-level object")
    return payload


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    payloads: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"{path}:{line_no}: expected top-level object")
            payloads.append(payload)
    return payloads


def build_validator(contracts_root: Path, target: str) -> Draft202012Validator:
    if Draft202012Validator is None:
        raise RuntimeError("jsonschema is not installed; install it in the local environment to run canonical schema validation")
    meta = SCHEMA_TARGETS[target]
    schema = load_json(contracts_root / meta["source_path"])
    return Draft202012Validator(schema)


def main() -> int:
    args = parse_args()
    contracts_root = Path(args.contracts_root)
    validator = build_validator(contracts_root, args.target)
    errors: List[Dict[str, Any]] = []
    checked = 0

    for raw_path in args.paths:
        path = Path(raw_path)
        for payload in load_jsonl(path):
            checked += 1
            for err in validator.iter_errors(payload):
                errors.append({
                    "id": payload.get("id"),
                    "type": payload.get("type"),
                    "message": err.message,
                    "validator": err.validator,
                    "path": list(err.path),
                })

    summary = {
        "target": args.target,
        "checked": checked,
        "valid": checked - len({e['id'] for e in errors}) if errors else checked,
        "invalid": len({e['id'] for e in errors}),
        "errors": errors,
    }

    if errors:
        print(json.dumps(summary, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
