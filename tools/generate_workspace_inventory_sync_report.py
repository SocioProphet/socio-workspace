#!/usr/bin/env python3
"""Generate the Workspace Inventory sync report placeholder.

This intentionally does not perform a network fetch. It records the deterministic
local mirror state and the future upstream comparison target.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
BINDING = ARTIFACT_ROOT / "workspace-inventory-source.v0.1.json"
MIRROR = ARTIFACT_ROOT / "canonical-repo-estate.mirror.v1.0.json"
OUT = ARTIFACT_ROOT / "workspace-inventory-sync-report.generated.csv"


def load_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def main() -> int:
    binding = load_json(BINDING)
    mirror = load_json(MIRROR)

    row = {
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

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = [
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
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(row)

    print(f"OK: generated {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
