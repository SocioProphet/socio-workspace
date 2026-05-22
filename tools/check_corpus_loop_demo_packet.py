#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("jsonschema is required: python3 -m pip install jsonschema") from exc

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "corpus-loop-demo-packet.schema.json"
PACKET = ROOT / "reports" / "corpus-loop-demo-packet.json"
REPORT = ROOT / "reports" / "corpus-loop-v1-resolution-report.json"
REQUIRED = {"evidence", "ontology", "policy", "runtime", "ledger"}


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("root must be object")
    return data


def main() -> int:
    schema = load(SCHEMA)
    packet = load(PACKET)
    report = load(REPORT)
    jsonschema.validate(packet, schema)

    packet_planes = {item["plane"] for item in packet["components"]}
    report_planes = {item["plane"] for item in report["components"]}
    if packet_planes != REQUIRED:
        raise SystemExit("packet required planes missing")
    if report_planes != REQUIRED:
        raise SystemExit("report required planes missing")
    if packet["loop_id"] != report["loop_id"]:
        raise SystemExit("packet/report loop mismatch")
    if packet["boundary"]["read_only"] is not True:
        raise SystemExit("packet must remain read-only")
    if packet["boundary"]["downstream_owner_policy"] != "owner_repos_retain_authority":
        raise SystemExit("downstream owner policy mismatch")

    report_by_plane = {item["plane"]: item for item in report["components"]}
    for item in packet["components"]:
        reported = report_by_plane[item["plane"]]
        if item["repo"] != reported["repo"]:
            raise SystemExit("repo mismatch")
        if item["pinned_commit"] != reported["pinned_commit"]:
            raise SystemExit("pin mismatch")
        if item["status"] != reported["status"]:
            raise SystemExit("status mismatch")
        if item["artifact_count"] != len(reported["artifacts"]):
            raise SystemExit("artifact count mismatch")
    print("OK: corpus loop demo packet validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
