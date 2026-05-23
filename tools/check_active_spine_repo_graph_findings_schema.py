#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"
SCHEMA = BASE / "active-spine.repo-graph.findings.schema.json"
VALID = BASE / "fixtures" / "valid.active-spine.repo-graph.findings.json"
INVALID = BASE / "fixtures" / "invalid.missing-finding-kind.repo-graph.findings.json"

REQUIRED_FINDING_KINDS = {
    "blocked-non-actionable",
    "missing-surface",
    "policy-review-required",
    "promotion-ready",
    "stale-pin",
}
ALLOWED_SEVERITIES = {"info", "warn", "review"}


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_packet(packet: dict) -> list[str]:
    errors = []
    required = {"schema_version", "kind", "corpus_loop", "generated_from", "finding_kinds", "findings"}
    missing = required - set(packet)
    if missing:
        errors.append(f"missing packet keys: {sorted(missing)}")
    if packet.get("schema_version") != "0.1":
        errors.append("schema_version must be 0.1")
    if packet.get("kind") != "active_spine_repo_graph_findings":
        errors.append("kind must be active_spine_repo_graph_findings")
    if packet.get("corpus_loop") != "watson-cyc-semantic-web-chronos-v1":
        errors.append("unexpected corpus_loop")
    kinds = set(packet.get("finding_kinds", []))
    if not REQUIRED_FINDING_KINDS <= kinds:
        errors.append(f"missing finding kinds: {sorted(REQUIRED_FINDING_KINDS - kinds)}")
    if not isinstance(packet.get("findings"), list) or not packet.get("findings"):
        errors.append("findings must be a non-empty list")
        return errors
    observed = set()
    for index, item in enumerate(packet["findings"]):
        for key in ["kind", "repository", "severity", "reason", "actionable"]:
            if key not in item:
                errors.append(f"finding {index} missing {key}")
        kind = item.get("kind")
        observed.add(kind)
        if kind not in REQUIRED_FINDING_KINDS:
            errors.append(f"finding {index} has invalid kind {kind}")
        if item.get("severity") not in ALLOWED_SEVERITIES:
            errors.append(f"finding {index} has invalid severity {item.get('severity')}")
        if not isinstance(item.get("repository"), str) or not item.get("repository"):
            errors.append(f"finding {index} repository must be non-empty string")
        if not isinstance(item.get("reason"), str) or not item.get("reason"):
            errors.append(f"finding {index} reason must be non-empty string")
        if not isinstance(item.get("actionable"), bool):
            errors.append(f"finding {index} actionable must be boolean")
    if not REQUIRED_FINDING_KINDS <= observed:
        errors.append(f"findings missing observed kinds: {sorted(REQUIRED_FINDING_KINDS - observed)}")
    return errors


def main() -> int:
    failed = False
    schema = load_json(SCHEMA)
    if schema.get("title") != "Active Spine Repo Graph Findings":
        fail("schema title mismatch")
        failed = True
    if "finding" not in schema.get("$defs", {}):
        fail("schema missing finding definition")
        failed = True

    valid_errors = validate_packet(load_json(VALID))
    if valid_errors:
        fail("valid fixture failed: " + "; ".join(valid_errors))
        failed = True

    invalid_errors = validate_packet(load_json(INVALID))
    if not invalid_errors:
        fail("invalid fixture unexpectedly passed")
        failed = True
    if not any("missing finding kinds" in err for err in invalid_errors):
        fail("invalid fixture did not fail for missing finding kinds")
        failed = True

    if failed:
        return 1

    print("OK: active spine repo graph findings schema fixtures validate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
