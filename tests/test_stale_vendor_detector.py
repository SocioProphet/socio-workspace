"""stale_vendor detector: detect + escalate (the fix is a cross-repo re-vendor).

The detector uses the register's own compute_state, so it can never disagree with the gate.
Because there is no locally-computable fix, the beacon carries no proposal — the responder
caps stale_vendor at propose_pr and, with nothing to file, escalates to a human with the
staleness report. `waived` staleness is not flagged.
"""

import textwrap

import pytest

from automation import detectors, responder
from automation.durable_queue import DurableQueue, state_dir


FIXTURE_REGISTER = textwrap.dedent(
    """\
    manifest_id: test
    sources:
      - source_id: libx
        version_scheme: semver
        upstream_latest_version: "2.0.0"
    artifacts:
      - artifact_id: libx@consumer-a
        source_id: libx
        consumer_repo: Org/consumer-a
        vendored_version: "1.0.0"          # stale (behind 2.0.0)
        freshness_policy: track-minor
        disposition: remediation-required
      - artifact_id: libx@consumer-b
        source_id: libx
        consumer_repo: Org/consumer-b
        vendored_version: "2.0.0"          # current
        freshness_policy: track-minor
        disposition: current
      - artifact_id: libx@consumer-c
        source_id: libx
        consumer_repo: Org/consumer-c
        vendored_version: "1.0.0"          # stale but WAIVED
        freshness_policy: track-minor
        disposition: waived
    """
)


@pytest.fixture
def register(tmp_path):
    p = tmp_path / "vendor-freshness.yaml"
    p.write_text(FIXTURE_REGISTER, encoding="utf-8")
    return p


def test_detects_only_unwaived_stale(register):
    beacons = detectors.detect_stale_vendors(register_path=register)

    ids = {b["detail"]["artifact_id"] for b in beacons}
    assert ids == {"libx@consumer-a"}            # current not flagged, waived not flagged
    b = beacons[0]
    assert b["kind_class"] == "stale_vendor"
    assert b["evidence"]["detector"] == "vendor_freshness.compute_state"
    assert b["detail"]["version_scheme"] == "semver"
    assert b["detail"]["vendored_ref"] == "1.0.0"        # scheme-appropriate typed identity
    assert b["detail"]["upstream_ref"] == "2.0.0"
    assert "proposal" not in b                    # no locally-computable fix


def test_commit_scheme_carries_shas_not_null(tmp_path):
    # the real defect: a commit-scheme vendor had null vendored_version; the identity must
    # now land in the scheme-appropriate typed fields, not only in the prose reason.
    reg = tmp_path / "reg.yaml"
    reg.write_text(textwrap.dedent("""\
        sources:
          - source_id: schemas
            version_scheme: commit
            upstream_latest_commit: 90c1384032cc069738d273df8e9877d46ec2820f
        artifacts:
          - artifact_id: schemas@consumer
            source_id: schemas
            vendored_commit: 487e4b614b79e556af3aea2c70471eca13281377
            disposition: remediation-required
    """), encoding="utf-8")
    b = detectors.detect_stale_vendors(register_path=reg)[0]
    assert b["detail"]["version_scheme"] == "commit"
    assert b["detail"]["vendored_ref"] == "487e4b614b79e556af3aea2c70471eca13281377"
    assert b["detail"]["upstream_ref"] == "90c1384032cc069738d273df8e9877d46ec2820f"


def test_no_stale_no_beacons(tmp_path):
    reg = tmp_path / "reg.yaml"
    reg.write_text(textwrap.dedent("""\
        sources:
          - source_id: libx
            version_scheme: semver
            upstream_latest_version: "2.0.0"
        artifacts:
          - artifact_id: libx@ok
            source_id: libx
            vendored_version: "2.0.0"
            freshness_policy: track-minor
            disposition: current
    """), encoding="utf-8")
    assert detectors.detect_stale_vendors(register_path=reg) == []


def test_real_register_detector_runs_and_is_well_formed():
    """Witness on the REAL register: the detector runs and emits well-formed beacons."""
    beacons = detectors.detect_stale_vendors()
    for b in beacons:
        assert b["kind_class"] == "stale_vendor"
        assert b["detail"]["state"] == "stale"
        assert b["detail"]["disposition"] != "waived"
        assert "proposal" not in b


# --- full loop: detect -> decide -> escalate with report --------------------

def test_full_loop_stale_vendor_escalates_with_report(register, tmp_path, monkeypatch):
    monkeypatch.setenv("SOCIOSPHERE_STATE_DIR", str(tmp_path / "state"))
    inbox = DurableQueue(state_dir() / "beacons")
    decisions = DurableQueue(state_dir() / "decisions")

    emitted = detectors.run_detectors(
        inbox=inbox, detector_paths={"register_path": register},
        detectors=[detectors.detect_stale_vendors],
    )
    assert len(emitted) == 1

    out = responder.run_once(inbox=inbox, decisions=decisions, execute=True,
                             executor_paths={"proposals_dir": tmp_path / "proposals"})

    r = out[0]
    # capped at propose_pr (weak), but with no computable proposal -> human, with the report
    assert r["execution"]["proposed"] is False
    assert r["action"] == "escalate_human"
    assert r["detail"]["artifact_id"] == "libx@consumer-a"
    assert r["detail"]["reason"]                       # the staleness explanation is carried
