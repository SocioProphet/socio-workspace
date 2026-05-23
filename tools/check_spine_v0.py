#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "registry" / "spine-v0.txt"
REQUIRED = [
    "SocioProphet/sociosphere",
    "SocioProphet/prophet-platform",
    "SocioProphet/TriTRPC",
    "SocioProphet/socioprophet-standards-storage",
    "SocioProphet/socioprophet-standards-knowledge",
    "SocioProphet/prophet-platform-standards",
    "SocioProphet/socioprophet-agent-standards",
    "SocioProphet/prophet-workspace",
    "SocioProphet/hellgraph",
    "SourceOS-Linux/sourceos-spec",
]


def main() -> int:
    text = REG.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED if item not in text]
    if missing:
        for item in missing:
            print(f"ERR: missing {item}", file=sys.stderr)
        return 1
    print("OK: active spine v0 registry covers required repos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
