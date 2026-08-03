"""tests/test_propagation_engine.py — unit tests for PropagationEngine."""

from __future__ import annotations

import pytest
from pathlib import Path

from engines.propagation_engine import PropagationEngine


# Engine LOGIC is tested against a deterministic fixture registry, not the live
# registry/. The real dependency-graph.yaml is now regenerated from measured
# evidence, so it changes shape as topology is re-measured and no longer carries
# hand-authored `dependency_levels` — binding unit tests to it made them assert a
# fabricated topology. The real artifact is guarded separately by
# test_real_registry_loads_and_is_acyclic below.
FIXTURE_DIR = Path(__file__).parent / "fixtures" / "propagation"
REAL_REGISTRY_DIR = Path(__file__).parent.parent / "registry"


@pytest.fixture
def engine() -> PropagationEngine:
    e = PropagationEngine(FIXTURE_DIR)
    e.load()
    return e


def test_dependencies_of_sociosphere(engine: PropagationEngine) -> None:
    deps = engine.dependencies_of("sociosphere")
    assert "tritrpc" in deps
    assert "trit-to-trust" in deps


def test_dependents_of_tritrpc(engine: PropagationEngine) -> None:
    dependents = engine.dependents_of("tritrpc")
    assert "sociosphere" in dependents
    assert "new-hope" in dependents


def test_dependencies_of_unknown_returns_empty(engine: PropagationEngine) -> None:
    deps = engine.dependencies_of("nonexistent-repo")
    assert deps == []


def test_dependents_of_unknown_returns_empty(engine: PropagationEngine) -> None:
    deps = engine.dependents_of("nonexistent-repo")
    assert deps == []


def test_dependency_level_known_repo(engine: PropagationEngine) -> None:
    # tritrpc is level 0 (no internal deps)
    assert engine.dependency_level("tritrpc") == 0


def test_dependency_level_sociosphere_higher(engine: PropagationEngine) -> None:
    soc_level = engine.dependency_level("sociosphere")
    tri_level = engine.dependency_level("tritrpc")
    assert soc_level is not None
    assert tri_level is not None
    assert soc_level > tri_level


def test_dependency_level_archived(engine: PropagationEngine) -> None:
    assert engine.dependency_level("socios") == -1


def test_get_rule_for_tritrpc(engine: PropagationEngine) -> None:
    rule = engine.get_rule("tritrpc")
    assert rule is not None
    assert rule["trigger"]["repo"] == "tritrpc"
    assert "propagate_to" in rule


def test_get_rule_unknown_returns_none(engine: PropagationEngine) -> None:
    assert engine.get_rule("definitely-nonexistent") is None


def test_all_rules_nonempty(engine: PropagationEngine) -> None:
    rules = engine.all_rules()
    assert len(rules) > 0


def test_compute_cascade_tritrpc(engine: PropagationEngine) -> None:
    cascade = engine.compute_cascade("tritrpc", max_depth=2)
    repos = {item["repo"] for item in cascade}
    # trit-to-trust and new-hope depend on tritrpc
    assert "trit-to-trust" in repos or "new-hope" in repos or "sociosphere" in repos


def test_compute_cascade_no_duplicates(engine: PropagationEngine) -> None:
    cascade = engine.compute_cascade("event-bus", max_depth=3)
    repos = [item["repo"] for item in cascade]
    assert len(repos) == len(set(repos)), "Duplicate repos in cascade output"


def test_compute_cascade_respects_max_depth(engine: PropagationEngine) -> None:
    cascade = engine.compute_cascade("tritrpc", max_depth=1)
    for item in cascade:
        assert item["depth"] <= 1


def test_compute_cascade_depth_ordering(engine: PropagationEngine) -> None:
    cascade = engine.compute_cascade("event-bus", max_depth=3)
    depths = [item["depth"] for item in cascade]
    # Depths should be non-decreasing (BFS order)
    assert depths == sorted(depths)


def test_no_cycles_in_registry(engine: PropagationEngine) -> None:
    cycles = engine.detect_cycles()
    assert cycles == [], f"Dependency cycles detected: {cycles}"


def test_real_registry_loads_and_is_acyclic() -> None:
    """Guard the ACTUAL committed graph: it must load and stay acyclic.

    Engine logic is covered by the fixture-backed tests above; this one keeps a
    witness on the real registry/dependency-graph.yaml so a malformed or cyclic
    regeneration fails here, without pinning assertions to any specific measured
    edge (which would re-introduce the brittleness we just removed).
    """
    e = PropagationEngine(REAL_REGISTRY_DIR)
    e.load()
    assert e.all_rules() is not None
    assert e.detect_cycles() == []
