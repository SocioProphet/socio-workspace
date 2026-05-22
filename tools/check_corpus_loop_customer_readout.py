#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

try:
    import jsonschema
except ImportError as exc:
    raise SystemExit("jsonschema is required: python3 -m pip install jsonschema") from exc

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "corpus-loop-customer-readout.schema.json"
READOUT = ROOT / "reports" / "corpus-loop-customer-readout.json"
PACKET = ROOT / "reports" / "corpus-loop-demo-packet.json"

REQUIRED_NON_CLAIMS = {
    "runtime",
    "external effects",
    "production storage",
    "corpus normalization",
    "patent or license clearance",
    "downstream implementation ownership",
}


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("root must be object")
    return data


def main() -> int:
    schema = load(SCHEMA)
    readout = load(READOUT)
    packet = load(PACKET)
    jsonschema.validate(readout, schema)

    if readout["source_packet"] != "reports/corpus-loop-demo-packet.json":
        raise SystemExit("readout source packet mismatch")
    if packet["boundary"]["read_only"] is not True:
        raise SystemExit("source packet must be read-only")
    if packet["boundary"]["downstream_owner_policy"] != "owner_repos_retain_authority":
        raise SystemExit("source packet owner policy mismatch")
    if readout["kind"] != "corpus_loop_customer_readout":
        raise SystemExit("unexpected readout kind")

    non_claim_text = "\n".join(readout["non_claims"]).lower()
    missing = [term for term in REQUIRED_NON_CLAIMS if term not in non_claim_text]
    if missing:
        raise SystemExit("readout missing required non-claim terms: " + ", ".join(sorted(missing)))

    if len(packet["components"]) != 5:
        raise SystemExit("source packet component count mismatch")
    if any(component["status"] != "found" for component in packet["components"]):
        raise SystemExit("source packet contains unresolved component")

    print("OK: corpus loop customer readout validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
