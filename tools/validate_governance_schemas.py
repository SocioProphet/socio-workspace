#!/usr/bin/env python3
"""Validate governance schema fixtures.

This validator intentionally depends on jsonschema rather than a partial hand-rolled
checker because the governance contracts use JSON Schema draft 2020-12 constraints.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover - exercised in CI setup failure only
    print("governance-schemas: ERROR: jsonschema is required", file=sys.stderr)
    raise SystemExit(2) from exc

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas" / "governance"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "governance"

CASES = {
    "evidence-bundle": {
        "schema": "evidence-bundle.v0.1.schema.json",
        "valid": "evidence-bundle.valid.synthetic.json",
        "invalid": "evidence-bundle.invalid.missing-policy.synthetic.json",
    },
    "procedure-template": {
        "schema": "procedure-template.v0.1.schema.json",
        "valid": "procedure-template.valid.synthetic.json",
        "invalid": "procedure-template.invalid.missing-replay.synthetic.json",
    },
    "execution-receipt": {
        "schema": "execution-receipt.v0.1.schema.json",
        "valid": "execution-receipt.valid.synthetic.json",
        "invalid": "execution-receipt.invalid.bad-digest.synthetic.json",
    },
    "institutional-action": {
        "schema": "institutional-action.v0.1.schema.json",
        "valid": "institutional-action.valid.synthetic.json",
        "invalid": "institutional-action.invalid.missing-execution-receipt.synthetic.json",
    },
    "governance-bench": {
        "schema": "governance-bench.v0.1.schema.json",
        "valid": "governance-bench.valid.synthetic.json",
        "invalid": "governance-bench.invalid.missing-thresholds.synthetic.json",
    },
    "workflow-bench": {
        "schema": "workflow-bench.v0.1.schema.json",
        "valid": "workflow-bench.valid.synthetic.json",
        "invalid": "workflow-bench.invalid.missing-metrics.synthetic.json",
    },
    "domain-bench": {
        "schema": "domain-bench.v0.1.schema.json",
        "valid": "domain-bench.valid.synthetic.json",
        "invalid": "domain-bench.invalid.missing-adjudication.synthetic.json",
    },
    "replay-bench": {
        "schema": "replay-bench.v0.1.schema.json",
        "valid": "replay-bench.valid.synthetic.json",
        "invalid": "replay-bench.invalid.missing-replay-tests.synthetic.json",
    },
}


def load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"governance-schemas: ERROR: invalid JSON in {path}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


def validate_case(name: str, spec: dict[str, str]) -> bool:
    schema_path = SCHEMA_DIR / spec["schema"]
    valid_path = FIXTURE_DIR / spec["valid"]
    invalid_path = FIXTURE_DIR / spec["invalid"]

    schema = load_json(schema_path)
    valid_doc = load_json(valid_path)
    invalid_doc = load_json(invalid_path)

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        print(f"governance-schemas: ERROR: schema invalid for {name}: {exc.message}", file=sys.stderr)
        return False

    validator = jsonschema.Draft202012Validator(schema)
    valid_errors = sorted(validator.iter_errors(valid_doc), key=lambda err: list(err.path))
    if valid_errors:
        print(f"governance-schemas: ERROR: valid fixture failed for {name}", file=sys.stderr)
        for err in valid_errors:
            print(f"  {valid_path}: {list(err.path)}: {err.message}", file=sys.stderr)
        return False

    invalid_errors = sorted(validator.iter_errors(invalid_doc), key=lambda err: list(err.path))
    if not invalid_errors:
        print(f"governance-schemas: ERROR: invalid fixture unexpectedly passed for {name}", file=sys.stderr)
        return False

    print(f"governance-schemas: OK {name} ({len(invalid_errors)} expected invalid-fixture error(s))")
    return True


def main() -> int:
    ok = True
    for name, spec in CASES.items():
        ok = validate_case(name, spec) and ok
    if ok:
        print(f"governance-schemas: OK ({len(CASES)} schema fixture pairs)")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
