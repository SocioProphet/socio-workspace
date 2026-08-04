"""Tests for the declared, governed storage placement loader + shard-replication resilience."""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.storage_placement import load_all, load_placement  # noqa: E402
from automation.storage_resilience import (  # noqa: E402
    Placement, disperse_with_replicas,
)


def _write(text) -> Path:
    p = Path(tempfile.mkdtemp()) / "mesh-storage-placement.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_loads_declared_tiers():
    base = load_placement("baseline")
    assert (base.rs_k, base.rs_m, base.shard_replicas) == (6, 3, 1)
    hostile = load_placement("hostile")
    assert hostile.shard_replicas == 2 and abs(hostile.durability_overhead - 3.0) < 1e-9


def test_default_tier_used_when_none():
    assert load_placement() == load_placement("hardened")  # default_tier: hardened


def test_unknown_tier_rejected():
    try:
        load_placement("nonexistent")
    except ValueError as e:
        assert "unknown threat tier" in str(e)
    else:
        raise AssertionError("unknown tier must raise")


def test_unencrypted_seizable_tier_rejected():
    bad = _write("tiers:\n  x:\n    rs_k: 6\n    rs_m: 3\n    encrypted_at_rest: false\n")
    try:
        load_placement("x", path=bad)
    except ValueError as e:
        assert "encrypted_at_rest" in str(e)
    else:
        raise AssertionError("an unencrypted seizable tier must be rejected")


def test_degenerate_params_rejected():
    for spec in ("rs_k: 0\n    rs_m: 3", "rs_k: 6\n    rs_m: 3\n    shard_replicas: 0",
                 "rs_k: 6\n    rs_m: 3\n    replicas: 0"):
        bad = _write(f"tiers:\n  x:\n    {spec}\n    encrypted_at_rest: true\n")
        try:
            load_placement("x", path=bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"degenerate spec must be rejected: {spec}")


def test_load_all_validates_whole_file():
    tiers = load_all()
    assert {"baseline", "hardened", "hostile"} <= set(tiers)
    assert all(isinstance(p, Placement) for p in tiers.values())


def test_replication_pushes_durability_past_half_analytically():
    baseline = Placement(rs_k=6, rs_m=3, shard_replicas=1)
    hostile = Placement(rs_k=6, rs_m=3, shard_replicas=2)
    # at half the mesh seized: baseline (parity only) is not durable in expectation; R=2 is.
    assert not baseline.expected_durable_under_seizure(0.5)
    assert hostile.expected_durable_under_seizure(0.5)


def test_disperse_with_replicas_places_r_distinct_nodes_per_shard():
    nodes = [f"n{i:02d}" for i in range(27)]
    placed = disperse_with_replicas(nodes, Placement(rs_k=6, rs_m=3, shard_replicas=2))
    assert len(placed) == 9                       # n shards
    for copies in placed.values():
        assert len(copies) == 2 and len(set(copies)) == 2  # R distinct nodes each


def test_disperse_rejects_mesh_too_small_for_replicas():
    nodes = [f"n{i}" for i in range(10)]
    try:
        disperse_with_replicas(nodes, Placement(rs_k=6, rs_m=3, shard_replicas=2))  # needs 18
    except ValueError:
        pass
    else:
        raise AssertionError("too-small mesh must be rejected")


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"storage_placement: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
