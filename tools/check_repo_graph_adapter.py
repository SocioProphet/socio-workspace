#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "tools" / "repo_graph_adapter.py"
REQUIRED_REPOS = {
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
}
REQUIRED_INPUTS = {
    "registry/spine-v0.txt",
    "manifest/active-spine.repos.toml",
    "governance/CANONICAL_SOURCES.yaml",
    "catalog/boundaries.yaml",
    "docs/TOPOLOGY.md",
    "registry/corpus-loop-v1/valid.watson-cyc-chronos.pinned.json",
}


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def load_adapter_module():
    spec = importlib.util.spec_from_file_location("repo_graph_adapter", ADAPTER)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load repo graph adapter")
    module = importlib.util.module_from_spec(spec)
    # The adapter defines dataclasses under `from __future__ import annotations`;
    # dataclasses resolves those string annotations through sys.modules, so the
    # module must be registered before it is executed.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failed = False
    module = load_adapter_module()
    adapter = module.default_adapter()

    repos = adapter.repositories()
    repo_names = {repo.repository for repo in repos}
    missing_repos = REQUIRED_REPOS - repo_names
    if missing_repos:
        fail(f"adapter missing repositories: {sorted(missing_repos)}")
        failed = True

    hellgraph = next((repo for repo in repos if repo.repository == "SocioProphet/hellgraph"), None)
    if hellgraph is None:
        fail("adapter missing hellgraph node")
        failed = True
    elif hellgraph.spine_role != "promotion_candidate":
        fail(f"hellgraph role mismatch: {hellgraph.spine_role}")
        failed = True

    fixture = adapter.graph_fixture()
    if fixture.fixture_id != "generated.active-spine.repo-graph":
        fail("fixture id mismatch")
        failed = True
    if fixture.corpus_loop != "watson-cyc-semantic-web-chronos-v1":
        fail("corpus loop mismatch")
        failed = True
    if len(fixture.source_digest) != 64:
        fail("source digest must be 64 hex characters")
        failed = True

    inputs = {item.source_path for item in adapter.source_inputs()}
    missing_inputs = REQUIRED_INPUTS - inputs
    if missing_inputs:
        fail(f"adapter missing source inputs: {sorted(missing_inputs)}")
        failed = True

    if failed:
        return 1
    print("OK: repo graph adapter boundary exposes generated graph state")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
