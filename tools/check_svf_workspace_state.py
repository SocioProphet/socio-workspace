#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "sovereign-validation-fabric.yaml"
NEEDED = {
    "SocioProphet/sociosphere",
    "SocioProphet/ProCybernetica",
    "SocioProphet/SCOPE-D",
    "SocioProphet/ontogenesis",
    "SourceOS-Linux/sourceos-spec",
}


def row(profile):
    command = profile.get("validation_command")
    notes = []
    if command:
        status = "selected_missing_observation"
        notes.append("validation_observation_missing")
    else:
        status = "not_configured"
        notes.append("validation_command_missing")
    if not profile.get("contract_refs", []):
        notes.append("contract_refs_missing")
    return {
        "repo": profile.get("repo"),
        "profile_id": profile.get("profile_id"),
        "status": status,
        "validation_command": command,
        "warnings": notes,
        "evidence_refs": [],
    }


def main():
    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    profiles = registry.get("profiles", [])
    rows = [row(p) for p in profiles if isinstance(p, dict)]
    repos = {r["repo"] for r in rows}
    problems = []
    missing = sorted(NEEDED - repos)
    if missing:
        problems.append({"check": "needed-repos-present", "missing": missing})
    for item in rows:
        if item["validation_command"] and "validation_observation_missing" not in item["warnings"]:
            problems.append({"check": "missing-observation-explicit", "repo": item["repo"]})
        if item["evidence_refs"] != []:
            problems.append({"check": "evidence-refs-empty-before-observation", "repo": item["repo"]})
    passed = not problems
    print(json.dumps({"passed": passed, "rows": rows, "problems": problems}, indent=2, sort_keys=True))
    print(("PASS" if passed else "FAIL") + ": svf workspace state")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
