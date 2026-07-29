#!/usr/bin/env python3
"""Gate the lifted vendored-artifact graph.

Three properties, in order:

1. FAITHFUL / REPRODUCIBLE. The committed graph equals what the lift regenerates
   from registry/vendor-freshness.yaml right now. A drift means someone hand-edited
   the graph or the register moved without regenerating — either way the graph is
   lying, so fail (same clean-tree discipline as the SVF fixtures).

2. NO SECOND REGISTER. Every freshnessState in the graph equals
   validate_vendor_freshness.compute_state for that artifact. The graph may not hold
   an opinion of staleness the gate does not.

3. VOCABULARY-COVERED. Every nrg: term the graph uses is declared, either in the
   base repo-graph vocabulary or the vendored-artifact extension.

4. REASONING-SOUND. Each source's staleConsumerCount and blastRadius match the set of
   consumers compute_state flags stale — the blast-radius inference is not decorative.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "registry" / "vendor-freshness.yaml"
REASONER = ROOT / "registry" / "neurosymbolic-repo-graph-reasoner"
GRAPH = REASONER / "vendored-artifact.graph.ttl"
BASE_VOCAB = REASONER / "neurosymbolic-repo-graph.ttl"
EXT_VOCAB = REASONER / "vendored-artifact.vocab.ttl"
VALIDATOR = ROOT / "tools" / "validate_vendor_freshness.py"
LIFT = ROOT / "tools" / "lift_vendor_freshness_to_graph.py"


def fail(msg: str) -> None:
    print(f"ERR: {msg}", file=sys.stderr)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module


def declared_terms(text: str) -> set[str]:
    return set(re.findall(r"^nrg:([A-Za-z][A-Za-z0-9]*)\s+a\s+(?:rdfs:Class|rdfs:Property)", text, re.MULTILINE))


def used_terms(text: str) -> set[str]:
    return set(re.findall(r"\bnrg:([A-Za-z][A-Za-z0-9]*)\b", text))


def main() -> int:
    failed = False

    if not GRAPH.exists():
        fail(f"missing lifted graph: {GRAPH.name} — run `make neurosymbolic-vendored-artifact-graph-write`")
        return 1

    lift = _load(LIFT, "lift_vendor_freshness_to_graph")
    vf = _load(VALIDATOR, "validate_vendor_freshness")

    # 1. faithful / reproducible
    regenerated = lift.build()
    committed = GRAPH.read_text(encoding="utf-8")
    if regenerated != committed:
        fail("committed vendored-artifact.graph.ttl is stale — regenerate with "
             "`make neurosymbolic-vendored-artifact-graph-write` and commit")
        failed = True

    # source of truth
    data = yaml.safe_load(REGISTER.read_text(encoding="utf-8"))
    shape_errors: list[str] = []
    sources, artifacts = vf.check_shape(data, shape_errors)
    if shape_errors:
        fail("register fails shape checks: " + "; ".join(shape_errors))
        return 1

    # 2. no second register — graph freshnessState agrees with compute_state for EVERY
    #    artifact. Coverage is asserted so a regex miss cannot silently drop one.
    state_pairs = re.findall(
        r'nrg:artifactId "([^"]+)" ;.*?nrg:freshnessState "([^"]+)"',
        committed,
        re.DOTALL,
    )
    if len(state_pairs) != len(artifacts):
        fail(f"parsed {len(state_pairs)} freshnessState pairs but the register declares "
             f"{len(artifacts)} artifacts — the graph parse dropped coverage")
        failed = True
    state_in_graph = dict(state_pairs)
    expected_stale: dict[str, list[str]] = {}
    for art in artifacts:
        aid = art["artifact_id"]
        state, _ = vf.compute_state(art, sources[art["source_id"]])
        if state_in_graph.get(aid) != state:
            fail(f"graph freshnessState for {aid} is {state_in_graph.get(aid)!r}, "
                 f"compute_state says {state!r} — graph must not hold a second opinion")
            failed = True
        if state == "stale":
            expected_stale.setdefault(art["source_id"], []).append(aid)

    # 3. vocabulary coverage
    declared = declared_terms(BASE_VOCAB.read_text(encoding="utf-8")) | declared_terms(EXT_VOCAB.read_text(encoding="utf-8"))
    used = used_terms(committed)
    undeclared = used - declared
    if undeclared:
        fail(f"graph uses undeclared nrg: terms: {sorted(undeclared)}")
        failed = True

    # 4. reasoning-sound — each source's staleConsumerCount and its nrg:staleConsumer
    #    edges match exactly the set compute_state flags stale.
    artifact_base = lift.ARTIFACT_BASE
    seen_sources: set[str] = set()
    for m in re.finditer(
        r'a nrg:VendoredSource ;\s*\n\s*nrg:sourceId "([^"]+)" ;\s*\n\s*'
        r'nrg:consumerCount \d+ ;\s*\n\s*nrg:staleConsumerCount (\d+)'
        r'((?:\s*;\s*nrg:staleConsumer <[^>]+>)*)',
        committed,
    ):
        sid, count_str, edges_blob = m.group(1), m.group(2), m.group(3)
        seen_sources.add(sid)
        edge_ids = set(re.findall(re.escape("nrg:staleConsumer <" + artifact_base) + r"([^>]+)>", edges_blob))
        want = set(expected_stale.get(sid, []))
        if edge_ids != want:
            fail(f"staleConsumer edges for {sid} are {sorted(edge_ids)}, expected {sorted(want)}")
            failed = True
        if int(count_str) != len(want):
            fail(f"staleConsumerCount for {sid} is {count_str}, expected {len(want)}")
            failed = True
    missing = set(expected_stale) - seen_sources
    if missing:
        fail(f"sources with stale consumers absent from the graph: {sorted(missing)}")
        failed = True

    if failed:
        return 1
    print(f"OK: vendored-artifact graph is faithful to the register, single-source, and vocabulary-covered "
          f"({len(artifacts)} artifacts, {len(expected_stale)} source(s) with stale blast radius)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
