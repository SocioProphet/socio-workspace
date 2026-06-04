#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "registry" / "resource-intake-adoption.yaml"
REQUIRED_AUTHORITY_SURFACES = {
    "learningLoop": "SocioProphet/systems-learning-loops",
    "valueMeasurement": "SocioProphet/economic-prophet",
    "estateGovernance": "SocioProphet/sociosphere",
}
REQUIRED_ADOPTION_FIELDS = {
    "id",
    "status",
    "sourceCorpus",
    "receivingRepo",
    "receivingFiles",
    "gates",
    "downstreamConsumers",
    "nextSteps",
}
REQUIRED_SOURCE_FIELDS = {
    "repo",
    "license",
    "intakeMode",
    "runtimeDependency",
}
REQUIRED_GATE_FRAGMENTS = [
    "runtime dependency must remain false",
    "advisory-only",
    "lambda_admit must not exceed lambda_evid",
    "lambda_release must not exceed lambda_admit",
    "residual must equal lambda_evid minus lambda_release",
]


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"registry must be a mapping: {path}")
    return data


def check(check_id: str, passed: bool, diagnostics: list[str] | None = None) -> dict[str, Any]:
    return {"check_id": check_id, "passed": bool(passed), "diagnostics": diagnostics or []}


def _missing(mapping: dict[str, Any], required: set[str]) -> list[str]:
    return sorted(key for key in required if key not in mapping)


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def validate_authority_surfaces(data: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    surfaces = data.get("authoritySurfaces", {})
    if not isinstance(surfaces, dict):
        return [check("authority-surfaces:mapping", False, ["authoritySurfaces must be a mapping"])]

    for key, expected_repo in REQUIRED_AUTHORITY_SURFACES.items():
        surface = surfaces.get(key)
        if not isinstance(surface, dict):
            results.append(check(f"authority-surfaces:{key}:present", False, [f"{key} missing"]))
            continue
        diagnostics = []
        if surface.get("repo") != expected_repo:
            diagnostics.append(f"repo must be {expected_repo}")
        if not surface.get("role"):
            diagnostics.append("role is required")
        results.append(check(f"authority-surfaces:{key}", not diagnostics, diagnostics))
    return results


def validate_adoption(adoption: dict[str, Any]) -> list[dict[str, Any]]:
    adoption_id = str(adoption.get("id", "unknown"))
    results: list[dict[str, Any]] = []

    missing_fields = _missing(adoption, REQUIRED_ADOPTION_FIELDS)
    results.append(check(f"adoption:{adoption_id}:required-fields", not missing_fields, missing_fields))

    source = adoption.get("sourceCorpus", {})
    source_missing = _missing(source, REQUIRED_SOURCE_FIELDS) if isinstance(source, dict) else sorted(REQUIRED_SOURCE_FIELDS)
    source_diagnostics = list(source_missing)
    if isinstance(source, dict) and source.get("runtimeDependency") is not False:
        source_diagnostics.append("sourceCorpus.runtimeDependency must be false")
    results.append(check(f"adoption:{adoption_id}:source-corpus", not source_diagnostics, source_diagnostics))

    receiving_files = adoption.get("receivingFiles")
    results.append(check(
        f"adoption:{adoption_id}:receiving-files",
        _nonempty_list(receiving_files),
        [] if _nonempty_list(receiving_files) else ["receivingFiles must be a non-empty list"],
    ))

    gates = adoption.get("gates")
    gate_diagnostics: list[str] = []
    if not _nonempty_list(gates):
        gate_diagnostics.append("gates must be a non-empty list")
    else:
        joined_gates = " ".join(str(item).lower() for item in gates)
        for fragment in REQUIRED_GATE_FRAGMENTS:
            if fragment not in joined_gates:
                gate_diagnostics.append(f"missing gate fragment: {fragment}")
    results.append(check(f"adoption:{adoption_id}:gates", not gate_diagnostics, gate_diagnostics))

    downstream = adoption.get("downstreamConsumers")
    downstream_diagnostics: list[str] = []
    if not _nonempty_list(downstream):
        downstream_diagnostics.append("downstreamConsumers must be a non-empty list")
    else:
        for expected in ["SocioProphet/economic-prophet", "SocioProphet/systems-learning-loops", "SocioProphet/sociosphere"]:
            if expected not in downstream:
                downstream_diagnostics.append(f"downstreamConsumers must include {expected}")
    results.append(check(f"adoption:{adoption_id}:downstream-consumers", not downstream_diagnostics, downstream_diagnostics))

    next_steps = adoption.get("nextSteps")
    results.append(check(
        f"adoption:{adoption_id}:next-steps",
        _nonempty_list(next_steps),
        [] if _nonempty_list(next_steps) else ["nextSteps must be a non-empty list"],
    ))

    return results


def validate_registry(data: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = [
        check("api-version", data.get("apiVersion") == "sociosphere.socioprophet.io/v1alpha1"),
        check("kind", data.get("kind") == "ResourceIntakeAdoptionRegistry"),
        check("metadata-authority", data.get("metadata", {}).get("authorityRepo") == "SocioProphet/sociosphere"),
    ]
    results.extend(validate_authority_surfaces(data))

    adoptions = data.get("adoptions", [])
    if not _nonempty_list(adoptions):
        results.append(check("adoptions:non-empty", False, ["adoptions must be a non-empty list"]))
        return results

    ids: set[str] = set()
    duplicate_ids: set[str] = set()
    for adoption in adoptions:
        if not isinstance(adoption, dict):
            results.append(check("adoptions:item-mapping", False, ["each adoption must be a mapping"]))
            continue
        adoption_id = str(adoption.get("id", ""))
        if adoption_id in ids:
            duplicate_ids.add(adoption_id)
        ids.add(adoption_id)
        results.extend(validate_adoption(adoption))
    results.append(check("adoptions:unique-ids", not duplicate_ids, sorted(duplicate_ids)))
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default=str(DEFAULT_REGISTRY))
    args = parser.parse_args()

    path = Path(args.path)
    data = load_yaml(path)
    results = validate_registry(data)
    passed = all(item["passed"] for item in results)
    print(json.dumps({"validator": "sociosphere.resource-intake-adoption.validator.v1", "path": str(path), "passed": passed, "results": results}, indent=2, sort_keys=True))
    print(("PASS" if passed else "FAIL") + ": resource intake adoption registry")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
