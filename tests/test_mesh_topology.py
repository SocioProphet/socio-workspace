"""Tests for the k-mesh topology — the recursive ternary generalization of the triad."""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.mesh_topology import (  # noqa: E402
    build_tree, depth, leaves, tree_healthy, tree_leader, turn_length,
)


def nodes(n):
    return [f"n{i:03d}" for i in range(n)]


def test_build_and_leaves_preserve_all_backends():
    for n in (1, 2, 3, 9, 27, 50, 100):
        t = build_tree(nodes(n))
        assert sorted(leaves(t)) == sorted(nodes(n))


def test_depth_scales_log3():
    assert depth(build_tree(nodes(3))) == 1
    assert depth(build_tree(nodes(9))) == 2
    assert depth(build_tree(nodes(27))) == 3
    assert depth(build_tree(nodes(81))) == 4


def test_powers_of_three_are_perfectly_even():
    for n in (3, 9, 27, 81):
        t = build_tree(nodes(n))
        T = turn_length(t)
        counts = Counter(tree_leader(t, e) for e in range(T))
        assert set(counts.values()) == {1}  # every leaf leads exactly once per turn


def test_all_up_is_healthy():
    for n in (3, 9, 27):
        t = build_tree(nodes(n))
        assert tree_healthy(t, set(nodes(n)))


def test_one_failure_per_triad_survives():
    # N=9: three triads; drop one node in each -> every triad keeps a 2/3 quorum -> healthy.
    t = build_tree(nodes(9))
    down = {"n000", "n003", "n006"}
    assert tree_healthy(t, set(nodes(9)) - down)


def test_two_dead_subtrees_break_it():
    # N=9: kill 2 of 3 nodes in two triads -> those triads lose quorum -> only 1 healthy -> down.
    t = build_tree(nodes(9))
    down = {"n000", "n001", "n003", "n004"}
    assert not tree_healthy(t, set(nodes(9)) - down)


def test_turn_length_is_product_for_balanced():
    assert turn_length(build_tree(nodes(3))) == 3
    assert turn_length(build_tree(nodes(9))) == 9
    assert turn_length(build_tree(nodes(27))) == 27


def test_rejects_empty_mesh():
    try:
        build_tree([])
    except ValueError:
        pass
    else:
        raise AssertionError("empty mesh must raise")


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"mesh_topology: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
