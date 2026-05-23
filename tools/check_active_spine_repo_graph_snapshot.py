#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner" / "generated.active-spine.repo-graph.ttl"
GENERATOR = ROOT / "tools" / "generate_active_spine_repo_graph.py"

REQUIRED_SNAPSHOT_TERMS = {
    "nrg:RepositoryGraphFixture",
    "nrg:fixtureId",
    "nrg:expectedResult",
    "nrg:corpusLoop",
    "nrg:policyDecision",
    "nrg:sourceDigest",
}


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def load_generator():
    spec = importlib.util.spec_from_file_location("generate_active_spine_repo_graph", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extract_digest(text: str) -> str | None:
    match = re.search(r'nrg:sourceDigest "([0-9a-f]{64})"', text)
    return match.group(1) if match else None


def main() -> int:
    failed = False
    if not SNAPSHOT.exists():
        fail(f"missing snapshot: {SNAPSHOT.relative_to(ROOT)}")
        return 1

    snapshot = SNAPSHOT.read_text(encoding="utf-8")
    for term in REQUIRED_SNAPSHOT_TERMS:
        if term not in snapshot:
            fail(f"snapshot missing term {term}")
            failed = True

    try:
        generator = load_generator()
        generated = generator.generate()
    except Exception as exc:  # pragma: no cover
        fail(f"generator failed: {exc}")
        return 1

    snapshot_digest = extract_digest(snapshot)
    generated_digest = extract_digest(generated)
    if not snapshot_digest:
        fail("snapshot missing sourceDigest")
        failed = True
    if not generated_digest:
        fail("generated graph missing sourceDigest")
        failed = True
    if snapshot_digest and generated_digest and snapshot_digest != generated_digest:
        fail(f"snapshot digest drift: snapshot={snapshot_digest} generated={generated_digest}")
        failed = True

    for required in [
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
    ]:
        if required not in generated:
            fail(f"generated graph missing active-spine repo {required}")
            failed = True

    if failed:
        return 1

    print("OK: active spine repo graph snapshot digest matches regenerated graph")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
