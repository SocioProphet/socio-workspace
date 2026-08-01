#!/usr/bin/env python3
"""GBRG MCP zero-trust gate — per-call authority + durable ledger for the MCP surface.

This is the fail-closed governance plumbing behind the GBRG MCP server
(``src/server.ts``). The TypeScript surface is a thin MCP/stdio transport shell;
ALL authority, ledger, and inclusion logic lives here and REUSES the shared
``gbrg/governance`` gate foundation (``feat/gbrg-gate``) — it is not reimplemented.

Conformance targets (spec: /Users/michaelheller/dev/mcp-a2a-zero-trust):
  * IDENTITY   — the server has a SPIFFE id (:data:`SPIFFE_ID`); its agent-registry
                 actor is ``agent-registry://gbrg/mcp``.
  * AUTHORIZE  — every tool call is gated by ``gate.authorize_inclusion`` (the same
                 authorize path the governance layer uses), which subprocesses the
                 never-modified agent-registry ``authorize.py`` FAIL-CLOSED.
  * LEDGER     — every call (allow AND refuse) emits a hash-chained ``LedgerEvent``
                 (mcp/ledger schema) via the gate's DURABLE append-only ledger
                 (``gbrg.governance.ledger.append``). No ledger event => failure.
                 Tamper-evidence is ENFORCED, not cosmetic: the chain is anchored
                 at ``ledger.GENESIS`` and every read path
                 (``ledger.read_all``/``read_verified``) recomputes each event
                 ``hash`` and walks the ``prev_hash`` chain via
                 ``ledger.verify_ledger``, raising on the first bad hash, broken
                 link, reorder, insertion, or deletion. RESIDUAL: a writer that
                 rebuilds the WHOLE file as a fresh consistent chain from GENESIS
                 verifies as internally ok — detecting that needs an out-of-band
                 head anchor (``ledger.verify_head``).
  * REGISTRY   — the 3 tools are declared in a capability_registry.json conforming
                 to mcp/registry/capability_registry.schema.json; ``policy_hash`` on
                 every ledger event is the sha256 of that governing registry doc.
  * READ-ONLY  — all tools are ``effect: "read"`` over a frozen graph; NO
                 write/exec/egress capability is declared.

Subcommands (invoked by the TS server or the test harness):
  gen-registry --out <path>
  authorize    --tool <t> --args-json <json> --state-file <s> [--status <st>]
               --ledger <l> --registry <r>
  emit-result  --tool <t> --result-json <json> --ledger <l> --registry <r>
  filter-include   (reads a JSON array of ProofArtifacts on stdin; prints the
                    subset the gate INCLUDES, using gate.decide_inclusion)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make `import gbrg.governance...` work: this file is at <repo>/gbrg/mcp/mcp_gate.py;
# add <repo> to sys.path (parents[2]) exactly as the governance tests do.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gbrg.governance import gate, ledger  # noqa: E402  (path set above)
from gbrg.governance.ledger import GENESIS  # noqa: E402  single source of the anchor

# --------------------------------------------------------------------------- #
# Identity (spec: TrustBoundary.spiffe_id / LedgerEvent.actor.spiffe_id).
# --------------------------------------------------------------------------- #
SPIFFE_ID = "spiffe://socioprophet/mcp/gbrg"
MCP_AGENT_REF = "agent-registry://gbrg/mcp"
SERVER_NAME = "gbrg-mcp"

# MCP tool invocation maps to the `tool` authority dimension of authorize.py
# (toolAccess). A suspended agent is denied on every dimension (global gate).
TOOL_ACTION = "tool"

# GENESIS is imported from gbrg.governance.ledger (single source of truth) so the
# writer here and the verifier there anchor the SAME chain.


def _sha(obj: Any) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


# --------------------------------------------------------------------------- #
# Tool capability descriptors — the single source of truth for the registry
# doc AND the per-call ledger target. All three are read-only.
# --------------------------------------------------------------------------- #
def _tool_descriptors() -> dict[str, dict[str, Any]]:
    proof_artifact_out = {
        "type": "object",
        "description": "GBRG BlastRadiusProofArtifact (never a bare float).",
        "required": ["proofId", "claim", "status", "blast_radius", "derivation", "declared_by"],
    }
    return {
        "impact_query": {
            "capability_ref": "capd://gbrg/mcp/impact_query",
            "effect": "read",
            "danger_class_hint": "LOW",
            "side_effect_tags": [],
            "schema": {
                "in": {
                    "type": "object",
                    "required": ["path"],
                    "properties": {
                        "path": {"type": "string"},
                        "cellId": {"type": "string"},
                    },
                },
                "out": proof_artifact_out,
            },
        },
        "minimal_context_query": {
            "capability_ref": "capd://gbrg/mcp/minimal_context_query",
            "effect": "read",
            "danger_class_hint": "LOW",
            "side_effect_tags": [],
            "schema": {
                "in": {
                    "type": "object",
                    "required": ["path"],
                    "properties": {"path": {"type": "string"}},
                },
                "out": {
                    "type": "object",
                    "description": "Only the cells the gate INCLUDES, each a ProofArtifact.",
                },
            },
        },
        "graph_status": {
            "capability_ref": "capd://gbrg/mcp/graph_status",
            "effect": "read",
            "danger_class_hint": "LOW",
            "side_effect_tags": [],
            "schema": {
                "in": {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}},
                "out": {"type": "object", "description": "Counts + epistemicLevel spread, wrapped as a ProofArtifact."},
            },
        },
    }


def _capability_digest(name: str, desc: dict[str, Any]) -> str:
    """Real sha256 over the tool's canonical capability descriptor."""
    core = {
        "name": name,
        "capability_ref": desc["capability_ref"],
        "effect": desc["effect"],
        "danger_class_hint": desc["danger_class_hint"],
        "side_effect_tags": desc["side_effect_tags"],
        "schema": desc["schema"],
    }
    return _sha(core)


