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
REPORT = ROOT / "reports" / "corpus-loop-v1-status.json"
REQUIRED = {"evidence", "ontology", "policy", "runtime", "ledger"}
EXPECTED_RESOLUTION = "not_enabled_in_this_tranche"
EXPECTED_STATUS = "pinned_declared"


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


def check_report(manifest: dict, report: dict) -> None:
    if report.get("loop_id") != manifest["loop_id"]:
        raise ValueError("report loop_id mismatch")
    if report.get("status") != EXPECTED_STATUS:
        raise ValueError("report status must be pinned_declared")
    if report.get("live_artifact_resolution") != EXPECTED_RESOLUTION:
        raise ValueError("report must declare unresolved live artifact resolution")
    if report.get("boundary", {}).get("sociosphere_owns_coordination") is not True:
        raise ValueError("report coordination boundary missing")
    if report.get("boundary", {}).get("sociosphere_owns_downstream_implementation") is not False:
        raise ValueError("report downstream ownership boundary mismatch")

    manifest_by_plane = {item["plane"]: item for item in manifest["components"]}
    report_by_plane = {item["plane"]: item for item in report.get("components", [])}
    if set(report_by_plane) != REQUIRED:
        raise ValueError("report required planes missing")
    for plane, item in manifest_by_plane.items():
        report_item = report_by_plane[plane]
        if report_item.get("repo") != item["repo"]:
            raise ValueError(f"report repo mismatch for {plane}")
        if report_item.get("pinned_commit") != item["pinned_commit"]:
            raise ValueError(f"report pin mismatch for {plane}")
        if report_item.get("resolution_status") != "declared_not_live_verified":
            raise ValueError(f"report resolution status mismatch for {plane}")


def validate(path: Path, schema: dict) -> None:
    data = load(path)
    jsonschema.validate(data, schema)
    check_manifest(data)


def main() -> int:
    schema = load(SCHEMA)
    manifest = load(VALID)
    jsonschema.validate(manifest, schema)
    check_manifest(manifest)
    check_report(manifest, load(REPORT))

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
    print("OK: corpus loop v1 manifest and status report validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
