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


def test_committed_register_reports_the_engine_drift() -> None:
    """Both engine copies must be surfaced as stale, not silently accepted."""
    result = run(Path("registry/vendor-freshness.yaml"), "--skip-disk")
    assert "STALE hellgraph-engine@hellgraph-service" in result.stdout
    assert "STALE hellgraph-engine@lifecycle-warden" in result.stdout
    # the guard that never runs is a declared finding in its own right
    assert "GUARD-NOT-INVOKED hellgraph-engine@lifecycle-warden" in result.stdout


def test_positive_control_passes() -> None:
    result = run(FIXTURES / "good-minimal.yaml", "--skip-disk")
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