def build_registry() -> dict[str, Any]:
    """The capability_registry.json document (conforms to the spec schema)."""
    descriptors = _tool_descriptors()
    tools = []
    for name, desc in descriptors.items():
        tools.append(
            {
                "name": name,
                "capability_ref": desc["capability_ref"],
                "capability_digest": _capability_digest(name, desc),
                "effect": desc["effect"],
                "side_effect_tags": desc["side_effect_tags"],
                "danger_class_hint": desc["danger_class_hint"],
                "schema": desc["schema"],
                "trustHints": {
                    "attestationRequired": True,
                    "grantRequired": True,
                    "ledgerMode": "required",
                },
            }
        )
    return {
        "servers": [
            {
                "name": SERVER_NAME,
                "side": "either",
                "tools": tools,
            }
        ]
    }


def _policy_hash(registry_path: Path) -> str:
    """sha256 of the governing capability-registry doc (canonicalized)."""
    doc = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    return _sha(doc)


def _tool_target(name: str, registry_path: Path) -> dict[str, Any]:
    doc = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    entry = next(
        t for s in doc["servers"] for t in s["tools"] if t["name"] == name
    )
    return {
        "kind": "mcp_tool",
        "spiffe_id": SPIFFE_ID,
        "capability_ref": entry["capability_ref"],
        "capability_digest": entry["capability_digest"],
        "server": SERVER_NAME,
        "tool": name,
    }


# --------------------------------------------------------------------------- #
# Durable, hash-chained ledger emission (reuses gbrg.governance.ledger.append).
# --------------------------------------------------------------------------- #
def _prev_hash(ledger_path: Path) -> str:
    """Next event's ``prev_hash`` = the current chain head (GENESIS if empty).

    Reads through the VERIFIED path so we refuse to extend a tampered chain
    (:class:`ledger.LedgerTamperError` propagates). L7: tolerate a mixed file by
    reading the last record's chained ``hash`` OR (single-writer invariant aside)
    its ``receipt``, instead of the old ``records[-1]["hash"]`` that KeyErrored on
    a governance-decision record.
    """
    records = ledger.read_all(ledger_path)
    if not records:
        return GENESIS
    last = records[-1]
    return last.get("hash") or last["receipt"]


