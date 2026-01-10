from pathlib import Path
import hashlib
import sys

from .util import find_repo_root


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
