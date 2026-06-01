from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registry" / "computational-artifacts.yaml"

_spec = importlib.util.spec_from_file_location(
    "validate_computational_artifacts",
    ROOT / "tools" / "validate_computational_artifacts.py",
)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

_runner_spec = importlib.util.spec_from_file_location(
    "artifact_health_report",
    ROOT / "tools" / "runner" / "artifact_health_report.py",
)
_runner = importlib.util.module_from_spec(_runner_spec)  # type: ignore[arg-type]
if "artifact_health_report" not in sys.modules:
    sys.modules["artifact_health_report"] = _runner
_runner_spec.loader.exec_module(_runner)  # type: ignore[union-attr]


def test_validate_computational_artifacts_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_computational_artifacts.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "OK:" in result.stdout


try:
    import yaml as _yaml

    _REGISTRY_DATA = _yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    _YAML_AVAILABLE = True
except ImportError:
    _REGISTRY_DATA = {}
    _YAML_AVAILABLE = False


def test_registry_has_required_health_states() -> None:
    if not _YAML_AVAILABLE:
        return
    states = set(_REGISTRY_DATA["spec"]["healthModel"]["freshnessStates"])
    for expected in ("fresh", "stale", "drifted", "blocked", "deprecated"):
        assert expected in states, f"missing health state: {expected}"


def test_registry_has_required_propagation_triggers() -> None:
    if not _YAML_AVAILABLE:
        return
    triggers = {r["when"] for r in _REGISTRY_DATA["spec"]["propagationRules"]}
    for expected in (
        "artifactContractChanged",
        "runtimeProfileChanged",
        "policyChanged",
        "evidenceChanged",
        "safetyClassPrivileged",
        "safetyClassProhibited",
    ):
        assert expected in triggers, f"missing propagation trigger: {expected}"


def test_registry_privileged_prohibited_block_auto_promotion() -> None:
    if not _YAML_AVAILABLE:
        return
    for rule in _REGISTRY_DATA["spec"]["propagationRules"]:
        if rule["when"] in ("safetyClassPrivileged", "safetyClassProhibited"):
            assert rule.get("blockAutoPromotion") is True, (
                f"{rule['when']} must have blockAutoPromotion: true"
            )
            assert rule.get("requireHumanReview") is True, (
                f"{rule['when']} must have requireHumanReview: true"
            )


def test_registry_has_slash_topic_governance() -> None:
    if not _YAML_AVAILABLE:
        return
    governance = _REGISTRY_DATA["spec"]["governance"]
    binding = governance["slashTopicBinding"]
    assert isinstance(binding["namespace"], str)
    assert len(binding["topics"]) > 0
    assert isinstance(binding["governingRepo"], str)


def test_registry_entries_have_required_fields() -> None:
    if not _YAML_AVAILABLE:
        return
    required = {"id", "ownerRepo", "runtimeProfile", "safetyClass", "downstreamConsumers", "requiredEvidence"}
    for entry in _REGISTRY_DATA["spec"]["registryEntries"]:
        for field in required:
            assert field in entry, f"entry '{entry.get('id')}' missing field: {field}"


def test_artifact_health_state_seed_is_stale() -> None:
    entry = {"id": "test.entry", "safetyClass": "bounded", "status": "seed"}
    assert _runner._artifact_health_state(entry) == "stale"


def test_artifact_health_state_prohibited_is_blocked() -> None:
    entry = {"id": "test.entry", "safetyClass": "prohibited", "status": "fresh"}
    assert _runner._artifact_health_state(entry) == "blocked"


def test_artifact_health_state_deprecated() -> None:
    entry = {"id": "test.entry", "safetyClass": "bounded", "status": "deprecated"}
    assert _runner._artifact_health_state(entry) == "deprecated"


def test_artifact_health_state_fresh() -> None:
    entry = {"id": "test.entry", "safetyClass": "advisory", "status": "fresh"}
    assert _runner._artifact_health_state(entry) == "fresh"


def test_artifact_health_report_payload_structure() -> None:
    if not _YAML_AVAILABLE:
        return
    registry = _REGISTRY_DATA
    payload = _runner.artifact_health_report_payload(registry)
    assert payload["kind"] == "ComputationalArtifactHealthReport"
    assert "generatedAt" in payload
    assert "artifacts" in payload
    assert isinstance(payload["artifacts"], list)
    assert len(payload["artifacts"]) > 0
    first = payload["artifacts"][0]
    for field in (
        "id",
        "ownerRepo",
        "runtimeProfile",
        "safetyClass",
        "evidenceStatus",
        "downstreamConsumers",
        "healthState",
        "autoPromotionBlocked",
    ):
        assert field in first, f"artifact health report missing field: {field}"


def test_artifact_health_report_runner_command() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "runner" / "artifact_health_report.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    assert report["kind"] == "ComputationalArtifactHealthReport"
    assert len(report["artifacts"]) > 0
