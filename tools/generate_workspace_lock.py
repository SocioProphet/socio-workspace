#!/usr/bin/env python3
"""Generate a deterministic lock file from manifest/workspace.toml.

The lock intentionally records manifest-declared repository metadata only. It
does not resolve remote refs to live commit SHAs; remote resolution should be a
separate, network-aware lock stage when the workspace materializer owns that
behavior.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest" / "workspace.toml"
LOCK = ROOT / "manifest" / "workspace.lock.json"

ENTRY_RE = re.compile(r"^\s*\[\[repos\]\]\s*$")
KV_RE = re.compile(r"^\s*([A-Za-z0-9_\-]+)\s*=\s*(.+?)\s*(?:#.*)?$")

SCALAR_KEYS = {
    "name",
    "role",
    "url",
    "ref",
    "rev",
    "local_path",
    "license_hint",
    "trust_zone",
    "trust_profile_ref",
}
ARRAY_KEYS = {"required_capabilities", "required_grants"}


def parse_scalar(raw: str) -> str | None:
    raw = raw.strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw in {"true", "false"}:
        return raw
    if raw.startswith("{") and raw.endswith("}"):
        return raw
    return raw if raw else None


def parse_array(raw: str) -> list[str] | None:
    raw = raw.strip()
    if not (raw.startswith("[") and raw.endswith("]")):
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    return [str(item) for item in parsed]


def parse_manifest(path: Path) -> list[dict[str, Any]]:
    repos: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    pending_array_key: str | None = None
    pending_array_values: list[str] = []

    def flush_pending_array() -> None:
        nonlocal pending_array_key, pending_array_values, current
        if pending_array_key and current is not None:
            current[pending_array_key] = pending_array_values
        pending_array_key = None
        pending_array_values = []

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if pending_array_key:
            if stripped.startswith("]"):
                flush_pending_array()
                continue
            value = stripped.rstrip(",").strip()
            if value.startswith('"') and value.endswith('"'):
                pending_array_values.append(value[1:-1])
            continue

        if ENTRY_RE.match(line):
            if current is not None:
                repos.append(current)
            current = {}
            continue

        if current is None:
            continue

        match = KV_RE.match(line)
        if not match:
            continue
        key, raw = match.groups()
        raw = raw.strip()

        if key in ARRAY_KEYS:
            parsed_array = parse_array(raw)
            if parsed_array is not None:
                current[key] = parsed_array
            elif raw == "[":
                pending_array_key = key
                pending_array_values = []
            continue

        if key in SCALAR_KEYS or key == "entry":
            current[key] = parse_scalar(raw)

    if pending_array_key:
        raise ValueError(f"unterminated array for {pending_array_key}")
    if current is not None:
        repos.append(current)

    return repos


def validate_repos(repos: list[dict[str, Any]]) -> None:
    names = [repo.get("name") for repo in repos]
    missing_name = [index for index, name in enumerate(names) if not name]
    if missing_name:
        raise ValueError("repo entries missing name at indexes: " + ", ".join(map(str, missing_name)))
    dupes = sorted({str(name) for name in names if names.count(name) > 1})
    if dupes:
        raise ValueError("duplicate repo names: " + ", ".join(dupes))


def build_lock(repos: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = []
    for repo in sorted(repos, key=lambda item: str(item.get("name", ""))):
        normalized.append({key: repo[key] for key in sorted(repo)})

    return {
        "schema_version": "sociosphere.workspace-lock.v0.1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_manifest": "manifest/workspace.toml",
        "resolution_mode": "manifest_declared_refs_only",
        "repo_count": len(normalized),
        "repos": normalized,
    }


def write_lock(lock: dict[str, Any]) -> None:
    LOCK.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write manifest/workspace.lock.json")
    parser.add_argument("--check", action="store_true", help="check current lock matches manifest except generated_at")
    args = parser.parse_args(argv)

    try:
        repos = parse_manifest(MANIFEST)
        validate_repos(repos)
        lock = build_lock(repos)
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 2

    if args.write:
        write_lock(lock)
        print(f"OK: wrote {LOCK.relative_to(ROOT)} with {len(repos)} repos")
        return 0

    if args.check:
        if not LOCK.exists():
            print("ERR: manifest/workspace.lock.json is missing", file=sys.stderr)
            return 2
        current = json.loads(LOCK.read_text(encoding="utf-8"))
        expected = dict(lock)
        expected["generated_at"] = current.get("generated_at")
        if current != expected:
            print("ERR: manifest/workspace.lock.json is stale", file=sys.stderr)
            return 2
        print("OK: manifest/workspace.lock.json matches manifest/workspace.toml")
        return 0

    print(json.dumps(lock, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
