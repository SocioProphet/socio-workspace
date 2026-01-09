#!/usr/bin/env python3
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: tools/schema_fp.py <file> [file ...]", file=sys.stderr)
        return 2
    for a in argv[1:]:
        p = Path(a)
        if not p.exists():
            print(f"ERR: missing file: {p}", file=sys.stderr)
            return 2
        print(f"{sha256_file(p)}  {p}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
