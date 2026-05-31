#!/usr/bin/env python3
"""Repo coverage checker for the SocioSphere service register."""
from __future__ import annotations

import csv
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "architecture" / "service-register"
REGISTER = ARTIFACT_ROOT / "service-architecture-register.v1.0.csv"
CANONICAL_REPOS = ARTIFACT_ROOT / "canonical-repo-estate.v1.0.csv"
EXPECTED_SERVICE_ROWS = 46
EXPECTED_REPO_COUNT = 125
REPO_FIELDS = ("owning_repo", "supporting_repos", "contract_repo")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def split_values(value: str | None) -> list[str]:
    if not value or value == "-":
        return []
    return [part.strip() for part in value.split(",") if part.strip() and part.strip() != "-"]


def repo_key(row: dict[str, str]) -> str:
    return row.get("repo") or row.get("repo_full_name") or row.get("repository") or ""


def warn(message: str) -> None:
    print(f"WARN: {message}")


def fail(message: str) -> None:
    print(f"FAIL: {message}")


def ok(message: str) -> None:
    print(f"OK: {message}")


def main() -> int:
    print("SocioSphere service-register repo coverage check")
    strict = os.environ.get("SERVICE_REGISTER_STRICT", "0") == "1"
    failures = 0

    if not REGISTER.exists():
        message = f"missing {REGISTER.relative_to(ROOT)}; coverage cannot run yet"
        if strict:
            fail(message)
            return 1
        warn(message)
        return 0

    service_rows = read_csv(REGISTER)
    if len(service_rows) == EXPECTED_SERVICE_ROWS:
        ok(f"service rows={len(service_rows)}")
    else:
        message = f"service row count {len(service_rows)} != expected {EXPECTED_SERVICE_ROWS}"
        if strict:
            fail(message)
            failures += 1
        else:
            warn(message)

    mapped_repos: set[str] = set()
    for row in service_rows:
        for field in REPO_FIELDS:
            for value in split_values(row.get(field)):
                if "/" in value and value != "TBD":
                    mapped_repos.add(value)

    if not CANONICAL_REPOS.exists():
        message = f"missing {CANONICAL_REPOS.relative_to(ROOT)}; mapped repo count={len(mapped_repos)}"
        if strict:
            fail(message)
            return 1
        warn(message)
        return 0

    canonical_rows = read_csv(CANONICAL_REPOS)
    canonical_repos = {repo_key(row).strip() for row in canonical_rows if repo_key(row).strip()}
    missing = sorted(canonical_repos - mapped_repos)
    extra = sorted(mapped_repos - canonical_repos)

    if len(canonical_repos) == EXPECTED_REPO_COUNT:
        ok(f"canonical repos={len(canonical_repos)}")
    else:
        message = f"canonical repo count {len(canonical_repos)} != expected {EXPECTED_REPO_COUNT}"
        if strict:
            fail(message)
            failures += 1
        else:
            warn(message)

    if missing:
        message = f"missing coverage for {len(missing)} repos: {missing}"
        if strict:
            fail(message)
            failures += 1
        else:
            warn(message)
    else:
        ok("no missing canonical repo coverage")

    if extra:
        message = f"register references {len(extra)} noncanonical repos: {extra}"
        if strict:
            fail(message)
            failures += 1
        else:
            warn(message)
    else:
        ok("no noncanonical repo references")

    if failures:
        return 1
    print("repo coverage check complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
