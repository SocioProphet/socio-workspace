#!/usr/bin/env python3
"""Summarize workspace disposition metadata.

Offline reporter. It reads manifest/workspace.dispositions.json and emits a
compact status summary for governance review. It does not mutate the workspace
manifest or resolve any network refs.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DISPOSITIONS_PATH = ROOT / "manifest" / "workspace.dispositions.json"


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} root must be a JSON object")
    return data


def build_summary() -> dict[str, Any]:
    data = load_json(DISPOSITIONS_PATH)
    dispositions = data.get("dispositions")
    if not isinstance(dispositions, list):
        raise ValueError("dispositions must be a list")

    by_status: dict[str, list[str]] = defaultdict(list)
    by_action: dict[str, list[str]] = defaultdict(list)
    by_issue: dict[str, list[str]] = defaultdict(list)
    candidate_successors: dict[str, Any] = {}

    for index, entry in enumerate(dispositions):
        if not isinstance(entry, dict):
            raise ValueError(f"disposition entry {index} must be object")
        name = entry.get("name")
        status = entry.get("status")
        action = entry.get("current_action")
        source_issue = entry.get("source_issue")
        if not isinstance(name, str) or not name:
            raise ValueError(f"disposition entry {index} missing name")
        if not isinstance(status, str) or not status:
            raise ValueError(f"{name}: missing status")
        if not isinstance(action, str) or not action:
            raise ValueError(f"{name}: missing current_action")
        if not isinstance(source_issue, int):
            raise ValueError(f"{name}: source_issue must be integer")

        by_status[status].append(name)
        by_action[action].append(name)
        by_issue[str(source_issue)].append(name)
        if "candidate_successor" in entry:
            candidate_successors[name] = entry["candidate_successor"]
        if "candidate_successors" in entry:
            candidate_successors[name] = entry["candidate_successors"]

    def counts(mapping: dict[str, list[str]]) -> dict[str, int]:
        return {key: len(values) for key, values in sorted(mapping.items())}

    return {
        "schema_version": "sociosphere.workspace-disposition-summary.v0",
        "source": "manifest/workspace.dispositions.json",
        "source_schema_version": data.get("schema_version"),
        "source_issue": data.get("source_issue"),
        "disposition_count": len(dispositions),
        "status_counts": counts(by_status),
        "action_counts": counts(by_action),
        "source_issue_counts": counts(by_issue),
        "by_status": {key: sorted(values) for key, values in sorted(by_status.items())},
        "candidate_successors": candidate_successors,
        "summary_status": "metadata_only_no_manifest_mutation",
    }


def main() -> int:
    try:
        summary = build_summary()
    except Exception as exc:
        print(f"ERR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
