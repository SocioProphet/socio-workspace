#!/usr/bin/env python3
from pathlib import Path
import re
import sys

MATRIX = Path("registry/repo-governance-matrix-v0.yaml")
VALID_CLASSES = {"canonical", "promotion_candidate", "provenance_only", "archive_retire"}
REQUIRED_AUTHORITY_FIELDS = {"contracts", "runtime_behavior", "standards", "evidence_state"}
REQUIRES_RESTRICTION = {"provenance_only", "archive_retire"}


def fail(message: str) -> int:
    print(f"repo-governance-matrix: ERROR: {message}", file=sys.stderr)
    return 1


def parse_repos(text: str) -> list[dict[str, object]]:
    repos = []
    current = None
    in_authority = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("- name: "):
            if current is not None:
                repos.append(current)
            current = {"name": stripped.removeprefix("- name: ").strip(), "authority": {}}
            in_authority = False
            continue
        if current is None or not stripped or stripped.startswith("#"):
            continue
        if stripped == "authority:":
            in_authority = True
            continue
        if re.match(r"^[A-Za-z_]+:", stripped):
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip()
            if in_authority and key in REQUIRED_AUTHORITY_FIELDS:
                current["authority"][key] = value
            elif key in {"class", "function", "promotion_condition", "risk", "restriction"}:
                current[key] = value
                in_authority = False
    if current is not None:
        repos.append(current)
    return repos


def main() -> int:
    if not MATRIX.exists():
        return fail(f"missing {MATRIX}")
    repos = parse_repos(MATRIX.read_text(encoding="utf-8"))
    if not repos:
        return fail("no repository entries found")
    seen = set()
    classes = set()
    for repo in repos:
        name = str(repo.get("name", "")).strip()
        klass = str(repo.get("class", "")).strip()
        if not name:
            return fail("repository entry without name")
        if name in seen:
            return fail(f"duplicate repository entry: {name}")
        seen.add(name)
        if klass not in VALID_CLASSES:
            return fail(f"{name} has invalid class {klass!r}")
        classes.add(klass)
        if not str(repo.get("function", "")).strip():
            return fail(f"{name} missing function")
        if klass == "canonical":
            missing = REQUIRED_AUTHORITY_FIELDS - set(repo.get("authority", {}))
            if missing:
                return fail(f"{name} missing authority fields: {', '.join(sorted(missing))}")
        if klass == "promotion_candidate":
            if not str(repo.get("promotion_condition", "")).strip():
                return fail(f"{name} missing promotion_condition")
            if not str(repo.get("risk", "")).strip():
                return fail(f"{name} missing risk")
        if klass in REQUIRES_RESTRICTION and not str(repo.get("restriction", "")).strip():
            return fail(f"{name} missing restriction")
    missing_classes = VALID_CLASSES - classes
    if missing_classes:
        return fail(f"missing governance classes: {', '.join(sorted(missing_classes))}")
    print(f"repo-governance-matrix: OK ({len(repos)} repositories)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
