#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("jsonschema is required: python3 -m pip install jsonschema") from exc

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "corpus-loop-v1" / "valid.watson-cyc-chronos.pinned.json"
RESOLUTION_REPORT = ROOT / "reports" / "corpus-loop-v1-resolution-report.json"
PACKET_SCHEMA = ROOT / "schemas" / "corpus-loop-demo-packet.schema.json"
READOUT_SCHEMA = ROOT / "schemas" / "corpus-loop-customer-readout.schema.json"
PACKET_OUT = ROOT / "reports" / "corpus-loop-demo-packet.json"
READOUT_OUT = ROOT / "reports" / "corpus-loop-customer-readout.json"

PLANE_LABELS = {
    "evidence": "Evidence",
    "ontology": "Ontology",
    "policy": "Policy",
    "runtime": "Agent carrier",
    "ledger": "Ledger",
}


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be object")
    return data


def dump(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2) + "\n"


def build_packet(manifest: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    report_by_plane = {item["plane"]: item for item in report["components"]}
    components = []
    for item in manifest["components"]:
        plane = item["plane"]
        reported = report_by_plane[plane]
        components.append(
            {
                "plane": plane,
                "repo": item["repo"],
                "merged_ref": item["merged_ref"],
                "pinned_commit": item["pinned_commit"],
                "status": reported["status"],
                "artifact_count": len(reported["artifacts"]),
            }
        )
    return {
        "schema_version": "0.1",
        "kind": "corpus_loop_demo_packet",
        "packet_id": "watson-cyc-semantic-web-chronos-demo-v0",
        "source_manifest": str(MANIFEST.relative_to(ROOT)),
        "source_report": str(RESOLUTION_REPORT.relative_to(ROOT)),
        "loop_id": manifest["loop_id"],
        "status": "ready_read_only" if all(item["status"] == "found" for item in components) else "partial",
        "components": components,
        "checks": {
            "positive": [
                "Five owner planes present",
                "All carrier commits pinned",
                "All referenced carrier artifacts found",
                "Workbench has generated v1 data",
                "SocioSphere remains coordination owner only",
            ],
            "negative": [
                "Missing carrier plane rejected",
                "Missing pinned commit rejected",
                "Downstream ownership claim rejected",
                "Missing artifact reported by resolver",
                "Review-only evidence remains non-admissible for implementation-safe status",
            ],
        },
        "boundary": {
            "read_only": True,
            "coordination_owner": "SocioProphet/sociosphere",
            "downstream_owner_policy": "owner_repos_retain_authority",
        },
    }


def build_readout(packet: dict[str, Any]) -> dict[str, Any]:
    found_count = sum(1 for item in packet["components"] if item["status"] == "found")
    artifact_count = sum(int(item["artifact_count"]) for item in packet["components"])
    return {
        "schema_version": "0.1",
        "kind": "corpus_loop_customer_readout",
        "readout_id": "watson-cyc-semantic-web-chronos-readout-v0",
        "source_packet": str(PACKET_OUT.relative_to(ROOT)),
        "title": "Governed neuro-symbolic corpus loop",
        "summary": (
            "A read-only demonstration packet showing that the Watson/Cyc/Semantic-Web/CHRONOS "
            "corpus substrate has been converted into a governed, live-resolved, cross-repo carrier "
            "loop across evidence, ontology, policy, agent carrier, and ledger planes."
        ),
        "proof_points": [
            "The source corpus is captured in SocioProphet/sociosphere#334.",
            f"{found_count} of 5 downstream owner planes have found carrier surfaces.",
            "All five carrier commits are pinned in the v1 manifest.",
            f"All {artifact_count} referenced carrier artifacts are represented in the resolution report.",
            "The demo packet validates as read-only and coordination-only.",
            "The corpus-loop workflow and local aggregate check validate the committed surfaces.",
        ],
        "safe_claims": [
            "The current state is a governed scaffold, not a production runtime.",
            "The loop is suitable for a read-only product demonstration and architecture review.",
            "SocioSphere owns coordination and topology validation while downstream repos retain their carrier ownership.",
        ],
        "non_claims": [
            "This readout does not claim live runtime execution.",
            "This readout does not claim autonomous external effects.",
            "This readout does not claim production storage integration.",
            "This readout does not claim completed corpus normalization.",
            "This readout does not claim patent or license clearance for artifact reuse.",
            "This readout does not move downstream implementation ownership into SocioSphere.",
        ],
        "next_step": "Promote from read-only packet to a bounded demo assembler that emits a demo artifact from the manifest without invoking downstream actions.",
    }


def validate_outputs(packet: dict[str, Any], readout: dict[str, Any]) -> None:
    jsonschema.validate(packet, load(PACKET_SCHEMA))
    jsonschema.validate(readout, load(READOUT_SCHEMA))
    if packet["boundary"]["read_only"] is not True:
        raise ValueError("packet must be read-only")
    if packet["boundary"]["downstream_owner_policy"] != "owner_repos_retain_authority":
        raise ValueError("packet owner policy mismatch")
    if readout["source_packet"] != str(PACKET_OUT.relative_to(ROOT)):
        raise ValueError("readout source packet mismatch")


def check_or_write(path: Path, content: str, *, write: bool) -> None:
    if write:
        path.write_text(content, encoding="utf-8")
        return
    current = path.read_text(encoding="utf-8")
    if current != content:
        raise SystemExit(f"generated artifact is stale: {path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    manifest = load(MANIFEST)
    report = load(RESOLUTION_REPORT)
    packet = build_packet(manifest, report)
    readout = build_readout(packet)
    validate_outputs(packet, readout)
    check_or_write(PACKET_OUT, dump(packet), write=args.write)
    check_or_write(READOUT_OUT, dump(readout), write=args.write)
    print("OK: corpus loop demo packet and customer readout are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
