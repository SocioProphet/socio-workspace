#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json
import sys

try:
    import yaml  # type: ignore
except Exception:
    print("ERR: PyYAML not installed. Install with: python3 -m pip install pyyaml", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parents[1]  # standards/qes
CAT = ROOT / "schemas/topics/topic-catalog.v1.yaml"

def main() -> int:
    if not CAT.exists():
        print(f"ERR: missing topic catalog: {CAT}", file=sys.stderr)
        return 2
    doc = yaml.safe_load(CAT.read_text())
    topics = doc.get("topics", [])
    errs = 0
    for t in topics:
        schema_rel = t.get("schema")
        if not schema_rel:
            print(f"ERR: topic missing schema field: {t}", file=sys.stderr)
            errs += 1
            continue
        schema_path = ROOT / "schemas" / schema_rel
        if not schema_path.exists():
            print(f"ERR: missing schema file for topic {t.get('name')}: {schema_path}", file=sys.stderr)
            errs += 1
            continue
        if schema_path.suffix == ".json":
            try:
                json.loads(schema_path.read_text())
            except Exception as e:
                print(f"ERR: invalid JSON in {schema_path}: {e}", file=sys.stderr)
                errs += 1
    if errs:
        print(f"FAIL: {errs} schema issue(s)", file=sys.stderr)
        return 1
    print("OK: topic catalog schemas exist and JSON parses")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
