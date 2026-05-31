#!/usr/bin/env python3
"""Validate workspace resolved lock contract fixtures."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas/workspace-resolved-lock.v0.schema.json"
VALID = ROOT / "tests/fixtures/workspace-resolved-lock.valid.synthetic.json"
INVALID_DUPLICATE = ROOT / "tests/fixtures/workspace-resolved-lock.duplicate-name.invalid.synthetic.json"
REQUIRED_WCF = {
    "prophet_workspace",
    "agent_registry",
    "memory_mesh",
    "socioprophet_agent_standards",
}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path} root must be object")
    return data


def validate_semantics(data: dict) -> None:
    if data["schema_version"] != "sociosphere.workspace-resolved-lock.v0":
        raise AssertionError("bad schema_version")
    if data["resolution_mode"] != "live_ref_resolution":
        raise AssertionError("bad resolution_mode")
    repos = data["repos"]
    if data["repo_count"] != len(repos):
        raise AssertionError("repo_count mismatch")
    names = [repo["name"] for repo in repos]
    dupes = sorted({name for name in names if names.count(name) > 1})
    if dupes:
        raise AssertionError("duplicate repo names: " + ", ".join(dupes))
    missing_wcf = REQUIRED_WCF - set(names)
    if missing_wcf:
        raise AssertionError("missing Workspace Context Fabric repos: " + ", ".join(sorted(missing_wcf)))
    for repo in repos:
        status = repo["resolution_status"]
        resolved = repo.get("resolved_rev")
        declared = repo.get("declared_rev")
        if status in {"resolved", "pinned"}:
            if not isinstance(resolved, str) or not SHA_RE.match(resolved):
                raise AssertionError(f"{repo['name']}: resolved/pinned repo must have 40-char sha")
        if status == "pinned" and declared != resolved:
            raise AssertionError(f"{repo['name']}: pinned status requires declared_rev == resolved_rev")
        if status in {"unresolved", "drift"} and not repo.get("resolution_error"):
            raise AssertionError(f"{repo['name']}: unresolved/drift requires resolution_error")


def main() -> int:
    try:
        schema = load(SCHEMA)
        if schema.get("title") != "WorkspaceResolvedLockV0":
            raise AssertionError("schema title mismatch")
        validate_semantics(load(VALID))
        try:
            validate_semantics(load(INVALID_DUPLICATE))
        except AssertionError:
            pass
        else:
            raise AssertionError("invalid duplicate-name fixture unexpectedly passed")
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 2
    print("OK: workspace resolved lock contract validates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
