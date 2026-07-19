#!/usr/bin/env python3
"""Validate Boundary Calculus standard examples."""

from __future__ import annotations

import json
from pathlib import Path
import sys

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("ERR: jsonschema is required: python3 -m pip install jsonschema") from exc


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "standards" / "boundary-calculus" / "boundary-calculus-claim-ledger.schema.json"
EXAMPLES_DIR = ROOT / "standards" / "boundary-calculus" / "examples"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def policy_checks(path: Path, entry: dict) -> list[str]:
    errors: list[str] = []
    status = entry.get("claim_status")

    if status == "metaphor" and entry.get("load_bearing") is not False:
        errors.append("metaphor claims must set load_bearing=false")

    if status in {"heuristic", "conjectural"} and not entry.get("promotion_criteria"):
        errors.append(f"{status} claims require promotion_criteria")

    if status == "dropped" and entry.get("load_bearing") is not False:
        errors.append("dropped claims must set load_bearing=false")

    if not entry.get("non_claims"):
        errors.append("non_claims must be non-empty")

    if entry.get("domain") == "security-decision":
        decision = entry.get("security_decision") or {}
        if decision.get("denominator_discipline") == "missing":
            errors.append("security decisions may not pass with missing denominator discipline")
        if decision.get("dependency_model") == "missing":
            errors.append("security decisions may not pass with missing dependency model")
        if not decision.get("discriminating_evidence"):
            errors.append("security decisions require discriminating_evidence")
        loss = decision.get("loss_matrix") or {}
        if "false_positive" not in loss or "false_negative" not in loss:
            errors.append("security decisions require a complete loss_matrix")

    result = (entry.get("policy_result") or {}).get("result")
    if result == "allow" and errors:
        errors.append("policy_result=allow is inconsistent with policy errors")

    return [f"{path}: {err}" for err in errors]


def main() -> int:
    schema = load_json(SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema)

    errors: list[str] = []
    for path in sorted(EXAMPLES_DIR.glob("*.json")):
        entry = load_json(path)
        for err in sorted(validator.iter_errors(entry), key=lambda e: list(e.path)):
            location = ".".join(str(part) for part in err.path) or "<root>"
            errors.append(f"{path}: schema error at {location}: {err.message}")
        errors.extend(policy_checks(path, entry))

    if errors:
        for err in errors:
            print(f"ERR: {err}", file=sys.stderr)
        return 1

    print("OK: boundary calculus examples validate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
