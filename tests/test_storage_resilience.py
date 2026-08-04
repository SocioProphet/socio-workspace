"""Tests for the storage-resilience predicates + shard dispersal (hostile threat model)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.storage_resilience import (  # noqa: E402
    Placement, confidential, disperse_shards, durable, max_seizable_nodes,
    read_available_under_partition, write_consistent_under_partition,
)

P = Placement(replicas=3, rs_k=6, rs_m=3, encrypted_at_rest=True)


def test_durable_needs_k_shards():
    assert durable(6, P) and durable(9, P)
    assert not durable(5, P)


def test_max_seizable_is_parity():
    assert max_seizable_nodes(P) == 3  # lose any m=3 of n=9, k=6 remain


def test_confidential_encrypted_holds_under_any_seizure():
    assert confidential(0, P) and confidential(9, P)  # ciphertext everywhere


def test_confidential_unencrypted_needs_below_k():
    plain = Placement(rs_k=6, rs_m=3, encrypted_at_rest=False)
    assert confidential(5, plain)          # < k seized -> safe
    assert not confidential(6, plain)      # k seized -> the leaf can be assembled


def test_write_is_cp_majority():
    assert write_consistent_under_partition(2, P)      # 2 of 3 replicas -> majority -> writable
    assert not write_consistent_under_partition(1, P)  # minority -> fail-closed, no fork


def test_read_is_ap_k_threshold():
    assert read_available_under_partition(6, P)
    assert not read_available_under_partition(5, P)


def test_only_one_partition_can_write():
    # a 2:1 split of the home triad -> exactly one side has the write quorum (no split-brain).
    assert write_consistent_under_partition(2, P)
    assert not write_consistent_under_partition(1, P)


def test_disperse_uses_distinct_nodes():
    nodes = [f"n{i:02d}" for i in range(27)]
    placed = disperse_shards(nodes, P)
    assert len(placed) == P.rs_n
    assert len(set(placed.keys())) == P.rs_n  # all distinct nodes


def test_disperse_rejects_too_small_mesh():
    try:
        disperse_shards([f"n{i}" for i in range(5)], P)  # need 9 nodes for 9 shards
    except ValueError:
        pass
    else:
        raise AssertionError("dispersal must reject a mesh too small for the shard count")


def test_durability_overhead():
    assert abs(P.durability_overhead - 1.5) < 1e-9  # 9/6


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"storage_resilience: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
