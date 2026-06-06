#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "health-ai" / "health-ai-eval-readiness.planning.json"
REGISTRY = ROOT / "registry" / "health-ai" / "health-ai-eval-readiness.v0.json"

REQUIRED_BLOCKS = {
    "production_ready",
    "patient_care_action",
    "autonomous_clinical_action",
    "customer_facing_healthcare_claim",
    "real_clinical_data_processing",
    "protected_benchmark_reproduction"
}

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> int:
    errors: list[str] = []

    try:
        fixture = load(FIXTURE)
        registry = load(REGISTRY)
    except Exception as exc:
        print(f"ERR: failed to load readiness artifacts: {exc}", file=sys.stderr)
        return 2

    for name, record in (("fixture", fixture), ("registry", registry)):
        if record.get("production_ready") is not False:
            errors.append(f"{name}: production_ready must be false")
        if record.get("patient_care_action") is not False:
            errors.append(f"{name}: patient_care_action must be false")
        if record.get("autonomous_clinical_action") is not False:
            errors.append(f"{name}: autonomous_clinical_action must be false")
        if record.get("customer_facing_healthcare_claim") is not False:
            errors.append(f"{name}: customer_facing_healthcare_claim must be false")
        if record.get("next_allowed_action") != "planning_record_only":
            errors.append(f"{name}: next_allowed_action must be planning_record_only")

    if fixture.get("readiness_state") != "planning_only":
        errors.append("fixture readiness_state must be planning_only")
    if registry.get("state") != "planning_only":
        errors.append("registry state must be planning_only")

    missing = REQUIRED_BLOCKS - set(fixture.get("blocked_from", []))
    if missing:
        errors.append(f"fixture missing blocked_from entries: {sorted(missing)}")

    required_inputs = [
        "health-eval-rubric.schema.json",
        "clinical-value-claim.schema.json",
        "health-ai-search-packet.schema.json"
    ]
    inputs = fixture.get("validated_inputs", [])
    for fragment in required_inputs:
        if not any(fragment in item for item in inputs):
            errors.append(f"fixture missing validated input containing {fragment}")

    if errors:
        print("ERR: Health AI readiness validation failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    print("Health AI readiness validates as planning_only.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
