#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "registry" / "corpus-loop-v1" / "valid.watson-cyc-chronos.pinned.json"
REPORT = ROOT / "reports" / "corpus-loop-v1-resolution-report.json"
REQUIRED = {"evidence", "ontology", "policy", "runtime", "ledger"}


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be object")
    return data


def raw_url(repo: str, sha: str, path: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"


def probe(url: str, timeout: int) -> str:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if 200 <= response.status < 300:
                return "found"
            return "unresolved"
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "missing"
        return "unresolved"
    except Exception:
        return "unresolved"


def build_report(manifest: dict[str, Any], *, live: bool, timeout: int) -> dict[str, Any]:
    components = []
    for component in manifest["components"]:
        artifacts = []
        for artifact_path in component["artifact_refs"]:
            url = raw_url(component["repo"], component["pinned_commit"], artifact_path)
            artifacts.append(
                {
                    "path": artifact_path,
                    "url": url,
                    "status": probe(url, timeout) if live else "unresolved",
                }
            )
        component_statuses = {artifact["status"] for artifact in artifacts}
        if component_statuses == {"found"}:
            status = "found"
        elif "missing" in component_statuses:
            status = "missing"
        else:
            status = "unresolved"
        components.append(
            {
                "plane": component["plane"],
                "repo": component["repo"],
                "merged_ref": component["merged_ref"],
                "pinned_commit": component["pinned_commit"],
                "status": status,
                "artifacts": artifacts,
            }
        )
    return {
        "schema_version": "0.1",
        "kind": "corpus_loop_v1_resolution_report",
        "loop_id": manifest["loop_id"],
        "source_corpus": manifest["source_corpus"],
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "resolution_mode": "live_github_raw" if live else "declared_unresolved",
        "components": components,
        "boundary": {
            "sociosphere_owns_coordination": True,
            "sociosphere_owns_downstream_implementation": False,
        },
    }


def check_report(manifest: dict[str, Any], report: dict[str, Any], *, require_found: bool) -> None:
    if report.get("loop_id") != manifest["loop_id"]:
        raise ValueError("loop_id mismatch")
    by_plane = {item["plane"]: item for item in manifest["components"]}
    report_by_plane = {item["plane"]: item for item in report.get("components", [])}
    if set(report_by_plane) != REQUIRED:
        raise ValueError("required planes missing from report")
    for plane, component in by_plane.items():
        reported = report_by_plane[plane]
        if reported["repo"] != component["repo"]:
            raise ValueError(f"repo mismatch for {plane}")
        if reported["pinned_commit"] != component["pinned_commit"]:
            raise ValueError(f"pin mismatch for {plane}")
        reported_paths = {artifact["path"] for artifact in reported.get("artifacts", [])}
        if reported_paths != set(component["artifact_refs"]):
            raise ValueError(f"artifact refs mismatch for {plane}")
        for artifact in reported.get("artifacts", []):
            if artifact["status"] not in {"found", "missing", "unresolved"}:
                raise ValueError(f"invalid status for {plane}: {artifact['status']}")
            if require_found and artifact["status"] != "found":
                raise ValueError(f"required artifact not found for {plane}: {artifact['path']}")
    boundary = report.get("boundary", {})
    if boundary.get("sociosphere_owns_coordination") is not True:
        raise ValueError("coordination boundary missing")
    if boundary.get("sociosphere_owns_downstream_implementation") is not False:
        raise ValueError("downstream ownership boundary mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="probe GitHub raw paths")
    parser.add_argument("--write", action="store_true", help="write the report file")
    parser.add_argument("--require-found", action="store_true", help="fail if any artifact is not found")
    parser.add_argument("--timeout", type=int, default=10)
    args = parser.parse_args()

    manifest = load(MANIFEST)
    if args.write:
        report = build_report(manifest, live=args.live, timeout=args.timeout)
        REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    else:
        report = load(REPORT)
    check_report(manifest, report, require_found=args.require_found)
    print("OK: corpus loop v1 resolution report validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
