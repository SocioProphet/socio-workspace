"""Lock the fractal-rotation simulation's claims into CI: even coverage, self-similar nesting,
and the quorum-of-quorums redundancy (tolerates any 3 failures, breaks at 4 well-placed)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from simulate_triad_rotation import (  # noqa: E402
    CLUSTERS, MASTERS, NODES, cluster_healthy, global_leader, min_failures_to_break,
    system_operational,
)


def test_global_leadership_is_perfectly_even():
    counts = {n: 0 for n in NODES}
    for e in range(9 * 50):  # 50 fractal turns
        counts[global_leader(e)] += 1
    assert set(counts.values()) == {50}  # every node led exactly 50 times


def test_self_similar_nesting_covers_every_pair_once_per_turn():
    # Over one 9-epoch turn each (cluster, master) pair is global leader exactly once.
    seen = [global_leader(e) for e in range(9)]
    assert sorted(seen) == sorted(NODES)


def test_all_up_is_operational():
    assert system_operational(set(NODES))


def test_tolerates_one_failure_per_cluster():
    # 3 failures, one per cluster -> every cluster still has a 2/3 quorum -> operational.
    down = {"C0.M0", "C1.M0", "C2.M0"}
    assert system_operational(set(NODES) - down)


def test_two_dead_clusters_breaks_it():
    # 2 masters down in each of two clusters -> those clusters lose quorum -> only 1 healthy -> down.
    down = {"C0.M0", "C0.M1", "C1.M0", "C1.M1"}
    assert not system_operational(set(NODES) - down)


def test_min_failures_to_break_is_four():
    assert min_failures_to_break() == 4


def test_cluster_quorum_is_two_of_three():
    up = set(NODES)
    assert cluster_healthy(up, "C0")
    assert cluster_healthy(up - {"C0.M0"}, "C0")           # 2/3 up -> healthy
    assert not cluster_healthy(up - {"C0.M0", "C0.M1"}, "C0")  # 1/3 up -> unhealthy


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"triad_rotation_sim: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
