#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"
SCHEMA = BASE / "repo-governance-observation.v0.schema.json"
VALID = BASE / "fixtures" / "valid.repo-governance-observations.v0.json"
INVALID = BASE / "fixtures" / "invalid.repo-governance-observation.missing-source-sha.v0.json"

REQUIRED_OBSERVATION_KEYS = {
    "schema_version",
    "observation_id",
    "subject_repository",
    "surface",
    "predicate",
    "value",
    "source_path",
    "source_blob_sha",
    "parser_id",
    "extraction_method",
    "confidence",
    "temporal_validity",
    "evidence_digest",
}
REQUIRED_SURFACES = {
    "spine_registry",
    "manifest_overlay",
    "canonical_sources",
    "boundaries",
    "topology",
    "corpus_loop_pin",
}
ALLOWED_PREDICATES = {
    "declares_repo",
    "declares_role",
    "declares_boundary",
    "declares_namespace",
    "mentions_repo",
    "pins_source",
}
ALLOWED_CONFIDENCE = {"exact", "derived", "heuristic"}
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_observation(item: dict, index: int) -> list[str]:
    errors = []
    missing = REQUIRED_OBSERVATION_KEYS - set(item)
    if missing:
        errors.append(f"observation {index} missing keys: {sorted(missing)}")
        return errors
    if item["schema_version"] != "0.1":
        errors.append(f"observation {index} schema_version must be 0.1")
    if not str(item["observation_id"]).startswith("obs:"):
        errors.append(f"observation {index} observation_id must start with obs:")
    if not REPO_RE.match(item["subject_repository"]):
        errors.append(f"observation {index} subject_repository must be org/repo")
    if item["surface"] not in REQUIRED_SURFACES:
        errors.append(f"observation {index} invalid surface {item['surface']}")
    if item["predicate"] not in ALLOWED_PREDICATES:
        errors.append(f"observation {index} invalid predicate {item['predicate']}")
    if not SHA1_RE.match(item["source_blob_sha"]):
        errors.append(f"observation {index} source_blob_sha must be 40 hex characters")
    if not item["parser_id"]:
        errors.append(f"observation {index} parser_id must be non-empty")
    if not item["extraction_method"]:
        errors.append(f"observation {index} extraction_method must be non-empty")
    if item["confidence"] not in ALLOWED_CONFIDENCE:
        errors.append(f"observation {index} invalid confidence {item['confidence']}")
    temporal = item["temporal_validity"]
    if not isinstance(temporal, dict) or "valid_at" not in temporal or "valid_until" not in temporal:
        errors.append(f"observation {index} temporal_validity must include valid_at and valid_until")
    if not SHA256_RE.match(item["evidence_digest"]):
        errors.append(f"observation {index} evidence_digest must be 64 hex characters")
    return errors


def validate_packet(packet: dict) -> list[str]:
    errors = []
    if packet.get("schema_version") != "0.1":
        errors.append("packet schema_version must be 0.1")
    if packet.get("kind") != "repo_governance_observation_set":
        errors.append("packet kind must be repo_governance_observation_set")
    observations = packet.get("observations")
    if not isinstance(observations, list) or not observations:
        errors.append("observations must be a non-empty list")
        return errors
    surfaces = set()
    for index, item in enumerate(observations):
        surfaces.add(item.get("surface"))
        errors.extend(validate_observation(item, index))
    missing_surfaces = REQUIRED_SURFACES - surfaces
    if missing_surfaces:
        errors.append(f"missing observation surfaces: {sorted(missing_surfaces)}")
    return errors


def main() -> int:
    failed = False
    schema = load_json(SCHEMA)
    if schema.get("title") != "Repo Governance Observation":
        fail("schema title mismatch")
        failed = True
    required = set(schema.get("required", []))
    missing_schema_keys = REQUIRED_OBSERVATION_KEYS - required
    if missing_schema_keys:
        fail(f"schema missing required observation keys: {sorted(missing_schema_keys)}")
        failed = True

    valid_errors = validate_packet(load_json(VALID))
    if valid_errors:
        fail("valid observation fixture failed: " + "; ".join(valid_errors))
        failed = True

    invalid_errors = validate_packet(load_json(INVALID))
    if not invalid_errors:
        fail("invalid observation fixture unexpectedly passed")
        failed = True
    if not any("source_blob_sha" in err for err in invalid_errors):
        fail("invalid observation fixture did not fail on missing source_blob_sha")
        failed = True

    if failed:
        return 1
    print("OK: repo governance observation schema and fixtures validate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
