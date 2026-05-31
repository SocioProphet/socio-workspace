#!/usr/bin/env python3
"""Generate or validate a live-ref resolved workspace lock.

Default behavior is offline and deterministic when `--fixture-map` is supplied.
Live GitHub resolution is available only with `--live`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest" / "workspace.toml"
DECLARED_LOCK = ROOT / "manifest" / "workspace.lock.json"
RESOLVED_LOCK = ROOT / "manifest" / "workspace.resolved.lock.json"

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ENTRY_RE = re.compile(r"^\s*\[\[repos\]\]\s*$")
KV_RE = re.compile(r"^\s*([A-Za-z0-9_\-]+)\s*=\s*(.+?)\s*(?:#.*)?$")
ARRAY_KEYS = {"required_capabilities", "required_grants"}
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
        if key in SCALAR_KEYS:
            current[key] = parse_scalar(raw)

    if pending_array_key:
        raise ValueError(f"unterminated array for {pending_array_key}")
    if current is not None:
        repos.append(current)
    return repos


def validate_repo_names(repos: list[dict[str, Any]]) -> None:
    names = [repo.get("name") for repo in repos]
    missing = [str(index) for index, name in enumerate(names) if not name]
    if missing:
        raise ValueError("repo entries missing name at indexes: " + ", ".join(missing))
    dupes = sorted({str(name) for name in names if names.count(name) > 1})
    if dupes:
        raise ValueError("duplicate repo names: " + ", ".join(dupes))


def normalize_repo_url(url: str) -> str:
    return url[:-4] if url.endswith(".git") else url.rstrip("/")


def load_fixture_map(path: Path) -> dict[str, dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("fixture map root must be object")
    normalized: dict[str, dict[str, str]] = {}
    for url, refs in data.items():
        if not isinstance(refs, dict):
            raise ValueError(f"fixture refs for {url} must be object")
        normalized[normalize_repo_url(url)] = {str(ref): str(sha) for ref, sha in refs.items()}
    return normalized


def resolve_from_fixture(repo: dict[str, Any], fixture_map: dict[str, dict[str, str]]) -> tuple[str | None, str | None]:
    url = normalize_repo_url(str(repo.get("url", "")))
    ref = repo.get("ref")
    if not url or not ref:
        return None, "missing url or ref"
    sha = fixture_map.get(url, {}).get(str(ref))
    if not sha:
        return None, f"fixture missing ref {url}@{ref}"
    if not SHA_RE.match(sha):
        return None, f"fixture ref {url}@{ref} is not 40-char sha"
    return sha, None


def github_api_url(repo_url: str, ref: str) -> str | None:
    url = normalize_repo_url(repo_url)
    prefix = "https://github.com/"
    if not url.startswith(prefix):
        return None
    owner_repo = url[len(prefix):]
    if owner_repo.count("/") != 1:
        return None
    return f"https://api.github.com/repos/{owner_repo}/commits/{ref}"


def resolve_live(repo: dict[str, Any]) -> tuple[str | None, str | None]:
    url = repo.get("url")
    ref = repo.get("ref")
    if not url or not ref:
        return None, "missing url or ref"
    api_url = github_api_url(str(url), str(ref))
    if not api_url:
        return None, "unsupported non-github url"
    request = Request(api_url, headers={"Accept": "application/vnd.github+json", "User-Agent": "sociosphere-lock-resolver"})
    try:
        with urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        return None, f"github http error {exc.code}"
    except URLError as exc:
        return None, f"github url error {exc.reason}"
    except Exception as exc:
        return None, f"github resolve error {exc}"
    sha = data.get("sha")
    if not isinstance(sha, str) or not SHA_RE.match(sha):
        return None, "github response missing 40-char sha"
    return sha, None


def build_repo_record(repo: dict[str, Any], resolved_rev: str | None, status: str, error: str | None) -> dict[str, Any]:
    return {
        "name": repo.get("name"),
        "role": repo.get("role"),
        "url": repo.get("url"),
        "local_path": repo.get("local_path"),
        "declared_ref": repo.get("ref"),
        "declared_rev": repo.get("rev"),
        "resolved_rev": resolved_rev,
        "resolution_status": status,
        "resolution_error": error,
        "trust_zone": repo.get("trust_zone"),
        "trust_profile_ref": repo.get("trust_profile_ref"),
        "license_hint": repo.get("license_hint"),
        "required_capabilities": repo.get("required_capabilities", []),
        "required_grants": repo.get("required_grants", []),
    }


def resolve_repo(repo: dict[str, Any], *, live: bool, fixture_map: dict[str, dict[str, str]] | None) -> dict[str, Any]:
    declared_rev = repo.get("rev")
    declared_ref = repo.get("ref")
    if declared_rev:
        if not SHA_RE.match(str(declared_rev)):
            return build_repo_record(repo, None, "unresolved", "declared_rev is not 40-char sha")
        if declared_ref and (live or fixture_map):
            resolved, error = resolve_live(repo) if live else resolve_from_fixture(repo, fixture_map or {})
            if error:
                return build_repo_record(repo, str(declared_rev), "pinned", None)
            if resolved != declared_rev:
                return build_repo_record(repo, resolved, "drift", f"declared rev {declared_rev} differs from ref resolution")
        return build_repo_record(repo, str(declared_rev), "pinned", None)
    if not declared_ref:
        return build_repo_record(repo, None, "skipped", "repo has no ref or rev")
    if live:
        resolved, error = resolve_live(repo)
    elif fixture_map is not None:
        resolved, error = resolve_from_fixture(repo, fixture_map)
    else:
        return build_repo_record(repo, None, "skipped", "no live or fixture resolver selected")
    if error:
        return build_repo_record(repo, None, "unresolved", error)
    return build_repo_record(repo, resolved, "resolved", None)


def build_lock(repos: list[dict[str, Any]], *, live: bool, fixture_map: dict[str, dict[str, str]] | None) -> dict[str, Any]:
    records = [resolve_repo(repo, live=live, fixture_map=fixture_map) for repo in repos]
    records.sort(key=lambda item: str(item.get("name", "")))
    return {
        "schema_version": "sociosphere.workspace-resolved-lock.v0",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source_manifest": "manifest/workspace.toml",
        "source_lock": "manifest/workspace.lock.json",
        "resolution_mode": "live_ref_resolution",
        "repo_count": len(records),
        "repos": records,
    }


def check_lock(expected: dict[str, Any], allow_drift: bool) -> int:
    if not RESOLVED_LOCK.exists():
        print("ERR: manifest/workspace.resolved.lock.json is missing", file=sys.stderr)
        return 2
    current = json.loads(RESOLVED_LOCK.read_text(encoding="utf-8"))
    expected_cmp = dict(expected)
    expected_cmp["generated_at"] = current.get("generated_at")
    if current != expected_cmp:
        if allow_drift:
            print("DRIFT: manifest/workspace.resolved.lock.json differs from current resolution")
            return 0
        print("ERR: manifest/workspace.resolved.lock.json is stale", file=sys.stderr)
        return 2
    print("OK: manifest/workspace.resolved.lock.json matches current resolution")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="resolve refs through GitHub API")
    parser.add_argument("--fixture-map", type=Path, help="offline url/ref to sha resolver map")
    parser.add_argument("--write", action="store_true", help="write manifest/workspace.resolved.lock.json")
    parser.add_argument("--check", action="store_true", help="check manifest/workspace.resolved.lock.json")
    parser.add_argument("--allow-drift", action="store_true", help="report drift without failing during --check")
    parser.add_argument("--require-all-resolved", action="store_true", help="fail if any repo is unresolved, drift, or skipped")
    parser.add_argument("--accept-subset", action="store_true", help="allow fixture maps that resolve only a subset of repos")
    args = parser.parse_args(argv)

    if args.live and args.fixture_map:
        print("ERR: choose either --live or --fixture-map, not both", file=sys.stderr)
        return 2
    if not args.live and not args.fixture_map:
        print("ERR: choose --live or --fixture-map", file=sys.stderr)
        return 2

    try:
        repos = parse_manifest(MANIFEST)
        validate_repo_names(repos)
        fixture_map = load_fixture_map(args.fixture_map) if args.fixture_map else None
        lock = build_lock(repos, live=args.live, fixture_map=fixture_map)
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 2

    bad = [repo for repo in lock["repos"] if repo["resolution_status"] in {"unresolved", "drift"} or (repo["resolution_status"] == "skipped" and args.require_all_resolved)]
    if bad and args.require_all_resolved:
        for repo in bad:
            print(f"ERR: {repo['name']}: {repo['resolution_status']}: {repo.get('resolution_error')}", file=sys.stderr)
        return 2

    if args.write:
        RESOLVED_LOCK.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"OK: wrote {RESOLVED_LOCK.relative_to(ROOT)} with {len(lock['repos'])} repos")
        return 0
    if args.check:
        return check_lock(lock, args.allow_drift)
    print(json.dumps(lock, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
