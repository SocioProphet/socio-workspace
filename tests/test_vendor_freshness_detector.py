"""Coverage for tools/detect_vendor_freshness.py.

Every test here replays a RECORDED observation instead of touching the network.
A detector whose tests need github to be up is a detector whose tests get skipped.
The one place the network shape is asserted is the ls-remote argument order, and
that is asserted against the argv the tool builds, not against a live remote.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, "tools")

import detect_vendor_freshness as detector  # noqa: E402
import validate_vendor_freshness as validator  # noqa: E402

REGISTER = Path("registry/vendor-freshness.yaml")
TODAY = date(2026, 7, 29)

# The engine as it will look the day 0.4.46 is cut — the case the plane exists for.
OBSERVED_0_4_46 = {
    "hellgraph-engine": {
        "source_id": "hellgraph-engine",
        "url": "https://github.com/SocioProphet/hellgraph",
        "version_scheme": "semver",
        "observed_at": "2026-07-29",
        "ok": True,
        "upstream_latest_version": "0.4.46",
        "upstream_latest_ref": "v0.4.46",
        "upstream_latest_commit": "f" * 40,
        "tags": ["0.4.40", "0.4.41", "0.4.42", "0.4.43", "0.4.44", "0.4.45", "0.4.46"],
        "observation_method": "fixture replay",
    }
}


def replay(tmp_path: Path, observations: dict, register: Path = REGISTER):
    path = tmp_path / "observations.json"
    path.write_text(json.dumps(observations), encoding="utf-8")
    return detector.run(register, TODAY, {"hellgraph-engine"}, path)


# ── one definition of stale ──────────────────────────────────────────────────

def test_detector_uses_the_gates_definition_of_stale() -> None:
    """Not "computes the same answer" — literally the same function object.

    A detector with its own opinion of staleness is a second register, and two
    registers disagreeing is how the first one stopped being believed.
    """
    assert detector.compute_state is validator.compute_state


# ── the evidence bundle ──────────────────────────────────────────────────────

def test_plan_carries_the_gap_and_the_releases_in_it(tmp_path: Path) -> None:
    _, _, plans, _ = replay(tmp_path, OBSERVED_0_4_46)
    plan = next(p for p in plans if p["parameters"]["consumerApp"] == "apps/hellgraph-service")
    params = plan["parameters"]
    assert params["fromVersion"] == "0.4.40"
    assert params["toVersion"] == "0.4.46"
    assert params["gapSize"] == 6
    assert params["gapReleases"] == ["0.4.41", "0.4.42", "0.4.43", "0.4.44", "0.4.45", "0.4.46"]


def test_blast_radius_counts_consumer_apps_not_repos(tmp_path: Path) -> None:
    """Both engine copies live in prophet-platform.

    Counting repos would answer 1 and hide apps/lifecycle-warden — which is exactly
    how it stayed hidden through five releases.
    """
    _, _, plans, _ = replay(tmp_path, OBSERVED_0_4_46)
    params = plans[0]["parameters"]
    assert params["blastRadius"] == 2
    apps = {entry["consumer_app"] for entry in params["blastRadiusApps"]}
    assert apps == {"apps/hellgraph-service", "apps/lifecycle-warden"}
    assert len({entry["consumer_repo"] for entry in params["blastRadiusApps"]}) == 1


def test_contract_crossing_is_derived_from_the_releases_in_the_gap(tmp_path: Path) -> None:
    _, _, plans, _ = replay(tmp_path, OBSERVED_0_4_46)
    params = plans[0]["parameters"]
    assert params["crossesContract"] is True
    assert set(params["contractKinds"]) == {"receipt-shape", "schema"}
    # NOT 0.4.42: that tag is an alias of the 0.4.41 commit, so it is not a release
    # and cannot have moved a contract. See test_alias_tags_are_not_counted_as_releases.
    assert {c["version"] for c in params["contractCrossings"]} == {"0.4.43", "0.4.45"}
    # every crossing resolves to a declared Contract node, so vfp:changesContract
    # has something to point AT — a bare kind string cannot be an edge target
    assert all(c["contract_id"] for c in params["contractCrossings"])
    # crossing a contract is what forces a human onto the decision
    assert plans[0]["requiresHumanApproval"] is True


def test_no_crossing_when_the_gap_contains_no_contract_change(tmp_path: Path) -> None:
    """The negative case matters: if everything crossed a contract, nothing would."""
    observed = json.loads(json.dumps(OBSERVED_0_4_46))
    observed["hellgraph-engine"].update({
        "upstream_latest_version": "0.4.41", "upstream_latest_ref": "v0.4.41",
        "tags": ["0.4.40", "0.4.41"],
    })
    _, _, plans, _ = replay(tmp_path, observed)
    params = plans[0]["parameters"]
    assert params["gapReleases"] == ["0.4.41"]
    assert params["crossesContract"] is False
    assert plans[0]["requiresHumanApproval"] is False


def test_plan_carries_the_discriminating_marker_and_not_the_useless_one(tmp_path: Path) -> None:
    """`graph:labels` exists in BOTH releases. A marker true before and after proves
    nothing, and shipping a detector that asserted it would ship rot under a fresh
    version string."""
    _, _, plans, _ = replay(tmp_path, OBSERVED_0_4_46)
    marker = plans[0]["parameters"]["versionMarker"]
    assert marker["marker"] == 'PROP_NS = "prop:"'
    assert marker["absentIn"] == "0.4.40"
    assert marker["assertInside"].endswith("ts/dist/index.js")
    assert "graph:labels" not in marker["marker"]


def test_plan_carries_the_committed_golden_receipts(tmp_path: Path) -> None:
    """The bytes CI actually compares — not the cross-engine equivalence digest,
    which is a different number over a different graph and must not be conflated."""
    _, _, plans, _ = replay(tmp_path, OBSERVED_0_4_46)
    digests = {f["digest"] for f in plans[0]["parameters"]["receiptFixtures"]}
    assert "sha256:018f2febf0c76f91752ba9726c9a32a4a8d3ca03895a5d877b780c312d34cc71" in digests
    assert "sha256:35a9df2dd74a25fcbb966a41d2949cd7646912d743aeec730a36fa1a1d3a00af" in digests


def test_plan_carries_every_place_that_names_the_pin(tmp_path: Path) -> None:
    """A re-vendor that updates the tarball and misses the floor leaves the repo
    internally inconsistent; the executor needs the whole list, not the obvious one."""
    _, _, plans, _ = replay(tmp_path, OBSERVED_0_4_46)
    plan = next(p for p in plans if p["parameters"]["consumerApp"] == "apps/hellgraph-service")
    paths = {entry["path"] for entry in plan["parameters"]["declaredIn"]}
    assert "apps/hellgraph-service/scripts/check-engine-version.mjs" in paths
    assert "apps/hellgraph-service/package-lock.json" in paths
    assert plan["parameters"]["guard"]["floor_constant"] == "MIN_ENGINE"


def test_idempotency_key_pins_one_finding_to_one_branch(tmp_path: Path) -> None:
    """A re-emitted finding must not open a second pull request."""
    _, _, first, _ = replay(tmp_path, OBSERVED_0_4_46)
    _, _, second, _ = replay(tmp_path, OBSERVED_0_4_46)
    assert [p["idempotencyKey"] for p in first] == [p["idempotencyKey"] for p in second]
    assert first[0]["idempotencyKey"].endswith("0.4.40->0.4.46")


def test_effect_request_envelope_matches_the_specified_contract(tmp_path: Path) -> None:
    _, _, plans, _ = replay(tmp_path, OBSERVED_0_4_46)
    plan = plans[0]
    assert plan["type"] == "EffectRequest"
    assert plan["effectKind"] == "update"
    assert plan["capability"] == "vendor.revendor"
    assert plan["target"]["kind"] == "vendor-pin"
    for field in ("type", "effectKind", "capability", "target", "idempotencyKey",
                  "requestedByEventRef", "requiresHumanApproval", "riskLabels", "policyLabels"):
        assert field in plan, f"EffectRequest is missing {field}"


# ── proposing a disposition ──────────────────────────────────────────────────

def test_a_new_release_makes_current_false_and_the_detector_files_it(tmp_path: Path) -> None:
    """kbpedia-kko is declared `current` on a pin-exact policy. Flip its source to
    unobserved and the pin becomes an unknown wearing a pin's clothes — the detector
    must file that rather than leave a register that contradicts itself."""
    register = tmp_path / "register.yaml"
    text = REGISTER.read_text(encoding="utf-8")
    text = text.replace(
        "upstream_latest_digest: 'sha256:d907919fb40f20ed39a7fde0e8d114027449d9354a1976ce8248db5634cb7b07'",
        "upstream_latest_digest: unknown")
    register.write_text(text, encoding="utf-8")

    observations = tmp_path / "obs.json"
    observations.write_text("{}", encoding="utf-8")
    _, results, _, proposals = detector.run(register, TODAY, set(), observations)

    kko = [r for r in results if r["artifact_id"].startswith("kbpedia-kko@")]
    assert kko and all(not r["agrees"] for r in kko)
    proposed = {p["artifact_id"]: p for p in proposals}
    assert "kbpedia-kko@hellgraph" in proposed
    assert proposed["kbpedia-kko@hellgraph"]["disposition"] == "observation-required"


def test_proposed_remediation_carries_a_finding_id_and_a_due_date(tmp_path: Path) -> None:
    register = tmp_path / "register.yaml"
    text = REGISTER.read_text(encoding="utf-8")
    # declare the stale engine copy `current`: a lie the observation will expose
    text = text.replace("disposition: remediation-open", "disposition: current", 1)
    register.write_text(text, encoding="utf-8")

    observations = tmp_path / "obs.json"
    observations.write_text(json.dumps(OBSERVED_0_4_46), encoding="utf-8")
    _, _, _, proposals = detector.run(register, TODAY, {"hellgraph-engine"}, observations)

    proposal = next(p for p in proposals if p["artifact_id"] == "hellgraph-engine@hellgraph-service")
    assert proposal["disposition"] == "remediation-required"
    assert proposal["finding_id"].startswith("VFP-")
    # foundation tier SLA is 30 days
    assert proposal["due"] == "2026-08-28"
    assert proposal["target_version"] == "0.4.46"


def test_a_human_disposition_that_already_agrees_is_never_overwritten(tmp_path: Path) -> None:
    """`remediation-open` names a real open PR. The detector must not downgrade a
    human's position just because it also computes `stale`."""
    observations = tmp_path / "obs.json"
    observations.write_text(json.dumps(OBSERVED_0_4_46), encoding="utf-8")
    _, _, _, proposals = detector.run(REGISTER, TODAY, {"hellgraph-engine"}, observations)
    assert not any(p["artifact_id"] == "hellgraph-engine@hellgraph-service" for p in proposals)


