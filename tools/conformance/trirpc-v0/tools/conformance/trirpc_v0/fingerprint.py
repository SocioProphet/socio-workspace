from pathlib import Path
import hashlib
import sys


def find_repo_root(start: Path) -> Path:
    # Prefer a repo root marker + schemas directory
    for d in [start, *start.parents]:
        if (d / "schemas").is_dir() and (
            (d / ".git").exists()
            or (d / "pyproject.toml").exists()
            or (d / "WORKSPACE.yaml").exists()
        ):
            return d
    # Fallback: nearest ancestor that has schemas/
    for d in [start, *start.parents]:
        if (d / "schemas").is_dir():
            return d
    return start.parents[0]


HERE = Path(__file__).resolve()
ROOT = find_repo_root(HERE.parent)

paths = [
    ROOT / "schemas/avro/trirpc/envelope.v0.avsc",
    ROOT / "schemas/avro/trirpc/value.v0.avsc",
    ROOT / "schemas/avro/trirpc/error.v0.avsc",
    ROOT / "schemas/schemasalad/trirpc-schema-bundle.v0.yml",
]

h = hashlib.sha256()
for p in paths:
    if not p.exists():
        print(f"ERR: missing {p}")
        sys.exit(2)
    h.update(p.read_bytes())

print("TRIRPC_V0_SCHEMA_SHA256", h.hexdigest())
