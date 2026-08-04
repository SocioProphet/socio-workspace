"""Tests for load_runtime_placement — the actuation->EFFECT link: the live threat posture actually
selects the storage placement new writes use, bounded never below the sanctioned floor."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.storage_placement import load_all, load_placement, load_runtime_placement  # noqa: E402


def _state(tier):
    p = Path(tempfile.mkdtemp()) / "mesh-threat-state.json"
    p.write_text(json.dumps({"level": tier, "tier": tier, "calm_dwell": 0}), encoding="utf-8")
    return p


FLOOR = load_placement()  # registry default_tier (hardened)
TIERS = load_all()


def test_no_posture_file_uses_floor():
    missing = Path(tempfile.mkdtemp()) / "absent.json"
    assert load_runtime_placement(state_path=missing) == FLOOR


def test_hostile_posture_selects_hostile_placement():
    got = load_runtime_placement(state_path=_state("hostile"))
    assert got == TIERS["hostile"] and got.shard_replicas == 2  # escalation realized


def test_posture_below_floor_is_clamped_up():
    # baseline is weaker than the hardened floor; the runtime posture may not lower resilience.
    got = load_runtime_placement(state_path=_state("baseline"))
    assert got.durability_overhead >= FLOOR.durability_overhead
    assert got == FLOOR  # clamped up to the sanctioned minimum


def test_corrupt_state_falls_back_to_floor():
    bad = Path(tempfile.mkdtemp()) / "state.json"
    bad.write_text("{not json", encoding="utf-8")
    assert load_runtime_placement(state_path=bad) == FLOOR


def test_unknown_tier_in_state_falls_back_to_floor():
    assert load_runtime_placement(state_path=_state("meltdown")) == FLOOR  # not a declared tier


def test_endtoend_detector_escalation_changes_the_placement():
    """The whole effect: the live detector escalates and writes the posture; the storage layer then
    selects a strictly more resilient placement for new writes than the floor."""
    from automation.detectors import detect_mesh_threat
    d = Path(tempfile.mkdtemp())
    reports, state = d / "reports.json", d / "state.json"
    reports.write_text(json.dumps({"quorum": 3, "reports": [
        {"vantage": f"m{i}", "unreachable_fraction": 0.3, "anomalies_seen": 4,
         "partition_suspected": True} for i in range(3)]}), encoding="utf-8")
    before = load_runtime_placement(state_path=state)   # no posture yet -> floor
    detect_mesh_threat(reports_path=reports, state_path=state)  # escalates + persists posture
    after = load_runtime_placement(state_path=state)
    assert before == FLOOR
    assert after.durability_overhead >= before.durability_overhead  # escalation raised the tier


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"runtime_placement: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
