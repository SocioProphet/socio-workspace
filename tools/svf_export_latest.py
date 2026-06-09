#!/usr/bin/env python3
"""
svf_export_latest — copy the most recent local-smoke run into exports/latest/
and update the export manifest with real digests.

Run after svf-runner-run-smoke via: make svf-export-latest

Boundary:
- Reads from artifacts/svf/runs/local-smoke/
- Writes to artifacts/svf/exports/latest/
- Does not execute SVF actions
- Does not issue or sign receipts
- Does not certify production readiness
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_SRC = ROOT / "artifacts/svf/runs/local-smoke/validation-run.json"
RECEIPT_SRC = ROOT / "artifacts/svf/runs/local-smoke/validation-receipt.json"
EXPORT_DIR = ROOT / "artifacts/svf/exports/latest"
MANIFEST = EXPORT_DIR / "export-manifest.json"

FIXED_MANIFEST_FIELDS = {
    "schema_version": "1.0",
    "export_id": "svf:export:sociosphere.registry-dogfood.latest",
    "repo": "SocioProphet/sociosphere",
    "profile_ref": "svf:profile:sociosphere.dogfood",
    "plan_ref": "svf:plan:sociosphere.registry-dogfood",
    "policy_ref": "svf:policy:sociosphere.local-readonly",
    "run_artifact": "artifacts/svf/exports/latest/validation-run.json",
    "receipt_artifact": "artifacts/svf/exports/latest/validation-receipt.json",
    "verification_status": "verified",
    "certified_claims": [
        "schema_conformant",
        "non_production_only",
        "policy_boundary_preserved",
        "artifact_integrity_verified",
        "receipt_integrity_verified",
    ],
    "non_certified_claims": [
        "production_readiness",
        "live_infrastructure_safety",
        "container_runtime_parity",
        "browser_runtime_parity",
        "qemu_runtime_parity",
        "signadot_vendor_parity",
        "network_isolation_enforced",
    ],
    "downstream_consumers": [
        "SocioProphet/prophet-platform#549",
        "SocioProphet/prophet-platform#588",
    ],
    "non_claims": [
        "Export manifest identifies stable SVF run and receipt artifacts for downstream consumers.",
        "Export manifest does not authorize downstream systems to issue or sign Sociosphere receipts.",
        "Export manifest does not certify production readiness, live infrastructure safety, or Signadot vendor parity.",
    ],
}


def sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if not RUN_SRC.exists():
        print(f"ERROR: run source missing: {RUN_SRC.relative_to(ROOT)}")
        return 1
    if not RECEIPT_SRC.exists():
        print(f"ERROR: receipt source missing: {RECEIPT_SRC.relative_to(ROOT)}")
        return 1

    run_data = json.loads(RUN_SRC.read_text(encoding="utf-8"))
    receipt_data = json.loads(RECEIPT_SRC.read_text(encoding="utf-8"))

    # Verify receipt before exporting
    if receipt_data.get("verification", {}).get("status") != "verified":
        print("ERROR: receipt is not verified — cannot export")
        return 1

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(RUN_SRC, EXPORT_DIR / "validation-run.json")
    shutil.copy2(RECEIPT_SRC, EXPORT_DIR / "validation-receipt.json")

    run_digest = sha256_hex(EXPORT_DIR / "validation-run.json")
    receipt_digest = sha256_hex(EXPORT_DIR / "validation-receipt.json")

    manifest = {
        **FIXED_MANIFEST_FIELDS,
        "run_ref": run_data["run_ref"],
        "receipt_ref": receipt_data["receipt_id"],
        "run_digest": {"algorithm": "sha256", "digest": run_digest},
        "receipt_digest": {"algorithm": "sha256", "digest": receipt_digest},
        "exported_at": run_data["ended_at"],
    }

    MANIFEST.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = {
        "tool": "sociosphere.svf_export_latest.v1",
        "run_ref": manifest["run_ref"],
        "receipt_ref": manifest["receipt_ref"],
        "run_digest": run_digest[:16] + "…",
        "receipt_digest": receipt_digest[:16] + "…",
        "exported_at": manifest["exported_at"],
        "non_claims": [
            "Does not execute SVF actions.",
            "Does not issue or sign receipts.",
            "Does not certify production readiness or vendor parity.",
        ],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    print("OK: svf-export-latest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
