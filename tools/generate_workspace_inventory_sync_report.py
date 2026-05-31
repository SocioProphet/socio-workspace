#!/usr/bin/env python3
"""Generate or check the Workspace Inventory sync report placeholder.

This intentionally does not perform a network fetch. It records the deterministic
local mirror state and the future upstream comparison target.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
BINDING = ARTIFACT_ROOT / "workspace-inventory-source.v0.1.json"
MIRROR = ARTIFACT_ROOT / "canonical-repo-estate.mirror.v1.0.json"
OUT = ARTIFACT_ROOT / "workspace-inventory-sync-report.generated.csv"
FIELDNAMES = [
    "check_id",
    "status",
    "source_repository",
    "source_artifact_path",
    "local_artifact_path",
    "pinning_mode",
    "expected_git_blob_sha",
    "network_policy",
    "notes",
]


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def build_row() -> dict[str, str]:
    binding = load_json(BINDING)
    mirror = load_json(MIRROR)
    return {
        "check_id": "workspace_inventory_upstream_sync",
        "status": "deferred",
        "source_repository": str(binding.get("source_repository", "SocioProphet/workspace-inventory")),
        "source_artifact_path": str(binding.get("source_artifact_path", "exports/canonical-repo-estate.v1.0.csv")),
        "local_artifact_path": str(mirror.get("local_artifact_path", "architecture/service-register/canonical-repo-estate.v1.0.csv")),
        "pinning_mode": str(mirror.get("pinning_mode", "git-blob-sha")),
        "expected_git_blob_sha": str(mirror.get("expected_git_blob_sha", "")),
        "network_policy": "no-network-in-service-register-ci",
        "notes": "Normal service-register CI validates the pinned local mirror only. Networked upstream comparison belongs in a future explicit sync/update job.",
    }


def render_csv() -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=FIELDNAMES, lineterminator="\n")
    writer.writeheader()
    writer.writerow(build_row())
    return buffer.getvalue()


def write_report() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render_csv(), encoding="utf-8")
    print(f"OK: generated {OUT.relative_to(ROOT)}")
    return 0


def check_report() -> int:
    expected = render_csv()
    if not OUT.exists():
        print(f"ERR: missing generated report: {OUT.relative_to(ROOT)}")
        return 2
    actual = OUT.read_text(encoding="utf-8")
    if actual != expected:
        print(f"ERR: stale generated report: {OUT.relative_to(ROOT)}")
        print("Run: python3 tools/generate_workspace_inventory_sync_report.py")
        return 2
    print(f"OK: {OUT.relative_to(ROOT)} is fresh")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the checked-in generated report is stale")
    args = parser.parse_args()
    if args.check:
        return check_report()
    return write_report()


if __name__ == "__main__":
    raise SystemExit(main())
