#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("jsonschema is required: python3 -m pip install jsonschema") from exc

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "corpus-loop-v1.schema.json"
FIXTURES = ROOT / "registry" / "corpus-loop-v1"
VALID = FIXTURES / "valid.watson-cyc-chronos.pinned.json"
REQUIRED = {"evidence", "ontology", "policy", "runtime", "ledger"}


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("root must be object")
    return data


def check_manifest(data: dict) -> None:
    planes = [item["plane"] for item in data["components"]]
    if set(planes) != REQUIRED:
        raise ValueError("required planes missing")
    if len(planes) != len(set(planes)):
        raise ValueError("duplicate plane")
    for item in data["components"]:
        if len(item["pinned_commit"]) != 40:
            raise ValueError("invalid pin length")
        if not item["artifact_refs"]:
            raise ValueError("missing artifact refs")
    boundary = data["sociosphere_boundary"]
    if boundary["owns_coordination"] is not True:
        raise ValueError("coordination flag must be true")
    if boundary["owns_downstream_implementation"] is not False:
        raise ValueError("owner boundary must remain false")


def validate(path: Path, schema: dict) -> None:
    data = load(path)
    jsonschema.validate(data, schema)
    check_manifest(data)


def main() -> int:
    schema = load(SCHEMA)
    validate(VALID, schema)
    invalids = sorted(FIXTURES.glob("invalid.*.json"))
    if not invalids:
        raise SystemExit("missing invalid v1 fixtures")
    passed = []
    for path in invalids:
        try:
            validate(path, schema)
        except Exception:
            continue
        passed.append(path.name)
    if passed:
        raise SystemExit("invalid v1 fixtures passed: " + ", ".join(passed))
    print("OK: corpus loop v1 manifest validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
