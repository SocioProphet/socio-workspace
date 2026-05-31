#!/usr/bin/env python3
"""Validate the SocioSphere contract target ledger."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "architecture" / "service-register" / "contract-target-ledger.v0.1.json"
EXPECTED_ENTRIES = 4
REQUIRED_ENTRY_KEYS = {
    "service_id",
    "contract_repo",
    "schema_path",
    "schema_commit",
    "fixture_path",
    "fixture_commit",
    "validator_path",
    "validator_commit",
    "workflow_path",
    "workflow_commit",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def warn(message: str) -> None:
    print(f"WARN: {message}")


def error(message: str) -> None:
    print(f"ERROR: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def record(required: bool, failures: list[str], message: str) -> None:
    if required:
        error(message)
        failures.append(message)
    else:
        warn(message)


def main() -> int:
    print("SocioSphere contract target ledger check")
    required = os.environ.get("SERVICE_REGISTER_STRICT", "0") == "1"
    failures: list[str] = []

    if not LEDGER.exists():
        record(required, failures, f"missing {LEDGER.relative_to(ROOT)}")
        return 1 if failures else 0

    try:
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        record(required, failures, f"invalid ledger JSON: {exc}")
        return 1 if failures else 0

    entries = ledger.get("entries")
    if not isinstance(entries, list):
        record(required, failures, "ledger entries must be a list")
        return 1 if failures else 0
    if len(entries) == EXPECTED_ENTRIES:
        ok(f"ledger entries={len(entries)}")
    else:
        record(required, failures, f"ledger entries {len(entries)} != expected {EXPECTED_ENTRIES}")

    seen_services: set[str] = set()
    for entry in entries:
        missing = sorted(REQUIRED_ENTRY_KEYS - set(entry))
        service_id = entry.get("service_id", "<missing-service-id>")
        if missing:
            record(required, failures, f"{service_id} missing keys {missing}")
            continue
        if service_id in seen_services:
            record(required, failures, f"duplicate service_id={service_id}")
        seen_services.add(service_id)
        if "/" not in entry["contract_repo"]:
            record(required, failures, f"{service_id} invalid contract_repo={entry['contract_repo']!r}")
        for path_key in ["schema_path", "fixture_path", "validator_path", "workflow_path"]:
            if not entry[path_key] or entry[path_key].startswith("/"):
                record(required, failures, f"{service_id} invalid {path_key}={entry[path_key]!r}")
        for sha_key in ["schema_commit", "fixture_commit", "validator_commit", "workflow_commit"]:
            if not SHA_RE.match(entry[sha_key]):
                record(required, failures, f"{service_id} invalid {sha_key}={entry[sha_key]!r}")

    if failures:
        return 1
    print("contract target ledger check complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
