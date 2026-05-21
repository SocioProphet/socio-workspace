#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("jsonschema is required: python3 -m pip install jsonschema") from exc

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "corpus-loop-v0.schema.json"
FIXTURES = ROOT / "registry" / "corpus-loop-v0"
VALID = FIXTURES / "valid.watson-cyc-chronos.json"


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("root must be object")
    return data


def main() -> int:
    schema = load(SCHEMA)
    jsonschema.validate(load(VALID), schema)
    invalids = sorted(FIXTURES.glob("invalid.*.json"))
    if not invalids:
        raise SystemExit("missing invalid fixtures")
    passed = []
    for path in invalids:
        try:
            jsonschema.validate(load(path), schema)
        except Exception:
            continue
        passed.append(path.name)
    if passed:
        raise SystemExit("invalid fixtures passed: " + ", ".join(passed))
    print("OK: corpus loop v0 fixtures validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
