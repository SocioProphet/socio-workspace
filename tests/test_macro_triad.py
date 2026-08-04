"""Tests for the Lazerus -> macro-triad -> failback bridge.

Covers the three seams: (1) the Lazerus receipt linter is fail-closed on the published token
grammar; (2) the macro-triad quorum names the sick k3s master only when a real majority exists;
(3) the failback producer emits a quorum-gated revert that the #585 pr_opener path accepts.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.lazerus import lint_receipt  # noqa: E402
from automation.macro_triad import assess_triad  # noqa: E402
from automation.beacon_producers import propose_state_failback  # noqa: E402
from automation.pr_opener import _valid  # noqa: E402

SHA = "sha256:" + "a" * 64          # a valid state_root
SHA_B = "sha256:" + "b" * 64        # a different state_root (divergence)
BLS = "bls:" + "c" * 96            # a valid BLS quorum signature
GOOD = "1" * 40                     # canonical git commit
BAD = "2" * 40                      # divergent git commit


def receipt(cluster, *, state_root=SHA, commit=GOOD, koe_id=None,
            writer="did:web:writer", replica="did:web:replica"):
    r = {
        "cluster": f"did:web:{cluster}",
        "receipt_id": f"urn:lz:rie:{cluster}-000001",
        "issued_at": "2026-08-04T12:00:00Z",
        "state_root": state_root,
        "commit": commit,
        "writer_principal": writer,
        "replica_principal": replica,
        "quorum_sigs": [BLS],
    }
    if koe_id is not None:
        r["koe_id"] = koe_id
    return r


# --- linter (fail-closed on the grammar) -----------------------------------------------------

def test_lint_accepts_a_wellformed_receipt():
    res = lint_receipt(receipt("a"))
    assert res.ok and res.receipt.state_root == SHA and not res.quarantined


def test_lint_rejects_non_dict():
    assert not lint_receipt("nope").ok
    assert not lint_receipt(None).ok


def test_lint_rejects_missing_required_field():
    r = receipt("a"); del r["state_root"]
    res = lint_receipt(r)
    assert not res.ok and any("state_root" in e for e in res.errors)


def test_lint_rejects_malformed_sha256():
    res = lint_receipt(receipt("a", state_root="sha256:xyz"))
    assert not res.ok and any("state_root" in e for e in res.errors)


def test_lint_rejects_self_attestation():
    res = lint_receipt(receipt("a", writer="did:web:same", replica="did:web:same"))
    assert not res.ok and any("self-attest" in e for e in res.errors)


def test_lint_rejects_empty_or_bad_quorum_sig():
    assert not lint_receipt({**receipt("a"), "quorum_sigs": []}).ok
    assert not lint_receipt({**receipt("a"), "quorum_sigs": ["deadbeef"]}).ok


def test_lint_flags_quarantine_koe_id():
    res = lint_receipt(receipt("a", koe_id="urn:lz:koe:abc123"))
    assert res.ok and res.quarantined and res.receipt.koe_id == "urn:lz:koe:abc123"


def test_lint_rejects_malformed_koe_id():
    assert not lint_receipt(receipt("a", koe_id="not-a-koe")).ok


# --- macro-triad quorum ----------------------------------------------------------------------

def test_all_three_agree_quorum_ok_nothing_sick():
    a = assess_triad([receipt("a"), receipt("b"), receipt("c")])
    assert a.quorum_ok and a.canonical_commit == GOOD
    assert not a.sick_clusters and not a.needs_failback


def test_two_agree_one_diverges_names_the_sick_one():
    a = assess_triad([receipt("a"), receipt("b"),
                      receipt("c", state_root=SHA_B, commit=BAD)])
    assert a.quorum_ok and a.canonical_commit == GOOD and a.needs_failback
    assert len(a.sick_clusters) == 1
    sick = a.sick_clusters[0]
    assert sick.cluster == "did:web:c" and sick.head_commit == BAD


def test_koe_quarantined_master_is_sick():
    a = assess_triad([receipt("a"), receipt("b"),
                      receipt("c", koe_id="urn:lz:koe:fenced1")])
    assert a.quorum_ok and a.needs_failback
    assert a.sick_clusters[0].koe_id == "urn:lz:koe:fenced1"


def test_malformed_receipt_cannot_vote_and_is_sick():
    bad = receipt("c"); del bad["state_root"]
    a = assess_triad([receipt("a"), receipt("b"), bad])
    # a+b still make quorum; c is sick because its receipt won't lint
    assert a.quorum_ok and a.needs_failback
    assert any("malformed" in s.reason for s in a.sick_clusters)


def test_split_brain_no_quorum_fails_closed():
    a = assess_triad([receipt("a"),
                      receipt("b", state_root=SHA_B, commit=BAD),
                      receipt("c", state_root="sha256:" + "d" * 64, commit="3" * 40)])
    assert not a.quorum_ok and a.canonical_commit is None and not a.needs_failback


def test_two_sick_no_quorum_fails_closed():
    a = assess_triad([receipt("a"),
                      receipt("b", koe_id="urn:lz:koe:x1"),
                      receipt("c", koe_id="urn:lz:koe:x2")])
    assert not a.quorum_ok and not a.needs_failback  # only 1 healthy — below quorum 2


# --- failback producer (quorum-gated, revert-range, pr_opener-compatible) ---------------------

def test_failback_reverts_the_divergent_range():
    beacons = propose_state_failback(
        [receipt("a"), receipt("b"), receipt("c", state_root=SHA_B, commit=BAD)],
        repo="SocioProphet/infra",
    )
    assert len(beacons) == 1
    b = beacons[0]
    assert b["kind_class"] == "deploy_regression"
    assert b["proposal"]["revert"] == f"{GOOD}..{BAD}"
    assert b["detail"]["healthy_quorum"] == ["did:web:a", "did:web:b"]
    assert _valid(b["proposal"])  # the #585 pr_opener path accepts a revert proposal


def test_failback_empty_when_all_healthy():
    assert propose_state_failback([receipt("a"), receipt("b"), receipt("c")],
                                  repo="SocioProphet/infra") == []


def test_failback_empty_without_quorum():
    beacons = propose_state_failback(
        [receipt("a"),
         receipt("b", state_root=SHA_B, commit=BAD),
         receipt("c", state_root="sha256:" + "d" * 64, commit="3" * 40)],
        repo="SocioProphet/infra",
    )
    assert beacons == []  # no trusted target -> propose nothing


def test_failback_skips_quarantine_on_same_commit():
    # Sick by koe_id but serving the SAME (canonical) commit -> not a bad-deploy failback.
    beacons = propose_state_failback(
        [receipt("a"), receipt("b"),
         receipt("c", commit=GOOD, koe_id="urn:lz:koe:datacorruption")],
        repo="SocioProphet/infra",
    )
    assert beacons == []  # nothing to revert TO a different commit; re-sync path, not revert


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"macro_triad: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
