#!/usr/bin/env python3
"""Validate the GitHub tool impedance ledger.

Stdlib-only validator for registry/github-tool-impedance-ledger.yaml.
The parser intentionally supports the subset of YAML used by the ledger:
indentation-based mappings, lists, strings, booleans, integers, null, and
literal/folded block scalars.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "registry" / "github-tool-impedance-ledger.yaml"

REQUIRED_TOP = {"ledger_id", "status", "schema", "purpose", "records"}
REQUIRED_RECORD = {
    "event_id",
    "observed_at",
    "source_context",
    "repository",
    "operation_intended",
    "observed_failure",
    "failure_classes",
    "impedance_symbols",
    "attribution",
    "evidence",
    "confidence",
    "status",
}
FAILURE_CLASSES = {
    "CONNECTOR_SCHEMA",
    "CONNECTOR_SAFETY_LAYER",
    "CONNECTOR_PARTIAL_SURFACE",
    "GITHUB_ASYNC_STATE",
    "BRANCH_PROTECTION",
    "STATUS_CONTEXT_MISMATCH",
    "CI_ENVIRONMENT_DRIFT",
    "STALE_BRANCH",
    "DRAFT_READY_TRANSITION",
    "AUTO_MERGE_UNAVAILABLE",
    "PERMISSION_BOUNDARY",
    "RATE_LIMIT",
    "SEARCH_INDEX_GAP",
    "PAYLOAD_SIZE_OR_SHAPE",
    "ASSISTANT_MISUSE",
    "REAL_REPO_DEFECT",
    "UNKNOWN",
}
IMPEDANCE_SYMBOLS = {
    "Gamma_i",
    "tau_s",
    "chi_m",
    "rho_r",
    "nu_n",
    "pi_1",
    "sigma_p",
    "alpha_m",
    "beta_p",
    "delta_r",
    "epsilon_r",
    "kappa_r",
    "omega_p",
    "lambda_v",
    "mu_h",
    "T_i",
    "R_0",
    "Pi_s",
    "Delta_n",
    "Delta_c",
    "Delta_a",
    "E_plus",
    "G_not_B",
    "H_star",
    "I_r",
    "S_d",
    "N_not_E",
    "C_m",
    "A_i",
    "W_to_K",
}
PR_STATES = {
    "unknown",
    "draft",
    "ready",
    "green",
    "green_but_unprotected",
    "blocked_expected_context",
    "mergeability_pending",
    "stale",
    "superseded",
    "probe_only",
    "canonical",
    "merged",
    "closed_unmerged",
    "abandoned",
    "not_applicable",
}
ATTRIBUTION_VALUES = {"none", "possible", "likely", "primary", "unknown"}
CONFIDENCE = {"low", "medium", "high"}
STATUS = {"proposed", "observed", "verified", "superseded", "rejected", "needs_evidence"}


class YamlError(ValueError):
    pass


def strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line.rstrip()


def scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "Null", "~"}:
        return None
    if (value.startswith("'") and value.endswith("'")) or (value.startswith('"') and value.endswith('"')):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [scalar(part.strip()) for part in inner.split(",")]
    return value


def preprocess(text: str) -> list[tuple[int, str]]:
    raw = text.splitlines()
    out: list[tuple[int, str]] = []
    i = 0
    while i < len(raw):
        line = strip_comment(raw[i])
        if not line.strip():
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        content = line.strip()
        if content.endswith(": >-") or content.endswith(": |"):
            key = content.split(":", 1)[0]
            block_indent = None
            parts: list[str] = []
            i += 1
            while i < len(raw):
                next_line = raw[i]
                if not next_line.strip():
                    parts.append("")
                    i += 1
                    continue
                next_indent = len(next_line) - len(next_line.lstrip(" "))
                if next_indent <= indent:
                    break
                if block_indent is None:
                    block_indent = next_indent
                parts.append(next_line[block_indent:])
                i += 1
            text_value = " ".join(part.strip() for part in parts).strip()
            out.append((indent, f"{key}: {text_value}"))
            continue
        out.append((indent, content))
        i += 1
    return out


def parse_yaml_subset(text: str) -> Any:
    lines = preprocess(text)
    index = 0

    def parse_block(indent: int) -> Any:
        nonlocal index
        if index >= len(lines):
            return {}
        if lines[index][0] < indent:
            return {}
        is_list = lines[index][1].startswith("- ")
        if is_list:
            result: list[Any] = []
            while index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("- "):
                item = lines[index][1][2:]
                index += 1
                if not item:
                    result.append(parse_block(indent + 2))
                elif ":" in item and not item.startswith(("'", '"')):
                    key, rest = item.split(":", 1)
                    obj: dict[str, Any] = {}
                    obj[key.strip()] = scalar(rest.strip()) if rest.strip() else parse_block(indent + 2)
                    if index < len(lines) and lines[index][0] > indent:
                        child = parse_block(indent + 2)
                        if isinstance(child, dict):
                            obj.update(child)
                        else:
                            raise YamlError(f"list item mapping at indent {indent} had non-mapping child")
                    result.append(obj)
                else:
                    result.append(scalar(item))
            return result
        result_dict: dict[str, Any] = {}
        while index < len(lines) and lines[index][0] == indent and not lines[index][1].startswith("- "):
            content = lines[index][1]
            if ":" not in content:
                raise YamlError(f"expected key-value line, got: {content}")
            key, rest = content.split(":", 1)
            key = key.strip()
            rest = rest.strip()
            index += 1
            if rest:
                result_dict[key] = scalar(rest)
            else:
                if index < len(lines) and lines[index][0] > indent:
                    result_dict[key] = parse_block(lines[index][0])
                else:
                    result_dict[key] = None
        return result_dict

    parsed = parse_block(0)
    if index != len(lines):
        raise YamlError("unparsed trailing lines")
    return parsed


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate(data: Any) -> list[str]:
    errors: list[str] = []
    require(isinstance(data, dict), "ledger root must be a mapping", errors)
    if not isinstance(data, dict):
        return errors
    missing_top = sorted(REQUIRED_TOP - set(data))
    require(not missing_top, f"missing top-level fields: {missing_top}", errors)
    records = data.get("records")
    require(isinstance(records, list), "records must be a list", errors)
    if not isinstance(records, list):
        return errors
    seen: set[str] = set()
    for idx, rec in enumerate(records):
        prefix = f"records[{idx}]"
        require(isinstance(rec, dict), f"{prefix} must be a mapping", errors)
        if not isinstance(rec, dict):
            continue
        event_id = rec.get("event_id")
        require(isinstance(event_id, str) and event_id, f"{prefix}.event_id must be a non-empty string", errors)
        if isinstance(event_id, str):
            require(event_id not in seen, f"duplicate event_id: {event_id}", errors)
            seen.add(event_id)
        missing = sorted(REQUIRED_RECORD - set(rec))
        require(not missing, f"{prefix} missing required fields: {missing}", errors)
        repo = rec.get("repository")
        require(isinstance(repo, dict) and isinstance(repo.get("full_name"), str), f"{prefix}.repository.full_name required", errors)
        source = rec.get("source_context")
        require(isinstance(source, dict) and isinstance(source.get("context_type"), str), f"{prefix}.source_context.context_type required", errors)
        failure_classes = rec.get("failure_classes")
        require(isinstance(failure_classes, list) and bool(failure_classes), f"{prefix}.failure_classes must be non-empty list", errors)
        if isinstance(failure_classes, list):
            for value in failure_classes:
                require(value in FAILURE_CLASSES, f"{prefix}.failure_classes has unknown value {value!r}", errors)
        symbols = rec.get("impedance_symbols")
        require(isinstance(symbols, list) and bool(symbols), f"{prefix}.impedance_symbols must be non-empty list", errors)
        if isinstance(symbols, list):
            for value in symbols:
                require(value in IMPEDANCE_SYMBOLS, f"{prefix}.impedance_symbols has unknown value {value!r}", errors)
        pr_state = rec.get("pr_operational_state")
        if pr_state is not None:
            require(pr_state in PR_STATES, f"{prefix}.pr_operational_state has unknown value {pr_state!r}", errors)
        attribution = rec.get("attribution")
        require(isinstance(attribution, dict), f"{prefix}.attribution must be mapping", errors)
        if isinstance(attribution, dict):
            for key in ["native_github", "connector_wrapper", "assistant_operator", "permission_boundary", "real_repo_defect"]:
                require(attribution.get(key) in ATTRIBUTION_VALUES, f"{prefix}.attribution.{key} invalid", errors)
        evidence = rec.get("evidence")
        require(isinstance(evidence, dict) and isinstance(evidence.get("narrative_summary"), str), f"{prefix}.evidence.narrative_summary required", errors)
        require(rec.get("confidence") in CONFIDENCE, f"{prefix}.confidence invalid", errors)
        require(rec.get("status") in STATUS, f"{prefix}.status invalid", errors)
    return errors


def main() -> int:
    if not LEDGER_PATH.exists():
        print(f"missing ledger: {LEDGER_PATH}", file=sys.stderr)
        return 1
    try:
        data = parse_yaml_subset(LEDGER_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validation CLI should surface parser failure
        print(f"failed to parse {LEDGER_PATH}: {exc}", file=sys.stderr)
        return 1
    errors = validate(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"validated {len(data['records'])} GitHub tool impedance ledger records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
