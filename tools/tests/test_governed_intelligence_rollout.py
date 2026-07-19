from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registry" / "governed-intelligence-rollout.yaml"


def test_governed_intelligence_rollout_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "validate_governed_intelligence_rollout.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert "OK: validated governed intelligence rollout registry" in result.stdout


def test_governed_intelligence_rollout_status_projection_values() -> None:
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    allowed = set(data["adoption_status_projection"]["allowed_statuses"])
    repos = data["adoption_status_projection"]["repos"]
    repo_names = {item["repo"] for item in repos}
    assert allowed == {
        "not_started",
        "schema_stubbed",
        "adapter_in_progress",
        "contract_tests_present",
        "vertical_slice_ready",
    }
    assert {
        "SocioProphet/sociosphere",
        "SocioProphet/ontogenesis",
        "SocioProphet/holmes",
        "SocioProphet/sherlock-search",
        "SocioProphet/gaia-world-model",
        "SocioProphet/guardrail-fabric",
        "SocioProphet/agentplane",
        "SocioProphet/model-governance-ledger",
        "SocioProphet/slash-topics",
    } <= repo_names
    assert all(item["status"] in allowed for item in repos)
