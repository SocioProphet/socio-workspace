from pathlib import Path

from .util import find_repo_root


def main() -> int:
    here = Path(__file__).resolve()
    root = find_repo_root(here.parent)

    required = [
        root / "schemas/avro/trirpc/envelope.v0.avsc",
        root / "schemas/avro/trirpc/value.v0.avsc",
        root / "schemas/avro/trirpc/error.v0.avsc",
        root / "schemas/schemasalad/trirpc-schema-bundle.v0.yml",
    ]

    missing = [p for p in required if not p.exists()]
    if missing:
        print("ERR: missing required TriRPC v0 artifacts:")
        for p in missing:
            print(f" - {p}")
        return 2

    print("OK: TriRPC v0 artifacts present")
    print("ROOT", root)
    for p in required:
        print("FOUND", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