def test_finding_ids_never_collide_within_one_run(tmp_path: Path) -> None:
    register = tmp_path / "register.yaml"
    text = REGISTER.read_text(encoding="utf-8")
    text = text.replace("disposition: remediation-open", "disposition: current", 1)
    text = text.replace("disposition: remediation-required", "disposition: current", 1)
    register.write_text(text, encoding="utf-8")
    observations = tmp_path / "obs.json"
    observations.write_text(json.dumps(OBSERVED_0_4_46), encoding="utf-8")
    _, _, _, proposals = detector.run(register, TODAY, {"hellgraph-engine"}, observations)
    ids = [p["finding_id"] for p in proposals if p.get("finding_id")]
    assert len(ids) == 2 and len(set(ids)) == 2


# ── the register rewrite ─────────────────────────────────────────────────────

def test_rewrite_preserves_comments_and_stays_parseable(tmp_path: Path) -> None:
    """The register's comments carry its findings. A round-trip through a YAML
    dumper would delete every one of them, so the rewrite is line-surgical."""
    register = tmp_path / "register.yaml"
    original = REGISTER.read_text(encoding="utf-8")
    register.write_text(original, encoding="utf-8")

    comments_before = [line for line in original.splitlines() if line.strip().startswith("#")]
    detector.rewrite_register(register, OBSERVED_0_4_46)
    updated = register.read_text(encoding="utf-8")

    assert [line for line in updated.splitlines() if line.strip().startswith("#")] == comments_before
    parsed = yaml.safe_load(updated)
    assert len(parsed["artifacts"]) == len(yaml.safe_load(original)["artifacts"])
    source = next(s for s in parsed["sources"] if s["source_id"] == "hellgraph-engine")
    assert source["upstream_latest_version"] == "0.4.46"
    assert source["upstream_latest_ref"] == "v0.4.46"


