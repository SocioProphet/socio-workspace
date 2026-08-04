"""Tests for the triad receipt collector — the producer-side aggregator that writes the file
detectors.detect_macro_triad_divergence reads. The decisive test is the round-trip: what the
collector writes is exactly what the detector consumes."""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.triad_receipts import collect_receipts  # noqa: E402
from automation.detectors import detect_macro_triad_divergence  # noqa: E402

SHA = "sha256:" + "a" * 64
SHA_B = "sha256:" + "b" * 64
BLS = "bls:" + "c" * 96
GOOD = "1" * 40
BAD = "2" * 40


def receipt(cluster, *, state_root=SHA, commit=GOOD, koe_id=None):
    r = {
        "cluster": f"did:web:{cluster}",
        "receipt_id": f"urn:lz:rie:{cluster}-000001",
        "issued_at": "2026-08-04T12:00:00Z",
        "state_root": state_root,
        "commit": commit,
        "writer_principal": "did:web:writer",
        "replica_principal": "did:web:replica",
        "quorum_sigs": [BLS],
    }
    if koe_id is not None:
        r["koe_id"] = koe_id
    return r


def _write(d: Path, name, obj) -> Path:
    p = d / name
    p.write_text(json.dumps(obj) if not isinstance(obj, str) else obj, encoding="utf-8")
    return p


def test_collects_wellformed_receipts():
    d = Path(tempfile.mkdtemp())
    paths = [_write(d, f"{c}.json", receipt(c)) for c in ("a", "b", "c")]
    doc = collect_receipts(paths, repo="SocioProphet/infra")
    assert len(doc["receipts"]) == 3 and doc["rejected"] == []
    assert doc["repo"] == "SocioProphet/infra" and doc["quorum"] == 2


def test_drops_malformed_and_records_rejection():
    d = Path(tempfile.mkdtemp())
    bad = receipt("b"); del bad["state_root"]
    paths = [_write(d, "a.json", receipt("a")), _write(d, "b.json", bad),
             _write(d, "c.json", receipt("c"))]
    doc = collect_receipts(paths, repo="r")
    assert len(doc["receipts"]) == 2  # a, c kept; b dropped
    assert len(doc["rejected"]) == 1 and "state_root" in doc["rejected"][0]["reason"]


def test_unreadable_file_is_rejected_not_fatal():
    d = Path(tempfile.mkdtemp())
    paths = [_write(d, "a.json", receipt("a")), d / "missing.json",
             _write(d, "junk.json", "{not json")]
    doc = collect_receipts(paths, repo="r")
    assert len(doc["receipts"]) == 1 and len(doc["rejected"]) == 2


def test_duplicate_master_rejected():
    d = Path(tempfile.mkdtemp())
    paths = [_write(d, "a.json", receipt("a")), _write(d, "a2.json", receipt("a"))]
    doc = collect_receipts(paths, repo="r")
    assert len(doc["receipts"]) == 1
    assert any("duplicate" in r["reason"] for r in doc["rejected"])


def test_writes_atomically_and_is_valid_json():
    d = Path(tempfile.mkdtemp())
    out = d / "status" / "lazerus-triad-receipts.json"
    paths = [_write(d, f"{c}.json", receipt(c)) for c in ("a", "b")]
    collect_receipts(paths, repo="r", out_path=out)
    assert out.exists() and not out.with_suffix(".json.tmp").exists()  # temp cleaned up
    reloaded = json.loads(out.read_text())
    assert len(reloaded["receipts"]) == 2


def test_roundtrip_collector_output_feeds_detector():
    """The decisive contract test: collect 2 healthy + 1 diverged master to the file, then the
    detector reads THAT file and proposes the failback. Producer and consumer agree on shape."""
    d = Path(tempfile.mkdtemp())
    out = d / "lazerus-triad-receipts.json"
    paths = [_write(d, "a.json", receipt("a")),
             _write(d, "b.json", receipt("b")),
             _write(d, "c.json", receipt("c", state_root=SHA_B, commit=BAD))]
    collect_receipts(paths, repo="SocioProphet/infra", out_path=out)
    beacons = detect_macro_triad_divergence(receipts_path=out)
    assert len(beacons) == 1
    assert beacons[0]["proposal"]["revert"] == f"{GOOD}..{BAD}"


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"triad_receipts: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
