#!/usr/bin/env python3
"""Validate the Sociosphere SVF exported receipt manifest fixture."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "svf" / "exports" / "latest" / "export-manifest.json"
REQUIRED_FIELDS = {
    "schema_version",
    "export_id",
    "repo",
    "profile_ref",
    "plan_ref",
    "policy_ref",
    "run_ref",
    "receipt_ref",
    "run_artifact",
    "receipt_artifact",
    "run_digest",
    "receipt_digest",
    "exported_at",
    "verification_status",
    "certified_claims",
    "non_certified_claims",
    "non_claims",
}
REQUIRED_NON_CERTIFIED = {
    "production_readiness",
    "live_infrastructure_safety",
    "signadot_vendor_parity",
}
SUPPORTED_CERTIFIED = {
    "schema_conformant",
    "fixtures_validated",
    "tests_passed",
    "semantic_roundtrip_preserved",
    "policy_boundary_preserved",
    "non_production_only",
    "runtime_smoke_passed",
    "artifact_integrity_verified",
    "receipt_integrity_verified",
}


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def digest_record_valid(record: Any) -> bool:
    return (
        isinstance(record, dict)
        and record.get("algorithm") == "sha256"
        and isinstance(record.get("digest"), str)
        and len(record["digest"]) == 64
    )


def sha256_of_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    manifest = load(MANIFEST)
    problems: list[str] = []

    missing = sorted(REQUIRED_FIELDS - set(manifest))
    problems.extend(f"missing required field: {field}" for field in missing)

    if manifest.get("schema_version") != "1.0":
        problems.append("schema_version must equal 1.0")
    if manifest.get("repo") != "SocioProphet/sociosphere":
        problems.append("repo must be SocioProphet/sociosphere")
    if manifest.get("export_id") != "svf:export:sociosphere.registry-dogfood.latest":
        problems.append("unexpected export_id")
    if manifest.get("profile_ref") != "svf:profile:sociosphere.dogfood":
        problems.append("profile_ref must be Sociosphere dogfood profile")
    if manifest.get("plan_ref") != "svf:plan:sociosphere.registry-dogfood":
        problems.append("plan_ref must be Sociosphere registry dogfood plan")
    if manifest.get("policy_ref") != "svf:policy:sociosphere.local-readonly":
        problems.append("policy_ref must be local-readonly policy")
    if not str(manifest.get("run_ref", "")).startswith("svf:run:"):
        problems.append("run_ref must start with svf:run:")
    if not str(manifest.get("receipt_ref", "")).startswith("svf:receipt:"):
        problems.append("receipt_ref must start with svf:receipt:")
    if manifest.get("run_ref") == manifest.get("receipt_ref"):
        problems.append("run_ref and receipt_ref must be distinct")
    if manifest.get("verification_status") != "verified":
        problems.append("verification_status must be verified for latest positive export fixture")

    if not str(manifest.get("run_artifact", "")).startswith("artifacts/svf/exports/latest/"):
        problems.append("run_artifact must be under artifacts/svf/exports/latest/")
    if not str(manifest.get("receipt_artifact", "")).startswith("artifacts/svf/exports/latest/"):
        problems.append("receipt_artifact must be under artifacts/svf/exports/latest/")
    if not digest_record_valid(manifest.get("run_digest")):
        problems.append("run_digest must be a sha256 digest record")
    if not digest_record_valid(manifest.get("receipt_digest")):
        problems.append("receipt_digest must be a sha256 digest record")

    certified = set(manifest.get("certified_claims", [])) if isinstance(manifest.get("certified_claims"), list) else set()
    unsupported = sorted(certified - SUPPORTED_CERTIFIED)
    if unsupported:
        problems.append(f"unsupported certified claims: {unsupported}")
    for claim in ("schema_conformant", "non_production_only", "receipt_integrity_verified"):
        if claim not in certified:
            problems.append(f"certified_claims must include {claim}")

    non_certified = set(manifest.get("non_certified_claims", [])) if isinstance(manifest.get("non_certified_claims"), list) else set()
    missing_non = sorted(REQUIRED_NON_CERTIFIED - non_certified)
    if missing_non:
        problems.append(f"non_certified_claims missing required non-claims: {missing_non}")

    # Artifact files must exist and match manifest digests
    run_artifact = manifest.get("run_artifact", "")
    receipt_artifact = manifest.get("receipt_artifact", "")
    run_path = ROOT / run_artifact if run_artifact else None
    receipt_path = ROOT / receipt_artifact if receipt_artifact else None

    if run_path and not run_path.exists():
        problems.append(f"run_artifact file missing: {run_artifact}")
    elif run_path and run_path.exists():
        actual_run_digest = sha256_of_file(run_path)
        expected_run_digest = (manifest.get("run_digest") or {}).get("digest", "")
        if actual_run_digest != expected_run_digest:
            problems.append(
                f"run_artifact digest mismatch: manifest={expected_run_digest[:16]}… "
                f"actual={actual_run_digest[:16]}…"
            )

    if receipt_path and not receipt_path.exists():
        problems.append(f"receipt_artifact file missing: {receipt_artifact}")
    elif receipt_path and receipt_path.exists():
        actual_receipt_digest = sha256_of_file(receipt_path)
        expected_receipt_digest = (manifest.get("receipt_digest") or {}).get("digest", "")
        if actual_receipt_digest != expected_receipt_digest:
            problems.append(
                f"receipt_artifact digest mismatch: manifest={expected_receipt_digest[:16]}… "
                f"actual={actual_receipt_digest[:16]}…"
            )

    non_claims = manifest.get("non_claims", [])
    for phrase in (
        "does not authorize downstream systems",
        "does not certify production readiness",
        "Signadot vendor parity",
    ):
        if not any(isinstance(item, str) and phrase in item for item in non_claims):
            problems.append(f"non_claims must include phrase: {phrase}")

    report = {
        "validator": "sociosphere.svf-export-manifest.validator.v1",
        "passed": not problems,
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "problems": problems,
        "non_claims": [
            "Validator checks the exported manifest fixture only.",
            "Validator does not execute SVF actions.",
            "Validator does not issue or sign receipts.",
            "Validator does not certify production readiness or vendor parity.",
        ],
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    print(("PASS" if not problems else "FAIL") + ": svf export manifest")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