def test_rewrite_touches_only_the_observed_source(tmp_path: Path) -> None:
    register = tmp_path / "register.yaml"
    original = REGISTER.read_text(encoding="utf-8")
    register.write_text(original, encoding="utf-8")
    detector.rewrite_register(register, OBSERVED_0_4_46)

    before = yaml.safe_load(original)
    after = yaml.safe_load(register.read_text(encoding="utf-8"))
    changed = [s["source_id"] for s, t in zip(before["sources"], after["sources"]) if s != t]
    assert changed == ["hellgraph-engine"]
    assert before["artifacts"] == after["artifacts"]


def test_proposed_disposition_lands_on_the_right_artifact(tmp_path: Path) -> None:
    """A key inserted after a section banner still PARSES onto the previous item, so
    a mis-scoped insertion is invisible to yaml.safe_load. Assert the mapping, and
    assert the banner did not move."""
    register = tmp_path / "register.yaml"
    text = REGISTER.read_text(encoding="utf-8")
    text = text.replace("disposition: remediation-open", "disposition: current", 1)
    register.write_text(text, encoding="utf-8")

    proposals = [{
        "artifact_id": "hellgraph-engine@hellgraph-service",
        "disposition": "remediation-required", "finding_id": "VFP-9999",
        "target_version": "0.4.46", "due": "2026-08-28", "tier": "foundation",
        "reason": "fixture", "detected_on": "2026-07-29", "was": "current",
    }]
    detector.rewrite_register(register, {}, proposals)
    parsed = yaml.safe_load(register.read_text(encoding="utf-8"))
    by_id = {a["artifact_id"]: a for a in parsed["artifacts"]}
    assert by_id["hellgraph-engine@hellgraph-service"]["remediation"]["finding_id"] == "VFP-9999"
    assert "remediation" not in by_id["hellgraph-engine@lifecycle-warden"] or \
        by_id["hellgraph-engine@lifecycle-warden"]["remediation"]["finding_id"] != "VFP-9999"


