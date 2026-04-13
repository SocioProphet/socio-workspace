#!/usr/bin/env python3
import sys
from pathlib import Path

try:
    import yaml  # PyYAML
except Exception as e:
    print("[fail] PyYAML not installed. Install with: python -m pip install pyyaml", file=sys.stderr)
    raise

REQ_TOP = ["spec_version", "name", "principles", "planes", "receptors", "pathways", "checkpoints", "apoptosis_quarantine"]

def fail(msg: str) -> None:
    print(f"[fail] {msg}", file=sys.stderr)
    sys.exit(2)

def main() -> None:
    p = Path("specs/biology/pathway-map.v0.1.yaml")
    if not p.exists():
        fail(f"Missing {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("Spec root must be a mapping/object")

    for k in REQ_TOP:
        if k not in data:
            fail(f"Missing top-level key: {k}")

    # Minimal structural checks
    if not isinstance(data["receptors"], list) or len(data["receptors"]) == 0:
        fail("receptors must be a non-empty list")
    if not isinstance(data["pathways"], list) or len(data["pathways"]) == 0:
        fail("pathways must be a non-empty list")

    # Ensure every pathway has negative_feedback
    for pw in data["pathways"]:
        pid = pw.get("id", "<missing-id>")
        if "negative_feedback" not in pw or not pw["negative_feedback"]:
            fail(f"pathway {pid} missing negative_feedback controls")

    # Ensure apoptosis evidence requirements exist
    aq = data["apoptosis_quarantine"]
    if "evidence_requirements" not in aq or not aq["evidence_requirements"]:
        fail("apoptosis_quarantine must specify evidence_requirements")

    print("[ok] biology spec validated")

if __name__ == "__main__":
    main()
