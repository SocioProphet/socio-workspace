"""Tests for the adaptive threat controller wired into the live loop: the stateful step()
transition and the detect_mesh_threat detector that persists the runtime posture."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.mesh_threat import (  # noqa: E402
    MeshThreatState, VantageReport, _rank, load_threat_policy, step,
)
from automation.detectors import detect_mesh_threat  # noqa: E402

POLICY = load_threat_policy()

CALM = [VantageReport(f"m{i}", 0.0, 0, False) for i in range(3)]
HOSTILE = [VantageReport(f"m{i}", 0.30, 4, True) for i in range(3)]


def test_step_escalates_immediately():
    state, a = step(HOSTILE, MeshThreatState(), POLICY)
    assert a.actuation == "auto_escalate"
    assert _rank(state.level) > _rank("calm") and state.calm_dwell == 0


def test_step_holds_then_deescalates_after_dwell():
    # start elevated, then feed calm: HOLD accumulating dwell, then a de-escalation is applied.
    state = MeshThreatState(level=step(HOSTILE, MeshThreatState(), POLICY)[0].level, calm_dwell=0)
    start_rank = _rank(state.level)
    actuations = []
    for _ in range(POLICY.deescalate_dwell + 2):
        state, a = step(CALM, state, POLICY)
        actuations.append(a.actuation)
        if a.actuation == "propose_deescalate":
            break
    assert "hold" in actuations                      # it waited (dwell) before dropping
    assert actuations[-1] == "propose_deescalate"    # then de-escalated
    assert _rank(state.level) < start_rank           # runtime posture actually lowered


def test_step_holds_dwell_not_yet_met():
    state = MeshThreatState(level="hostile", calm_dwell=0)
    state, a = step(CALM, state, POLICY)
    assert a.actuation == "hold" and state.level == "hostile" and state.calm_dwell == 1


# ── the detector (persists the runtime posture; beacons transitions) ─────────────────────────

def _files():
    d = Path(tempfile.mkdtemp())
    return d / "reports.json", d / "state.json"


def _write_reports(path, reports, quorum=3):
    path.write_text(json.dumps({"quorum": quorum, "reports": reports}), encoding="utf-8")


def test_detector_no_reports_is_noop():
    r, s = _files()
    assert detect_mesh_threat(reports_path=r, state_path=s) == []


def test_detector_escalation_persists_and_beacons():
    r, s = _files()
    _write_reports(r, [{"vantage": f"m{i}", "unreachable_fraction": 0.3,
                        "anomalies_seen": 4, "partition_suspected": True} for i in range(3)])
    beacons = detect_mesh_threat(reports_path=r, state_path=s)
    assert len(beacons) == 1
    assert beacons[0]["detail"]["from_level"] == "calm"
    assert _rank(beacons[0]["detail"]["to_level"]) > _rank("calm")
    persisted = json.loads(s.read_text())
    assert persisted["level"] == beacons[0]["detail"]["to_level"]  # runtime posture applied


def test_detector_no_transition_no_beacon():
    r, s = _files()
    _write_reports(r, [{"vantage": f"m{i}", "unreachable_fraction": 0.3,
                        "anomalies_seen": 4, "partition_suspected": True} for i in range(3)])
    detect_mesh_threat(reports_path=r, state_path=s)          # escalates
    assert detect_mesh_threat(reports_path=r, state_path=s) == []  # same signal -> no transition


def test_detector_holographic_outvotes_a_liar():
    # 3 honest vantages see hostile; 1 liar reports all-clear. The quorum median must not be fooled.
    r, s = _files()
    reports = [{"vantage": f"m{i}", "unreachable_fraction": 0.3, "anomalies_seen": 4,
                "partition_suspected": True} for i in range(3)]
    reports.append({"vantage": "liar", "unreachable_fraction": 0.0, "anomalies_seen": 0,
                    "partition_suspected": False})
    _write_reports(r, reports)
    beacons = detect_mesh_threat(reports_path=r, state_path=s)
    assert beacons and _rank(beacons[0]["detail"]["to_level"]) > _rank("calm")  # liar did not suppress


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"mesh_threat_actuation: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