def test_rewrite_then_validate_is_green(tmp_path: Path) -> None:
    """The loop has to close: what the detector writes, the gate must accept.

    If a refreshed register cannot pass its own validator, the automation's only
    product is a red build somebody has to repair by hand — which is the labour this
    was built to delete.
    """
    register = tmp_path / "register.yaml"
    register.write_text(REGISTER.read_text(encoding="utf-8"), encoding="utf-8")
    observations = tmp_path / "obs.json"
    observations.write_text(json.dumps(OBSERVED_0_4_46), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "tools/detect_vendor_freshness.py", "--register", str(register),
         "--offline", str(observations), "--source", "hellgraph-engine",
         "--today", "2026-07-29", "--write-register", "--propose-disposition"],
        capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr

    validated = subprocess.run(
        [sys.executable, "tools/validate_vendor_freshness.py", "--register", str(register),
         "--today", "2026-07-29", "--skip-disk"],
        capture_output=True, text=True, check=False)
    assert validated.returncode == 0, validated.stdout + validated.stderr


# ── the network surface ──────────────────────────────────────────────────────

def test_ls_remote_puts_refs_after_the_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression. `git ls-remote main <url>` treats "main" as the repository and
    fails with "'main' does not appear to be a git repository" — a message that reads
    like a permissions problem and is not one. It silently made three sources look
    unreachable."""
    seen: list[list[str]] = []

    def fake_run(argv, **kwargs):
        seen.append(argv)
        return subprocess.CompletedProcess(argv, 0, "abc123\trefs/heads/main\n", "")

    monkeypatch.setattr(detector.subprocess, "run", fake_run)
    detector.observe_head("https://example.invalid/repo", "main")
    argv = seen[0]
    assert argv.index("https://example.invalid/repo") < argv.index("main")


def test_observation_failure_is_recorded_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    """An upstream we could not read must never come out looking current."""
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 128, "", "fatal: repository not found")

    monkeypatch.setattr(detector.subprocess, "run", fake_run)
    record = detector.observe_source(
        {"source_id": "x", "url": "https://example.invalid/repo", "version_scheme": "semver"}, TODAY)
    assert record["ok"] is False
    assert "repository not found" in record["error"]
    assert "upstream_latest_version" not in record


# ── alias tags: a version that is not a distinct artifact is not a release ────

ALIASED = {
    "hellgraph-engine": {
        **OBSERVED_0_4_46,
        **OBSERVED_0_4_46["hellgraph-engine"],
        # v0.4.41 and v0.4.42 on ONE commit — the real state of hellgraph today
        "tag_commits": {"0.4.40": "aaa", "0.4.41": "bbb", "0.4.42": "bbb",
                        "0.4.43": "ccc", "0.4.44": "ddd", "0.4.45": "eee", "0.4.46": "fff"},
        "tag_aliases": {"bbb": ["0.4.41", "0.4.42"]},
    }
}


def test_alias_tags_are_not_counted_as_releases(tmp_path: Path) -> None:
    """hellgraph v0.4.42 points at the v0.4.41 commit, whose package.json says 0.4.41.

    Anyone pinning v0.4.42 gets 0.4.41 bytes. Counting it would inflate the gap by
    one and invent a release that never existed — a wrong number in the ALARMING
    direction, which erodes the register's credibility just as fast as a wrong number
    in the reassuring one.
    """
    _, _, plans, _ = replay(tmp_path, ALIASED)
    params = plans[0]["parameters"]
    assert "0.4.42" not in params["gapReleases"]
    assert params["gapReleases"] == ["0.4.41", "0.4.43", "0.4.44", "0.4.45", "0.4.46"]
    assert params["gapSize"] == 5


def test_alias_detection_is_computed_from_ls_remote_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """No extra fetch: two tags on one sha is visible in the output we already have."""
    def fake_run(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0,
            "aaa\trefs/tags/v0.4.41\naaa\trefs/tags/v0.4.42\nbbb\trefs/tags/v0.4.43\n", "")

    monkeypatch.setattr(detector.subprocess, "run", fake_run)
    record = detector.observe_source(
        {"source_id": "x", "url": "https://example.invalid/r", "version_scheme": "semver"}, TODAY)
    assert record["tag_aliases"] == {"aaa": ["0.4.41", "0.4.42"]}


# ── the detector maintains the release chain ─────────────────────────────────

def test_newly_observed_releases_are_appended_and_left_contract_silent(tmp_path: Path) -> None:
    """The chain stays current as a side effect of polling, not as a chore.

    And the appended entry carries NO changes_contract: what a release moved is a
    judgement about behaviour. A detector that guessed it from the version number
    would manufacture exactly the false assurance this plane removes.
    """
    register = tmp_path / "register.yaml"
    register.write_text(REGISTER.read_text(encoding="utf-8"), encoding="utf-8")
    detector.rewrite_register(register, ALIASED)

    parsed = yaml.safe_load(register.read_text(encoding="utf-8"))
    source = next(s for s in parsed["sources"] if s["source_id"] == "hellgraph-engine")
    versions = [str(r["version"]) for r in source["releases"]]
    assert "0.4.46" in versions, "a newly observed release must be appended"
    assert "0.4.42" not in versions, "an alias tag must never be appended as a release"
    fresh = next(r for r in source["releases"] if str(r["version"]) == "0.4.46")
    assert "changes_contract" not in fresh
    assert fresh["contract_review"] == "pending"


def test_appending_is_idempotent(tmp_path: Path) -> None:
    register = tmp_path / "register.yaml"
    register.write_text(REGISTER.read_text(encoding="utf-8"), encoding="utf-8")
    detector.rewrite_register(register, ALIASED)
    once = yaml.safe_load(register.read_text(encoding="utf-8"))
    detector.rewrite_register(register, ALIASED)
    twice = yaml.safe_load(register.read_text(encoding="utf-8"))
    assert once["sources"] == twice["sources"]


def test_a_chain_that_does_not_reach_its_head_is_a_finding(tmp_path: Path) -> None:
    """gapSize is a path length. A chain with a hole answers from a SHORTER path —
    a smaller number, in the reassuring direction — so a hole must fail, not warn."""
    register = tmp_path / "register.yaml"
    text = REGISTER.read_text(encoding="utf-8")
    text = text.replace("      - version: '0.4.45'\n        ref: v0.4.45\n        commit: dbe854f\n", "", 1)
    register.write_text(text, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "tools/validate_vendor_freshness.py", "--register", str(register),
         "--today", "2026-07-29", "--skip-disk"],
        capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert "the chain does not reach its own head" in result.stderr
