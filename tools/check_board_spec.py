#!/usr/bin/env python3
"""Validate registry/board-spec.yaml — the declarative source of truth for the
estate program boards (GitHub Projects + sovereign render targets).

Without this, the source of truth is an unvalidated blob: a bad edit would only
surface as reconciler/drill drift far downstream. This is the schema gate.
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for check_board_spec.py") from exc

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "registry" / "board-spec.yaml"


def main() -> int:
    if not SPEC_PATH.exists():
        print(f"ERROR: missing {SPEC_PATH}", file=sys.stderr)
        return 1

    data = yaml.safe_load(SPEC_PATH.read_text())
    errors: list[str] = []

    if not isinstance(data, dict):
        print("ERROR: board-spec must be a mapping", file=sys.stderr)
        return 1

    if data.get("version") is None:
        errors.append("top-level 'version' missing")
    if not isinstance(data.get("std_program_fields"), list) or not data["std_program_fields"]:
        errors.append("'std_program_fields' must be a non-empty list")

    boards = data.get("boards")
    if not isinstance(boards, list) or not boards:
        print("ERROR: 'boards' must be a non-empty list", file=sys.stderr)
        return 1

    titles: set[str] = set()
    for i, b in enumerate(boards):
        where = f"board[{i}]"
        if not isinstance(b, dict):
            errors.append(f"{where}: must be a mapping"); continue
        title = b.get("title")
        if not title:
            errors.append(f"{where}: missing 'title'")
        else:
            if title in titles:
                errors.append(f"duplicate board title: {title!r}")
            titles.add(title)
            where = title
        if not b.get("owner_org"):
            errors.append(f"{where}: missing 'owner_org'")
        if not isinstance(b.get("github_number"), int):
            errors.append(f"{where}: 'github_number' must be an int")
        # items are optional (empty boards are legal), but if present must be well-formed
        items = b.get("items")
        if items is not None:
            if not isinstance(items, list):
                errors.append(f"{where}: 'items' must be a list")
            else:
                for it in items:
                    if not isinstance(it, dict) or not it.get("repo") or not isinstance(it.get("issue"), int):
                        errors.append(f"{where}: each item needs a 'repo' (str) and 'issue' (int): {it!r}")

    pb = data.get("portfolio_board")
    if pb is not None and pb not in titles:
        errors.append(f"'portfolio_board' {pb!r} names no board in the spec")

    if errors:
        print(f"FAIL: {len(errors)} problem(s) in board-spec.yaml:\n", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"OK: board-spec.yaml v{data['version']} — {len(boards)} boards, all well-formed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
