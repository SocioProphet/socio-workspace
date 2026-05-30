#!/usr/bin/env python3
"""Rehydrate large service-register CSV artifacts from gzipped base64 chunks.

The connector may reject larger CSV uploads. This script reconstructs exact CSV
artifacts before validators run when chunk files are present under
architecture/service-register/artifact-chunks/.
"""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
CHUNK_ROOT = ARTIFACT_ROOT / "artifact-chunks"

TARGETS = [
    "service-architecture-register.v1.0.csv",
    "service-dependency-edges.v0.1.csv",
]


def main() -> int:
    print("SocioSphere service-register artifact rehydration")
    if not CHUNK_ROOT.exists():
        print("WARN: artifact chunk directory missing; nothing to rehydrate")
        return 0

    for target in TARGETS:
        parts = sorted(CHUNK_ROOT.glob(f"{target}.gz.b64.*"))
        if not parts:
            print(f"WARN: no chunks for {target}")
            continue
        payload = "".join(part.read_text(encoding="utf-8").strip() for part in parts)
        data = gzip.decompress(base64.b64decode(payload))
        out = ARTIFACT_ROOT / target
        out.write_bytes(data)
        print(f"OK: rehydrated {target} from {len(parts)} chunks; bytes={len(data)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
