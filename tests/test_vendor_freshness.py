"""Coverage for tools/validate_vendor_freshness.py.

Every negative vector in fixtures/vendor-freshness/ is executed here. A fixture
that is written but never run is exactly the failure mode this plane exists to
stop, so the parametrised list below is asserted to cover the whole directory.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path("fixtures/vendor-freshness")
VALIDATOR = "tools/validate_vendor_freshness.py"
# Fixed so date-based checks (waiver expiry, remediation due, observation age)
# assert behaviour rather than drifting with the wall clock.
TODAY = "2026-07-29"

ENGINE_DIGEST = "sha256:a1f477969c8f335f95d806baeee349c8d1bbfc9e288665f20caa8a2a016aa6e0"


def run(register: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", VALIDATOR, "--register", str(register), "--today", TODAY, *extra],
        capture_output=True,
        text=True,
        check=False,
    )


# ── the real register ────────────────────────────────────────────────────────

def test_committed_register_is_valid() -> None:
    """The register as committed must pass its own validator."""
    result = run(Path("registry/vendor-freshness.yaml"), "--skip-disk")
    assert result.returncode == 0, result.stderr


def test_committed_register_reports_the_staleness_it_actually_has() -> None:
    """Whatever is stale must be SURFACED as stale, never silently accepted.

    Rewritten when VFP-0001 closed. It used to assert the two engine copies were stale,
    which was the truth on 2026-07-29 morning and stopped being the truth that afternoon
    when prophet-platform #1030 and #1032 landed 0.4.45 in both. A test that asserts a
    finding which has been FIXED is a test that must be edited to stay green, and the
    thing to assert is the invariant, not the snapshot: staleness is reported.

    The staleness that remains is sourceos-spec, and it is real — two consumers pinning
    two different commits of one schema family, both behind upstream 65925aed.
    """
    result = run(Path("registry/vendor-freshness.yaml"), "--skip-disk")
    assert "STALE sourceos-spec-schemas@market-replay" in result.stdout
    assert "STALE sourceos-spec-schemas@hellgraph-service" in result.stdout
    # A guard nobody calls stays a declared finding in its own right — and these two are
    # now here on EVIDENCE rather than on assertion; see the invoked_by_ci tests below.
    assert "GUARD-NOT-INVOKED sourceos-spec-schemas@market-replay" in result.stdout
    assert "GUARD-NOT-INVOKED sourceos-spec-schemas@hellgraph-service" in result.stdout


def test_committed_register_keeps_the_engine_closed() -> None:
    """VFP-0001 is closed and must stay closed: neither engine copy may read stale."""
    result = run(Path("registry/vendor-freshness.yaml"), "--skip-disk")
    assert result.returncode == 0, result.stderr
    assert "STALE hellgraph-engine@" not in result.stdout


POSITIVE = ["good-minimal.yaml", "good-reference-observation-tolerated.yaml"]


@pytest.mark.parametrize("filename", POSITIVE)
def test_positive_control_passes(filename: str) -> None:
    result = run(FIXTURES / filename, "--skip-disk")
    assert result.returncode == 0, result.stderr


# ── negative vectors ─────────────────────────────────────────────────────────

NEGATIVE = [
    ("bad-stale-declared-current.yaml", "computed freshness is 'stale'"),
    ("bad-stale-without-remediation.yaml", "requires remediation.finding_id"),
    ("bad-overdue-remediation.yaml", "is overdue"),
    ("bad-expired-waiver.yaml", "waiver expired"),
    ("bad-stale-observation.yaml", "observation is"),
    ("bad-unknown-source-ref.yaml", "references unknown source_id"),
    ("bad-pin-exact-without-reason.yaml", "requires pin_reason"),
    ("bad-unbound-source.yaml", "is not declared in manifest/workspace.toml"),
    ("bad-missing-fields.yaml", "missing required fields"),
    ("bad-enum-values.yaml", "must be one of"),
    # ── W12.5: tier-based severity ──
    ("bad-missing-tier.yaml", "missing required fields: ['tier']"),
    ("bad-foundation-without-tier-reason.yaml", "tier foundation requires tier_reason"),
    ("bad-foundation-observation-too-old.yaml", "tier foundation limit 30"),
    ("bad-foundation-unobservable-without-gap.yaml", "declare observation_gap"),
    ("bad-expired-observation-gap.yaml", "observation_gap revisit_by has passed"),
]


@pytest.mark.parametrize("filename,expected", NEGATIVE)
def test_negative_vector_is_rejected(filename: str, expected: str) -> None:
    result = run(FIXTURES / filename, "--skip-disk")
    assert result.returncode == 1, f"{filename} should have failed\n{result.stdout}"
    assert expected in result.stderr, f"{filename} failed for the wrong reason:\n{result.stderr}"


def test_every_bad_fixture_is_exercised() -> None:
    """No negative vector may sit in the directory unrun."""
    on_disk = {p.name for p in FIXTURES.glob("bad-*.yaml")}
    covered = {name for name, _ in NEGATIVE}
    assert on_disk == covered, f"unexercised fixtures: {sorted(on_disk - covered)}"


def test_every_good_fixture_is_exercised() -> None:
    """A positive control nobody runs proves nothing either."""
    on_disk = {p.name for p in FIXTURES.glob("good-*.yaml")}
    assert on_disk == set(POSITIVE), f"unexercised positive controls: {sorted(on_disk - set(POSITIVE))}"


# ── tier changes the VERDICT, not just the wording ───────────────────────────

def test_tier_decides_the_observation_budget() -> None:
    """The tier pair is the whole claim of W12.5, so assert it as a pair.

    Both fixtures carry the SAME 44-day-old observation. foundation (30) must fail
    and reference (90) must pass. If they ever agree, tier has become decoration.
    """
    strict = run(FIXTURES / "bad-foundation-observation-too-old.yaml", "--skip-disk")
    lenient = run(FIXTURES / "good-reference-observation-tolerated.yaml", "--skip-disk")
    assert strict.returncode == 1, strict.stdout
    assert "tier foundation limit 30" in strict.stderr
    assert lenient.returncode == 0, lenient.stderr


def test_tier_never_softens_a_contradiction() -> None:
    """A disposition that contradicts the computed state fails at EVERY tier.

    Tier grades unverifiability. If it could also grade contradiction it would be a
    supported way to opt out of the gate, which is the one thing it must not be.
    """
    source = (FIXTURES / "bad-stale-declared-current.yaml").read_text(encoding="utf-8")
    assert "tier: reference" in source
    for tier in ("reference", "foundation"):
        text = source.replace("tier: reference", f"tier: {tier}")
        if tier == "foundation":
            text = text.replace(f"tier: {tier}", f"tier: {tier}\n    tier_reason: fixture")
        path = FIXTURES.parent / f"_tmp-tier-{tier}.yaml"
        path.write_text(text, encoding="utf-8")
        try:
            result = run(path, "--skip-disk")
            assert result.returncode == 1, f"tier {tier} let a contradiction through"
            assert "computed freshness is 'stale'" in result.stderr
        finally:
            path.unlink()


# ── fail-closed: an unverified repo must never read as verified ──────────────

def test_require_disk_turns_skipped_into_failure(tmp_path: Path) -> None:
    """--skip-disk is honest locally and dishonest in CI.

    The workflow materializes the consumer repos on purpose. A checkout that
    silently did not happen would make the whole on-disk layer a no-op that still
    printed green, which is the failure class this plane exists for.
    """
    register = register_for("0.4.45", ENGINE_DIGEST, tmp_path)
    lenient = run(register, "--repo-root=prophet-platform=/nonexistent-path")
    assert lenient.returncode == 0
    assert "SKIPPED on-disk verification" in lenient.stdout

    strict = run(register, "--repo-root=prophet-platform=/nonexistent-path",
                 "--require-disk", "prophet-platform")
    assert strict.returncode == 1, strict.stdout
    assert "Refusing to report a pass for bytes nobody read" in strict.stderr


def test_require_disk_and_skip_disk_are_contradictory(tmp_path: Path) -> None:
    register = register_for("0.4.45", ENGINE_DIGEST, tmp_path)
    result = run(register, "--skip-disk", "--require-disk", "prophet-platform")
    assert result.returncode == 1
    assert "contradictory" in result.stderr


def test_require_disk_rejects_an_unknown_repo(tmp_path: Path) -> None:
    """Guarding a repo the register does not know about is a typo, not a guard."""
    register = register_for("0.4.45", ENGINE_DIGEST, tmp_path)
    result = run(register, "--repo-root=prophet-platform=/nonexistent",
                 "--require-disk", "prophet-platfrom")
    assert result.returncode == 1
    assert "which no artifact declares as a consumer_repo" in result.stderr


# ── on-disk drift, against a synthetic consumer repo ─────────────────────────

def build_consumer(root: Path, tarball_version: str, payload: bytes) -> None:
    """A minimal prophet-platform-shaped repo with one vendored tarball."""
    app = root / "apps" / "hellgraph-service"
    (app / "vendor").mkdir(parents=True)
    (app / "vendor" / f"socioprophet-hellgraph-{tarball_version}.tgz").write_bytes(payload)
    (app / "package.json").write_text(
        json.dumps({
            "name": "hellgraph-service",
            "dependencies": {"@socioprophet/hellgraph": f"file:vendor/socioprophet-hellgraph-{tarball_version}.tgz"},
        }),
        encoding="utf-8",
    )


def register_for(root_version: str, digest: str, tmp_path: Path) -> Path:
    text = (FIXTURES / "good-minimal.yaml").read_text(encoding="utf-8")
    text = text.replace("0.4.45.tgz", f"{root_version}.tgz")
    text = text.replace("vendored_version: 0.4.45", f"vendored_version: {root_version}")
    text = text.replace(
        "    owner: '@mdheller'",
        f"    vendored_digest: '{digest}'\n    owner: '@mdheller'",
    )
    if root_version != "0.4.45":
        # The supersession chain must reach whatever this register pins, or the
        # chain check fires and the test fails for a reason it is not about.
        text = text.replace(
            "      - version: '0.4.45'\n        ref: v0.4.45",
            f"      - version: '0.4.45'\n        ref: v0.4.45\n"
            f"      - version: '{root_version}'\n        ref: v{root_version}")
        text = text.replace("disposition: current", "disposition: remediation-required")
        text += "    remediation:\n      finding_id: VFP-TEST\n      due: '2026-12-31'\n"
    path = tmp_path / "register.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_digest_drift_is_detected(tmp_path: Path) -> None:
    """Recorded digest must match the bytes actually vendored."""
    root = tmp_path / "prophet-platform"
    build_consumer(root, "0.4.45", b"these are not the bytes you recorded")
    register = register_for("0.4.45", ENGINE_DIGEST, tmp_path)

    result = run(register, f"--repo-root=prophet-platform={root}")
    assert result.returncode == 1
    assert "DRIFT" in result.stderr


def test_matching_digest_passes(tmp_path: Path) -> None:
    payload = b"engine tarball bytes"
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    root = tmp_path / "prophet-platform"
    build_consumer(root, "0.4.45", payload)
    register = register_for("0.4.45", digest, tmp_path)

    result = run(register, f"--repo-root=prophet-platform={root}")
    assert result.returncode == 0, result.stderr


def test_undeclared_vendored_artifact_is_detected(tmp_path: Path) -> None:
    """The lifecycle-warden case: a second vendored copy nothing declares."""
    payload = b"engine tarball bytes"
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    root = tmp_path / "prophet-platform"
    build_consumer(root, "0.4.45", payload)

    warden = root / "apps" / "lifecycle-warden" / "vendor"
    warden.mkdir(parents=True)
    (warden / "socioprophet-hellgraph-0.4.45.tgz").write_bytes(payload)

    register = register_for("0.4.45", digest, tmp_path)
    result = run(register, f"--repo-root=prophet-platform={root}")
    assert result.returncode == 1
    assert "UNDECLARED" in result.stderr
    assert "lifecycle-warden" in result.stderr


def test_undeclared_file_dependency_is_detected(tmp_path: Path) -> None:
    """A file: specifier pointing outside any declared artifact path."""
    payload = b"engine tarball bytes"
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    root = tmp_path / "prophet-platform"
    build_consumer(root, "0.4.45", payload)

    other = root / "apps" / "other-service"
    other.mkdir(parents=True)
    (other / "sidecar.tgz").write_bytes(payload)
    (other / "package.json").write_text(
        json.dumps({"name": "other", "dependencies": {"@socioprophet/sidecar": "file:sidecar.tgz"}}),
        encoding="utf-8",
    )

    register = register_for("0.4.45", digest, tmp_path)
    result = run(register, f"--repo-root=prophet-platform={root}")
    assert result.returncode == 1
    assert "UNDECLARED file: dependency" in result.stderr


def test_missing_declared_path_is_detected(tmp_path: Path) -> None:
    payload = b"engine tarball bytes"
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    root = tmp_path / "prophet-platform"
    build_consumer(root, "0.4.45", payload)
    # register claims 0.4.46; disk has 0.4.45
    register = register_for("0.4.46", digest, tmp_path)

    result = run(register, f"--repo-root=prophet-platform={root}")
    assert result.returncode == 1
    assert "declared path does not exist" in result.stderr


def test_absent_consumer_repo_is_skipped_not_passed(tmp_path: Path) -> None:
    """An unverifiable repo must be reported as skipped, never silently green."""
    register = register_for("0.4.45", ENGINE_DIGEST, tmp_path)
    result = run(register, "--repo-root=prophet-platform=/nonexistent-path")
    assert result.returncode == 0, result.stderr
    assert "SKIPPED on-disk verification" in result.stdout


# ── invoked_by_ci is VERIFIED, never asserted (W12.6) ────────────────────────
#
# The hole this closes, in its own words: hellgraph-service's engine guard was declared
# in package.json as `check:engine`, invoked by no workflow, no Makefile target and no
# Dockerfile, and had never once run — while being cited as the authority that stale
# engines get caught. A boolean anyone can type is not evidence. These tests build a
# synthetic consumer repo so the chain-follower is exercised against real files rather
# than against a mock of itself.

GUARD_REL = "apps/hellgraph-service/scripts/check-engine-version.mjs"


def with_guard(root: Path, *, workflow: str | None = None, makefile: str | None = None,
               scripts: dict | None = None, floor: str = "0.4.45") -> None:
    """Add a guard script to a consumer repo, plus whatever claims to invoke it."""
    guard = root / GUARD_REL
    guard.parent.mkdir(parents=True, exist_ok=True)
    guard.write_text(f"const MIN_ENGINE = '{floor}'\n", encoding="utf-8")
    if workflow is not None:
        wf = root / ".github" / "workflows"
        wf.mkdir(parents=True, exist_ok=True)
        (wf / "ci.yml").write_text(workflow, encoding="utf-8")
    if makefile is not None:
        (root / "Makefile").write_text(makefile, encoding="utf-8")
    if scripts is not None:
        package = root / "apps" / "hellgraph-service" / "package.json"
        manifest = json.loads(package.read_text(encoding="utf-8"))
        manifest["scripts"] = scripts
        package.write_text(json.dumps(manifest), encoding="utf-8")


def register_with_guard(tmp_path: Path, digest: str, guard: dict) -> Path:
    text = (FIXTURES / "good-minimal.yaml").read_text(encoding="utf-8")
    text = text.replace(
        "    owner: '@mdheller'",
        f"    vendored_digest: '{digest}'\n"
        + "    guard:\n"
        + "".join(f"      {k}: {v}\n" for k, v in guard.items())
        + "    owner: '@mdheller'",
    )
    path = tmp_path / "register.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def guarded(tmp_path: Path, guard: dict, **repo: object) -> subprocess.CompletedProcess[str]:
    payload = b"engine tarball bytes"
    digest = "sha256:" + hashlib.sha256(payload).hexdigest()
    root = tmp_path / "prophet-platform"
    build_consumer(root, "0.4.45", payload)
    with_guard(root, **repo)  # type: ignore[arg-type]
    register = register_with_guard(tmp_path, digest, guard)
    return run(register, f"--repo-root=prophet-platform={root}")


def test_invoked_by_ci_true_with_no_caller_anywhere_fails(tmp_path: Path) -> None:
    """The check:engine case exactly: the guard exists, and nothing runs it."""
    result = guarded(tmp_path, {"path": GUARD_REL, "invoked_by_ci": "true"})
    assert result.returncode == 1
    assert "declares guard.invoked_by_ci: true" in result.stderr


def test_invoked_by_ci_true_with_an_npm_script_nobody_runs_still_fails(tmp_path: Path) -> None:
    """A package.json script IS the hole, not the fix. Declaring is not invoking."""
    result = guarded(
        tmp_path, {"path": GUARD_REL, "invoked_by_ci": "true"},
        scripts={"check:engine": "node scripts/check-engine-version.mjs"},
        workflow="name: ci\njobs:\n  build:\n    steps:\n      - run: npm ci\n",
    )
    assert result.returncode == 1
    assert "no package.json script that runs it is itself run" in result.stderr


def test_invoked_by_ci_true_via_a_make_target_in_a_workflow_passes(tmp_path: Path) -> None:
    """The real prophet-platform shape: workflow matrix -> make engine-guards -> node."""
    result = guarded(
        tmp_path, {"path": GUARD_REL, "invoked_by_ci": "true"},
        makefile=f"engine-guards:\n\tnode {GUARD_REL}\n",
        workflow="name: ci\njobs:\n  d:\n    strategy:\n      matrix:\n"
                 "        target:\n          - engine-guards\n"
                 "    steps:\n      - run: make ${{ matrix.target }}\n",
    )
    assert result.returncode == 0, result.stderr
    assert "GUARD-INVOKED" in result.stdout


def test_a_make_target_no_workflow_runs_is_not_evidence(tmp_path: Path) -> None:
    """Reachability is from CI. A target only a human types has never run in CI."""
    result = guarded(
        tmp_path, {"path": GUARD_REL, "invoked_by_ci": "true"},
        makefile=f"engine-guards:\n\tnode {GUARD_REL}\n",
        workflow="name: ci\njobs:\n  d:\n    steps:\n      - run: make lint\n",
    )
    assert result.returncode == 1
    assert "no CI-reachable make target runs it" in result.stderr


def test_a_prerequisite_of_a_ci_target_counts(tmp_path: Path) -> None:
    """`make validate` pulling in engine-guards is a real invocation, one hop down."""
    result = guarded(
        tmp_path, {"path": GUARD_REL, "invoked_by_ci": "true"},
        makefile=f"validate: lint engine-guards\n\ttrue\n\nengine-guards:\n\tnode {GUARD_REL}\n",
        workflow="name: ci\njobs:\n  d:\n    steps:\n      - run: make validate\n",
    )
    assert result.returncode == 0, result.stderr


def test_a_sibling_apps_guard_is_not_evidence_for_this_one(tmp_path: Path) -> None:
    """Both apps ship a file called check-engine-version.mjs.

    A basename match would report lifecycle-warden's invocation as proof that
    hellgraph-service's guard runs — which is the precise confusion that let a second
    stale copy of the same tarball sit unnoticed through five releases.
    """
    result = guarded(
        tmp_path, {"path": GUARD_REL, "invoked_by_ci": "true"},
        makefile="engine-guards:\n\tnode apps/lifecycle-warden/scripts/check-engine-version.mjs\n",
        workflow="name: ci\njobs:\n  d:\n    steps:\n      - run: make engine-guards\n",
    )
    assert result.returncode == 1
    assert "declares guard.invoked_by_ci: true" in result.stderr


def test_a_guard_floor_that_drifted_from_the_file_is_detected(tmp_path: Path) -> None:
    """The register recorded MIN_ENGINE 0.4.40 for weeks after the file moved to 0.4.45."""
    result = guarded(
        tmp_path,
        {"path": GUARD_REL, "floor_constant": "MIN_ENGINE", "floor_value": "0.4.40",
         "invoked_by_ci": "true"},
        floor="0.4.45",
        makefile=f"engine-guards:\n\tnode {GUARD_REL}\n",
        workflow="name: ci\njobs:\n  d:\n    steps:\n      - run: make engine-guards\n",
    )
    assert result.returncode == 1
    assert "guard floor: register records MIN_ENGINE=0.4.40" in result.stderr


def test_a_floor_constant_the_file_does_not_define_is_detected(tmp_path: Path) -> None:
    result = guarded(
        tmp_path,
        {"path": GUARD_REL, "floor_constant": "NOT_A_REAL_CONSTANT", "floor_value": "0.4.45",
         "invoked_by_ci": "true"},
        makefile=f"engine-guards:\n\tnode {GUARD_REL}\n",
        workflow="name: ci\njobs:\n  d:\n    steps:\n      - run: make engine-guards\n",
    )
    assert result.returncode == 1
    assert "which SocioProphet/prophet-platform" in result.stderr
    assert "does not define" in result.stderr


def test_invoked_by_ci_false_while_the_repo_does_invoke_it_is_reported(tmp_path: Path) -> None:
    """Understating is not a build failure, but it is drift and must be visible."""
    result = guarded(
        tmp_path, {"path": GUARD_REL, "invoked_by_ci": "false"},
        makefile=f"engine-guards:\n\tnode {GUARD_REL}\n",
        workflow="name: ci\njobs:\n  d:\n    steps:\n      - run: make engine-guards\n",
    )
    assert result.returncode == 0, result.stderr
    assert "GUARD-UNDERSTATED" in result.stdout


# ── vfp:guardedBy needs a Contract node, not a path string ───────────────────

def test_guards_contract_must_name_a_declared_contract(tmp_path: Path) -> None:
    text = (FIXTURES / "good-minimal.yaml").read_text(encoding="utf-8")
    text = text.replace(
        "    owner: '@mdheller'",
        "    guard:\n      path: null\n      guards_contract: [no-such-contract]\n"
        "    owner: '@mdheller'",
    )
    path = tmp_path / "register.yaml"
    path.write_text(text, encoding="utf-8")
    result = run(path, "--skip-disk")
    assert result.returncode == 1
    assert "guards_contract names 'no-such-contract'" in result.stderr


def test_contract_id_and_id_must_agree(tmp_path: Path) -> None:
    """Both spellings are carried because two readers want different ones.

    This register says `contract_id`; the engine's ingest reads `id`. Carrying both is
    only safe if they cannot silently diverge into two different Contract nodes.
    """
    text = (FIXTURES / "good-minimal.yaml").read_text(encoding="utf-8")
    text = text.replace(
        "    observation_method: fixture",
        "    observation_method: fixture\n"
        "    contracts:\n      - contract_id: enrich-receipt\n        contract_kind: receipt-shape",
    )
    text = text.replace(
        "      - version: '0.4.45'\n        ref: v0.4.45",
        "      - version: '0.4.45'\n        ref: v0.4.45\n"
        "        changes_contract:\n"
        "          - contract_id: enrich-receipt\n            id: cypher-projection\n"
        "            kind: receipt-shape",
    )
    path = tmp_path / "register.yaml"
    path.write_text(text, encoding="utf-8")
    result = run(path, "--skip-disk")
    assert result.returncode == 1
    assert "they name the same Contract node and must agree" in result.stderr


def test_every_scenario_fixture_is_exercised() -> None:
    """Same rule as the bad-/good- vectors: a fixture nobody runs proves nothing."""
    on_disk = {p.name for p in FIXTURES.glob("scenario-*.yaml")}
    used = set(Path("tests/test_vendor_freshness_detector.py").read_text(encoding="utf-8").split())
    unexercised = {name for name in on_disk if not any(name in token for token in used)}
    assert not unexercised, f"unexercised scenario fixtures: {sorted(unexercised)}"


def test_the_scenario_fixture_is_itself_a_valid_register() -> None:
    """A fixture the validator would reject cannot be evidence about the validator."""
    result = run(FIXTURES / "scenario-engine-behind.yaml", "--skip-disk")
    assert result.returncode == 0, result.stderr
