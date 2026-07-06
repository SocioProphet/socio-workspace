#!/usr/bin/env python3
"""Validate Regis graph, extraction (NER/EL/GrASP), Sherlock index, and masking/tokenization contracts.

Sociosphere-side conformance gate for the contract families added under
protocol/identity-is-prime/{regis,extract,sherlock,masking}/. Like the sibling
validators it is dependency-free for the structural checks (schema shape +
schema_version const + fixture<->schema binding). If `jsonschema` is importable
it additionally runs a full draft 2020-12 validation of every fixture against
its owning schema.

Exit code 0 = all checks pass; non-zero on first failure.
"""

from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
IP = ROOT / "protocol" / "identity-is-prime"

SCHEMA_GLOBS = [
    "regis/schemas/*.schema.json",
    "extract/schemas/*.schema.json",
    "sherlock/schemas/*.schema.json",
    "masking/schemas/*.schema.json",
    "audience/schemas/*.schema.json",
]
FIXTURE_GLOBS = [
    "regis/fixtures/*.json",
    "extract/fixtures/*.json",
    "masking/fixtures/*.json",
    "audience/fixtures/*.json",
]
TRITRPC_REGIS = [
    "tritrpc/regis.graph.v1.upsert_entity.json",
    "tritrpc/regis.graph.v1.unmerge.json",
]

errors: list[str] = []


def err(path: Path, msg: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {msg}")


def load(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        err(path, f"invalid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        err(path, "top-level JSON must be an object")
        return None
    return data


def check_schema(path: Path) -> tuple[str, dict[str, Any]] | None:
    schema = load(path)
    if schema is None:
        return None
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        err(path, "$schema must be draft 2020-12")
    for key in ("$id", "title"):
        if not isinstance(schema.get(key), str) or not schema[key]:
            err(path, f"missing string {key!r}")
    if schema.get("type") != "object":
        err(path, "type must be object")
    required = schema.get("required")
    if not isinstance(required, list) or "schema_version" not in required:
        err(path, "required[] must include schema_version")
    props = schema.get("properties", {})
    sv = props.get("schema_version", {})
    const = sv.get("const")
    if not isinstance(const, str):
        err(path, "properties.schema_version.const must be a string")
        return None
    return const, schema


def main() -> int:
    # 1. schemas -> const map
    const_to_schema: dict[str, dict[str, Any]] = {}
    schema_count = 0
    for g in SCHEMA_GLOBS:
        for sp in sorted(glob.glob(str(IP / g))):
            res = check_schema(Path(sp))
            schema_count += 1
            if res:
                const, schema = res
                if const in const_to_schema:
                    err(Path(sp), f"duplicate schema_version const {const!r}")
                const_to_schema[const] = schema

    # 2. optional deep validator
    validator_for = None
    try:
        from jsonschema import Draft202012Validator

        def validator_for(const: str):  # type: ignore
            return Draft202012Validator(const_to_schema[const])
    except ImportError:
        pass

    # 3. fixtures bind to a schema by their schema_version
    fixture_count = 0
    for g in FIXTURE_GLOBS:
        for fp in sorted(glob.glob(str(IP / g))):
            fixture_count += 1
            path = Path(fp)
            data = load(path)
            if data is None:
                continue
            const = data.get("schema_version")
            if const not in const_to_schema:
                err(path, f"schema_version {const!r} has no matching schema")
                continue
            if validator_for is not None:
                v = validator_for(const)
                issues = sorted(v.iter_errors(data), key=lambda e: e.path)
                for e in issues:
                    err(path, f"jsonschema: {e.message} at {list(e.path)}")

    # 4. regis graph TriTRPC fixtures (wire shape, not object schema)
    tritrpc_count = 0
    for rel in TRITRPC_REGIS:
        path = IP / rel
        tritrpc_count += 1
        if not path.exists():
            err(path, "required TriTRPC fixture missing")
            continue
        data = load(path)
        if data is None:
            continue
        for key in ("fixture_id", "schema_version", "service", "method", "request", "response"):
            if key not in data:
                err(path, f"missing required key {key!r}")
        if data.get("response", {}).get("result") not in {"VERIFIED", "REFUTED", "PENDING", "FAILED"}:
            err(path, "response.result must be VERIFIED/REFUTED/PENDING/FAILED")

    deep = "deep jsonschema" if validator_for else "structural only (install jsonschema for deep)"
    print(f"checked {schema_count} schemas, {fixture_count} fixtures, {tritrpc_count} tritrpc fixtures [{deep}]")
    if errors:
        print(f"\nFAIL — {len(errors)} issue(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS — regis/extract/sherlock/masking contracts conformant")
    return 0


if __name__ == "__main__":
    sys.exit(main())