def emit_event(
    *,
    event_type: str,
    tool: str,
    payload: dict[str, Any],
    allow: bool,
    reason: str,
    ledger_path: Path,
    registry_path: Path,
) -> dict[str, Any]:
    """Build, seal (hash-chain) and DURABLY append one spec-conformant LedgerEvent."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    event_id = "evt_" + uuid.uuid4().hex[:16]
    payload_hash = _sha(payload)
    policy_hash = _policy_hash(registry_path)
    prev_hash = _prev_hash(ledger_path)
    actor = {"spiffe_id": SPIFFE_ID}
    target = _tool_target(tool, registry_path)
    decision = {"allow": allow, "reason": reason}

    core = {
        "event_id": event_id,
        "ts": ts,
        "type": event_type,
        "actor": actor,
        "target": target,
        "payload_hash": payload_hash,
        "policy_hash": policy_hash,
        "prev_hash": prev_hash,
        "decision": decision,
    }
    event_hash = _sha(core)

    event = {
        "event_id": event_id,
        "ts": ts,
        "type": event_type,
        "actor": actor,
        "target": target,
        "payload_hash": payload_hash,
        "policy_hash": policy_hash,
        "prev_hash": prev_hash,
        "hash": event_hash,
        "decision": decision,
    }
    # DURABLE append-only sink — the gate foundation's ledger mechanism.
    ledger.append(event, ledger_path=ledger_path)
    return event


# --------------------------------------------------------------------------- #
# Subcommand: authorize (per-call gate) — emits the MCP_CALL event ALWAYS.
# --------------------------------------------------------------------------- #
def cmd_authorize(args: argparse.Namespace) -> int:
    tool = args.tool
    ledger_path = Path(args.ledger)
    registry_path = Path(args.registry)
    try:
        call_args = json.loads(args.args_json) if args.args_json else {}
    except json.JSONDecodeError:
        call_args = {"_unparseable": True}

    # REUSE the gate's authorize path -> agent-registry authorize.py, FAIL-CLOSED.
    # authorize.py is subprocessed with cwd=<agent-registry/tools>, so a relative
    # --state-file would resolve against the wrong dir; make it absolute first.
    state_file = str(Path(args.state_file).resolve()) if args.state_file else None
    verdict, raw = gate.authorize_inclusion(
        state_file=state_file,
        status=args.status,
        agent_ref=MCP_AGENT_REF,
        action=TOOL_ACTION,
    )
    allow = verdict == "allow"
    reason_code = str(raw.get("reason_code", ""))
    reason = f"authorize verdict={verdict} ({reason_code})"

    payload = {"tool": tool, "args": call_args, "verdict": verdict, "reason_code": reason_code}

    # EMIT the per-call ledger event for EVERY call (allow AND refuse).
    try:
        event = emit_event(
            event_type="MCP_CALL",
            tool=tool,
            payload=payload,
            allow=allow,
            reason=reason,
            ledger_path=ledger_path,
            registry_path=registry_path,
        )
        ledger_written = True
    except Exception as exc:  # noqa: BLE001  no event => hard failure
        print(json.dumps({
            "verdict": "deny",
            "reason_code": "ledger_emit_failed",
            "error": str(exc),
            "ledger_written": False,
            "event": None,
        }))
        return 1

    out = {
        "verdict": verdict,
        "reason_code": reason_code,
        "ledger_written": ledger_written,
        "event": {"event_id": event["event_id"], "hash": event["hash"], "prev_hash": event["prev_hash"], "type": event["type"]},
        "authority": raw,
    }
    print(json.dumps(out))
    return 0 if allow else 1


# --------------------------------------------------------------------------- #
# Subcommand: emit-result — the post-success MCP_RESULT event.
# --------------------------------------------------------------------------- #
def cmd_emit_result(args: argparse.Namespace) -> int:
    ledger_path = Path(args.ledger)
    registry_path = Path(args.registry)
    try:
        result = json.loads(args.result_json) if args.result_json else {}
    except json.JSONDecodeError:
        result = {"_unparseable": True}
    # Only hash a compact summary of the result (avoid unbounded payloads).
    summary = {"tool": args.tool, "result_keys": sorted(result.keys()) if isinstance(result, dict) else "array"}
    try:
        event = emit_event(
            event_type="MCP_RESULT",
            tool=args.tool,
            payload=summary,
            allow=True,
            reason="tool result served",
            ledger_path=ledger_path,
            registry_path=registry_path,
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ledger_written": False, "error": str(exc), "event": None}))
        return 1
    print(json.dumps({"ledger_written": True, "event": {"event_id": event["event_id"], "hash": event["hash"], "type": event["type"]}}))
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: filter-include — CONSUME the gate foundation's inclusion decision.
# --------------------------------------------------------------------------- #
def cmd_filter_include(_args: argparse.Namespace) -> int:
    data = json.loads(sys.stdin.read() or "[]")
    if isinstance(data, dict):
        data = [data]
    included: list[dict[str, Any]] = []
    for art in data:
        # M2: one malformed artifact must not abort the batch. If decide_inclusion
        # somehow raises on a pathological cell, FAIL TOWARD INCLUSION (surface it
        # for review) rather than silently dropping it or crashing filter-include.
        try:
            proposal = gate.decide_inclusion(art)  # gate foundation's content decision
        except Exception as exc:  # noqa: BLE001  defensive: never drop-on-crash
            enriched = dict(art) if isinstance(art, dict) else {"_raw": art}
            enriched["_inclusion"] = {
                "priority": "high",
                "reason": f"unverifiable artifact → included for review (decide_inclusion error: {exc})",
            }
            included.append(enriched)
            continue
        if proposal.verdict == gate.INCLUDE:
            enriched = dict(art)
            enriched["_inclusion"] = {"priority": proposal.priority, "reason": proposal.reason}
            included.append(enriched)
    print(json.dumps({"included": included, "included_count": len(included), "total": len(data)}))
    return 0


# --------------------------------------------------------------------------- #
# Subcommand: gen-registry.
# --------------------------------------------------------------------------- #
def cmd_gen_registry(args: argparse.Namespace) -> int:
    doc = build_registry()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"written": str(out), "servers": len(doc["servers"]), "tools": len(doc["servers"][0]["tools"])}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mcp_gate", description="GBRG MCP zero-trust gate.")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("gen-registry")
    g.add_argument("--out", required=True)
    g.set_defaults(func=cmd_gen_registry)

    a = sub.add_parser("authorize")
    a.add_argument("--tool", required=True)
    a.add_argument("--args-json", default="{}")
    a.add_argument("--state-file")
    a.add_argument("--status")
    a.add_argument("--ledger", required=True)
    a.add_argument("--registry", required=True)
    a.set_defaults(func=cmd_authorize)

    r = sub.add_parser("emit-result")
    r.add_argument("--tool", required=True)
    r.add_argument("--result-json", default="{}")
    r.add_argument("--ledger", required=True)
    r.add_argument("--registry", required=True)
    r.set_defaults(func=cmd_emit_result)

    f = sub.add_parser("filter-include")
    f.set_defaults(func=cmd_filter_include)

    return p


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
