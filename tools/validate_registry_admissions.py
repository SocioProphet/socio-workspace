#!/usr/bin/env python3
"""Validate registry admission fragments.

This validator keeps staged registry admissions machine-checkable without forcing
large canonical registry rewrites through connector-driven full-file replacement.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
ADMISSIONS = ROOT / "registry" / "admissions"
REQUIRED = {
    "id",
    "name",
    "url",
    "role",
    "status",
    "description",
    "primary_language",
    "tags",
    "canonical_owner",
    "sociosphere_role",
    "claim_boundary",
    "source_ledger",
    "candidate_pin",
}


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path}: root must be a mapping")
    return data


def validate_admission(path: Path) -> None:
    data = load_yaml(path)
    missing = REQUIRED - set(data)
    if missing:
        raise AssertionError(f"{path}: missing required fields: {sorted(missing)}")
    if data["status"] != "active":
        raise AssertionError(f"{path}: status must be active")
    if not str(data["url"]).startswith("https://github.com/"):
        raise AssertionError(f"{path}: url must be a GitHub HTTPS URL")
    tags = data["tags"]
    if not isinstance(tags, list) or not tags:
        raise AssertionError(f"{path}: tags must be a non-empty list")
    if not all(isinstance(tag, str) and tag for tag in tags):
        raise AssertionError(f"{path}: tags must contain only non-empty strings")
    pin = str(data["candidate_pin"])
    if len(pin) != 40 or any(ch not in "0123456789abcdef" for ch in pin):
        raise AssertionError(f"{path}: candidate_pin must be a 40-character lowercase commit SHA")
    source_ledger = ROOT / str(data["source_ledger"])
    if not source_ledger.exists():
        raise AssertionError(f"{path}: source_ledger does not exist: {source_ledger}")
    if data["id"] != data["name"]:
        raise AssertionError(f"{path}: id and name must match for canonical admissions")


def main() -> int:
    files = sorted(ADMISSIONS.glob("*.yaml")) if ADMISSIONS.exists() else []
    if not files:
        print("registry admissions: none")
        return 0
    for path in files:
        validate_admission(path)
    print(f"registry admissions: ok ({len(files)} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
