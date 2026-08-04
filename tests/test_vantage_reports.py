"""Tests for the vantage report producer + collector — the sensor half of the adaptive loop.
The decisive test is the round-trip: nodes build reports, the collector writes the file, and the
live detector reads THAT file and escalates. Producer and consumer agree end to end."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.vantage_reports import build_report, collect_reports, probe_and_report  # noqa: E402
from automation.detectors import detect_mesh_threat  # noqa: E402
from automation.mesh_threat import _rank  # noqa: E402


def _dir():
    return Path(tempfile.mkdtemp())


def _write(d, name, obj):
    p = d / name
    p.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding="utf-8")
    return p


# ── build_report (honest local signal) ───────────────────────────────────────────────────────

def test_build_report_computes_fraction():
    r = build_report("m0", peers_total=10, peers_unreachable=3, anomalies_seen=2)
    assert r["unreachable_fraction"] == 0.3 and r["anomalies_seen"] == 2
    assert r["partition_suspected"] is False  # 3 of 10 unreachable -> majority reachable


def test_partition_suspected_derived_when_majority_unreachable():
    r = build_report("m0", peers_total=10, peers_unreachable=6)
    assert r["partition_suspected"] is True  # can't see a majority -> partitioned from its vantage


def test_no_peers_sees_nothing():
    r = build_report("m0", peers_total=0, peers_unreachable=0)
    assert r["unreachable_fraction"] == 0.0 and r["partition_suspected"] is False


def test_build_report_rejects_bad_counts():
    for kw in ({"peers_total": 5, "peers_unreachable": 6}, {"peers_total": -1, "peers_unreachable": 0}):
        try:
            build_report("m0", **kw)
        except ValueError:
            pass
        else:
            raise AssertionError(f"bad counts must raise: {kw}")


# ── probe_and_report (injected reachability seam) ─────────────────────────────────────────────

def test_probe_counts_unreachable_peers():
    peers = ["p1", "p2", "p3", "p4"]
    down = {"p2", "p3"}
    r = probe_and_report("m0", peers, reach=lambda p: p not in down)
    assert r["unreachable_fraction"] == 0.5 and r["partition_suspected"] is False  # 2 of 4, not majority


def test_probe_majority_down_suspects_partition():
    peers = ["p1", "p2", "p3"]
    r = probe_and_report("m0", peers, reach=lambda p: p == "p1")  # 2 of 3 down
    assert r["partition_suspected"] is True


def test_probe_error_counts_as_unreachable():
    def flaky(p):
        if p == "p2":
            raise ConnectionError("timeout")
        return True
    r = probe_and_report("m0", ["p1", "p2"], reach=flaky)
    assert r["unreachable_fraction"] == 0.5  # the erroring peer is unreachable, not healthy


# ── collector (fail-closed fan-in) ────────────────────────────────────────────────────────────

def test_collects_wellformed_reports():
    d = _dir()
    paths = [_write(d, f"{v}.json", build_report(v, peers_total=10, peers_unreachable=3)) for v in ("a", "b", "c")]
    doc = collect_reports(paths, quorum=3)
    assert len(doc["reports"]) == 3 and doc["rejected"] == [] and doc["quorum"] == 3


def test_drops_malformed_and_records_rejection():
    d = _dir()
    good = _write(d, "a.json", build_report("a", peers_total=10, peers_unreachable=3))
    bad = _write(d, "b.json", {"vantage": "b", "unreachable_fraction": 1.7})  # out of range
    missing = d / "gone.json"
    doc = collect_reports([good, bad, missing], quorum=3)
    assert len(doc["reports"]) == 1 and len(doc["rejected"]) == 2


def test_duplicate_vantage_rejected():
    d = _dir()
    p1 = _write(d, "a.json", build_report("a", peers_total=10, peers_unreachable=3))
    p2 = _write(d, "a2.json", build_report("a", peers_total=10, peers_unreachable=4))
    doc = collect_reports([p1, p2], quorum=3)
    assert len(doc["reports"]) == 1
    assert any("duplicate" in r["reason"] for r in doc["rejected"])


def test_writes_atomically():
    d = _dir()
    out = d / "status" / "mesh-vantage-reports.json"
    paths = [_write(d, f"{v}.json", build_report(v, peers_total=10, peers_unreachable=3)) for v in ("a", "b")]
    collect_reports(paths, out_path=out)
    assert out.exists() and not out.with_suffix(".json.tmp").exists()
    assert len(json.loads(out.read_text())["reports"]) == 2


def test_roundtrip_producer_feeds_detector_into_escalation():
    """3 nodes each observe a hostile local view; collector writes the file; the live detector
    reads it and escalates. The full sensor->collector->detector->actuation path, exercised."""
    d = _dir()
    out = d / "mesh-vantage-reports.json"
    state = d / "mesh-threat-state.json"
    # each node: most peers unreachable + anomalies + (derived) partition
    paths = [_write(d, f"{v}.json", build_report(v, peers_total=10, peers_unreachable=7, anomalies_seen=4))
             for v in ("a", "b", "c")]
    collect_reports(paths, quorum=3, out_path=out)
    beacons = detect_mesh_threat(reports_path=out, state_path=state)
    assert beacons and _rank(beacons[0]["detail"]["to_level"]) > _rank("calm")
    assert json.loads(state.read_text())["level"] == beacons[0]["detail"]["to_level"]


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"vantage_reports: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
