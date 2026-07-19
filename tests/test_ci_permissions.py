from __future__ import annotations

import json
import subprocess
from pathlib import Path


POLICY = {
    "schema_version": "sociosphere.angel-ci-permissions-policy/v0.1",
    "name": "test policy",
    "default_result_when_warnings_only": "warn",
    "required_workflow_permissions_block": True,
    "required_job_permissions_block": False,
    "deny_permissions_shorthand": ["write-all"],
    "allowed_write_scopes": ["contents", "pull-requests"],
    "workflow_write_exceptions": [
        {
            "path": ".github/workflows/pr.yml",
            "scope": "pull-requests",
            "reason": "test exception",
        }
    ],
    "blocked_write_scopes_without_exception": ["contents"],
    "warn_on_unpinned_actions": True,
    "trusted_local_action_prefixes": ["./"],
}


def write_policy(repo: Path) -> Path:
    policy = repo / "policy.json"
    policy.write_text(json.dumps(POLICY), "utf-8")
    return policy


def run_checker(repo: Path, policy: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            "tools/check_ci_permissions.py",
            "--root",
            str(repo),
            "--policy",
            str(policy),
            "--json-out",
            "-",
        ],
        cwd=Path.cwd(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_ci_permissions_blocks_missing_top_level_permissions(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    policy = write_policy(repo)
    workflows.joinpath("bad.yml").write_text(
        "name: bad\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n",
        "utf-8",
    )

    cp = run_checker(repo, policy)

    assert cp.returncode == 2
    report = json.loads(cp.stdout)
    assert report["result"] == "fail"
    assert any(f["id"] == "ci-missing-workflow-permissions" for f in report["findings"])


def test_ci_permissions_allows_exception_but_warns_on_unpinned_action(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    policy = write_policy(repo)
    workflows.joinpath("pr.yml").write_text(
        "name: pr\non: workflow_dispatch\npermissions:\n  contents: read\n  pull-requests: write\njobs:\n  create:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n",
        "utf-8",
    )

    cp = run_checker(repo, policy)

    assert cp.returncode == 0
    report = json.loads(cp.stdout)
    assert report["result"] == "warn"
    assert any(f["id"] == "ci-action-not-immutable" for f in report["findings"])
    assert not any(f["id"] == "ci-blocked-write-scope" for f in report["findings"])


def test_ci_permissions_blocks_unexcepted_contents_write(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    policy = write_policy(repo)
    workflows.joinpath("write.yml").write_text(
        "name: write\non: [push]\npermissions:\n  contents: write\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo ok\n",
        "utf-8",
    )

    cp = run_checker(repo, policy)

    assert cp.returncode == 2
    report = json.loads(cp.stdout)
    assert report["result"] == "fail"
    assert any(f["id"] == "ci-blocked-write-scope" for f in report["findings"])
