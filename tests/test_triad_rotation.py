"""Tests for the triad master rotation — the geometric, triangular-even leader schedule."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.triad_rotation import (  # noqa: E402
    Assignment, RotationSchedule, epoch_for_time, leader_counts, load_schedule, rotate,
)

TRIAD = ["did:web:a", "did:web:b", "did:web:c"]


def test_rotation_walks_the_triangle():
    assert rotate(TRIAD, 0).leader == "did:web:a"
    assert rotate(TRIAD, 1).leader == "did:web:b"
    assert rotate(TRIAD, 2).leader == "did:web:c"
    assert rotate(TRIAD, 3).leader == "did:web:a"  # back to the start after one turn


def test_writer_never_equals_replica():
    for e in range(-5, 20):
        a = rotate(TRIAD, e)
        assert len({a.leader, a.attestor, a.witness}) == 3  # all three distinct
        w, r = a.writer_replica
        assert w != r  # the Lazerus rule the rotation exists to strengthen


def test_triangular_evenness_over_a_full_turn():
    # Over any 3 consecutive epochs each master leads exactly once.
    for start in range(0, 9):
        counts = leader_counts(TRIAD, range(start, start + 3))
        assert set(counts.values()) == {1}
    # Over 3N epochs each master leads exactly N times.
    counts = leader_counts(TRIAD, range(0, 300))
    assert counts == {"did:web:a": 100, "did:web:b": 100, "did:web:c": 100}


def test_step_two_is_the_reverse_orientation_still_even():
    assert rotate(TRIAD, 1, step=2).leader == "did:web:c"  # A -> C -> B
    counts = leader_counts(TRIAD, range(0, 300), step=2)
    assert counts == {"did:web:a": 100, "did:web:b": 100, "did:web:c": 100}


def test_step_multiple_of_three_rejected():
    for bad in (0, 3, 6, -3):
        try:
            rotate(TRIAD, 1, step=bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"step {bad} should be rejected (not triangular-even)")


def test_rejects_non_triad():
    for bad in [["a", "b"], ["a", "b", "c", "d"], ["a", "a", "b"]]:
        try:
            rotate(bad, 0)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{bad} is not a valid triad")


def test_determinism():
    assert rotate(TRIAD, 7) == rotate(TRIAD, 7)  # pure function of (triad, epoch)


def test_epoch_for_time():
    assert epoch_for_time(0, period_s=3600) == 0
    assert epoch_for_time(3599, period_s=3600) == 0
    assert epoch_for_time(3600, period_s=3600) == 1
    assert epoch_for_time(7200, period_s=3600) == 2
    # phase shifts the boundary
    assert epoch_for_time(3600, period_s=3600, phase_s=1) == 0  # just before the shifted boundary


def test_schedule_at_time_composes():
    sched = RotationSchedule(masters=TRIAD, period_s=3600, step=1)
    assert sched.at_time(0).leader == "did:web:a"
    assert sched.at_time(3600).leader == "did:web:b"
    assert sched.at_time(7200).leader == "did:web:c"


def test_load_declared_schedule_validates():
    sched = load_schedule()  # registry/triad-rotation.yaml
    assert len(sched.masters) == 3 and sched.step in (1, 2) and sched.period_s > 0
    # the declared schedule is itself triangular-even
    counts = leader_counts(sched.masters, range(0, 30), step=sched.step)
    assert set(counts.values()) == {10}


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"triad_rotation: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
