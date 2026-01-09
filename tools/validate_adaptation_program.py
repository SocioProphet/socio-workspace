#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def parse_metric_ids_from_registry_yaml(text: str) -> set[str]:
    # Minimal YAML extraction (no external deps): look for lines like "  - id: f1.entity"
    ids = set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("id: "):
            ids.add(line.split("id:", 1)[1].strip())
        elif line.startswith("- id: "):
            ids.add(line.split("- id:", 1)[1].strip())
    return ids

def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("USAGE: tools/validate_adaptation_program.py <program.json> [<metric-registry.v1.yaml>]", file=sys.stderr)
        return 2

    program_path = Path(argv[1])
    reg_path = Path(argv[2]) if len(argv) >= 3 else Path("standards/metrics/metric-registry.v1.yaml")

    if not program_path.exists():
        print(f"ERR: missing program file: {program_path}", file=sys.stderr)
        return 2
    if not reg_path.exists():
        print(f"ERR: missing metric registry: {reg_path}", file=sys.stderr)
        return 2

    metric_ids = parse_metric_ids_from_registry_yaml(reg_path.read_text(encoding="utf-8"))
    if not metric_ids:
        print(f"ERR: could not parse any metric ids from registry: {reg_path}", file=sys.stderr)
        return 2

    prog = load_json(program_path)
    metrics = prog.get("metrics", [])
    bad = []
    for m in metrics:
        name = m.get("name")
        if not isinstance(name, str) or not name:
            bad.append(("__missing__", m))
        elif name not in metric_ids:
            bad.append((name, m))

    if bad:
        print("FAIL: program references unknown metrics (not in registry)")
        for name, obj in bad:
            print(f"  - {name}: {json.dumps(obj, sort_keys=True)}")
        print("\nFix: add metric IDs to standards/metrics/metric-registry.v1.yaml or change program.metrics[].name")
        return 1

    print("OK: program metric IDs are all registered")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

