#!/usr/bin/env python3
"""Cross-repo readiness check for the synthetic Exodus Migration Workroom demo.

This script is intentionally local and offline by default. It checks the known
artifact paths across the three repositories and can optionally run each repo's
validator commands.

Default checkout layout:

- ~/dev/exodus
- ~/dev/prophet-workspace
- ~/dev/sociosphere

No provider credentials are requested or used. No provider APIs are called.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path.home() / "dev"

EXPECTED = {
    "exodus": {
        "default_path": DEFAULT_ROOT / "exodus",
        "artifacts": [
            "schemas/exodus-run.v0.schema.json",
            "examples/synthetic-tenant-a/exodus-run.json",
            "scripts/validate_exodus_demo.py",
            ".github/workflows/ci.yml",
            "docs/synthetic-workroom-demo.md",
        ],
        "validators": [["python3", "scripts/validate_exodus_demo.py"]],
    },
    "prophet_workspace": {
        "default_path": DEFAULT_ROOT / "prophet-workspace",
        "artifacts": [
            "contracts/workspace/exodus-workroom-bridge.schema.json",
            "contracts/workspace/exodus-workroom-bridge.v0.1.example.json",
            "contracts/workspace/exodus-migration-workroom.v0.1.example.json",
            "tools/validate_professional_workrooms.py",
            "docs/exodus-migration-workroom.md",
        ],
        "validators": [["python3", "tools/validate_professional_workrooms.py"]],
    },
    "sociosphere": {
        "default_path": DEFAULT_ROOT / "sociosphere",
        "artifacts": [
            "reports/exodus-workroom-demo.integration-v0.md",
            "reports/exodus-workroom-demo.integration-v0.json",
            "docs/workspace-session-resume.md",
            "reports/workspace-control-plane-context-integration.md",
            "reports/workspace-disposition-summary.baseline.json",
            "manifest/workspace.dispositions.json",
            "reports/workspace-manifest-cleanup.readiness-v0.md",
            "reports/workspace-manifest-cleanup.readiness-v0.json",
            "tools/validate_workspace_dispositions.py",
            "tools/report_workspace_disposition_summary.py",
        ],
        "validators": [
            ["python3", "tools/validate_workspace_dispositions.py"],
            ["python3", "tools/report_workspace_disposition_summary.py"],
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check synthetic Exodus Migration Workroom demo readiness")
    parser.add_argument("--exodus", type=Path, default=EXPECTED["exodus"]["default_path"], help="Path to local exodus checkout")
    parser.add_argument("--prophet-workspace", type=Path, default=EXPECTED["prophet_workspace"]["default_path"], help="Path to local prophet-workspace checkout")
    parser.add_argument("--sociosphere", type=Path, default=EXPECTED["sociosphere"]["default_path"], help="Path to local sociosphere checkout")
    parser.add_argument("--run-validators", action="store_true", help="Run repo-local validator commands after artifact checks")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    return parser.parse_args()


def check_repo(name: str, path: Path, run_validators: bool) -> dict[str, Any]:
    spec = EXPECTED[name]
    path = path.expanduser().resolve()
    missing: list[str] = []
    present: list[str] = []
    for artifact in spec["artifacts"]:
        target = path / artifact
        if target.exists():
            present.append(artifact)
        else:
            missing.append(artifact)

    validator_results: list[dict[str, Any]] = []
    if run_validators and not missing and path.exists():
        for command in spec["validators"]:
            try:
                completed = subprocess.run(
                    command,
                    cwd=path,
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=120,
                )
            except Exception as exc:
                validator_results.append({
                    "command": command,
                    "status": "error",
                    "error": str(exc),
                })
                continue
            validator_results.append({
                "command": command,
                "status": "passed" if completed.returncode == 0 else "failed",
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-2000:],
                "stderr_tail": completed.stderr[-2000:],
            })

    return {
        "repo_key": name,
        "path": str(path),
        "path_exists": path.exists(),
        "artifact_count": len(spec["artifacts"]),
        "present_count": len(present),
        "missing_count": len(missing),
        "present": present,
        "missing": missing,
        "validators": validator_results,
        "status": "ready" if path.exists() and not missing and all(v.get("status") == "passed" for v in validator_results) else "not_ready",
    }


def main() -> int:
    args = parse_args()
    results = {
        "exodus": check_repo("exodus", args.exodus, args.run_validators),
        "prophet_workspace": check_repo("prophet_workspace", args.prophet_workspace, args.run_validators),
        "sociosphere": check_repo("sociosphere", args.sociosphere, args.run_validators),
    }
    ready = all(item["status"] == "ready" for item in results.values())
    report = {
        "schema_version": "sociosphere.exodus-workroom-demo-readiness.v0",
        "source_issue": "SocioProphet/sociosphere#478",
        "mode": "validators_enabled" if args.run_validators else "artifact_presence_only",
        "demo_boundary": "synthetic_offline_no_provider_credentials_no_provider_api_calls_no_provider_side_writes",
        "repo_results": results,
        "readiness_status": "ready" if ready else "not_ready",
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
        print()
        print(f"Exodus Migration Workroom demo readiness: {report['readiness_status']}")
        if not ready:
            print("Missing artifacts or failed validators remain. See JSON above.")
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
