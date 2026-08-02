#!/usr/bin/env python3
"""Validate registry/agent-prompt-catalog.yaml — the raw+refined operator-prompt
record with review-flags (produced-too-much-work / reused>3x). Schema gate so
the catalog can't drift into malformed entries."""
from __future__ import annotations
import sys
from pathlib import Path
try:
    import yaml  # type: ignore
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required for check_agent_prompt_catalog.py") from exc

ROOT = Path(__file__).resolve().parents[1]
CAT = ROOT / "registry" / "agent-prompt-catalog.yaml"


def main() -> int:
    if not CAT.exists():
        print(f"ERROR: missing {CAT}", file=sys.stderr); return 1
    d = yaml.safe_load(CAT.read_text())
    errors: list[str] = []
    if not isinstance(d, dict):
        print("ERROR: catalog must be a mapping", file=sys.stderr)
        return 1
    if d.get("kind") != "AgentPromptCatalog":
        errors.append("kind must be AgentPromptCatalog")
    if d.get("version") is None:
        errors.append("missing version")
    prompts = d.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        print("ERROR: 'prompts' must be a non-empty list", file=sys.stderr)
        return 1
    # 'domains' must be a list — a bare string would set()-split into characters.
    raw_domains = d.get("domains")
    if raw_domains is not None and not isinstance(raw_domains, list):
        errors.append("'domains' must be a list")
        raw_domains = []
    domains = set(raw_domains or [])
    _WORK = {"light", "medium", "high", "very-high"}
    _SPEC = {"low", "medium", "high"}
    ids: set = set()
    for p in prompts:
        if not isinstance(p, dict):
            errors.append(f"prompt entry not a mapping: {p!r}")
            continue
        pid = p.get("id")
        where = f"prompt#{pid}"
        if pid is None:
            errors.append("prompt missing id")
        elif not isinstance(pid, (int, str)):  # must be a hashable scalar for the id set
            errors.append(f"{where}: id must be an int or string, got {type(pid).__name__}")
        elif pid in ids:
            errors.append(f"duplicate prompt id {pid}")
        else:
            ids.add(pid)
        for field in ("raw", "refined", "domain"):
            if not p.get(field):
                errors.append(f"{where}: missing '{field}'")
        if domains and p.get("domain") not in domains:
            errors.append(f"{where}: domain {p.get('domain')!r} not in declared domains")
        if p.get("work_footprint") not in _WORK:
            errors.append(f"{where}: work_footprint must be one of {sorted(_WORK)}")
        if p.get("prompt_specificity") not in _SPEC:
            errors.append(f"{where}: prompt_specificity must be one of {sorted(_SPEC)}")
        rf = p.get("review_flag")
        if not isinstance(rf, dict) or "flag" not in rf or not isinstance(rf.get("flag"), bool):
            errors.append(f"{where}: review_flag must have a boolean 'flag'")
        elif rf.get("flag") and not rf.get("reason"):
            errors.append(f"{where}: review_flag true requires a 'reason'")
    if errors:
        print(f"FAIL: {len(errors)} problem(s) in agent-prompt-catalog.yaml:", file=sys.stderr)
        for e in errors: print(f"  - {e}", file=sys.stderr)
        return 1
    flagged = sum(1 for p in prompts if (p.get("review_flag") or {}).get("flag"))
    print(f"OK: agent-prompt-catalog v{d['version']} — {len(prompts)} prompts, {flagged} flagged for review.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
