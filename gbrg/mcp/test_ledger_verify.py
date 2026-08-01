#!/usr/bin/env python3
"""Prove the ledger's tamper-evidence ACTUALLY FIRES — a control that can fail.

The adversarial review's blocking finding was that the "sealed, hash-chained"
ledger was never verified on read, so tamper-evidence was cosmetic. This test
writes a REAL chain via the production writer (:func:`mcp_gate.emit_event`), then
TAMPERS it three ways and asserts :func:`ledger.verify_ledger` DETECTS each:

  (a) flip a ``deny`` event's ``decision.allow`` false -> true (content edit)
  (b) delete a record (and separately: reorder two records)
  (c) truncate + rebuild a FRESH, internally-consistent chain from GENESIS
      -> verify_ledger reports internally-ok (honest residual), but the
         out-of-band head anchor (:func:`ledger.verify_head`) DETECTS it.

Plus the happy path: an untampered chain verifies ok with head == anchor, and the
verified read path (:func:`ledger.read_all`) raises ``LedgerTamperError`` on tamper.

Runs under pytest OR as a plain script (``python3 test_ledger_verify.py``).
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

_MCP_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _MCP_DIR.parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))

import mcp_gate  # noqa: E402
from gbrg.governance import ledger  # noqa: E402


# --------------------------------------------------------------------------- #
# Independent canonical sha (matches the writer; recomputed here, not imported).
# --------------------------------------------------------------------------- #
def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha(obj: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def _write_lines(path: Path, records: list[dict]) -> None:
    path.write_text("".join(_canonical(r) + "\n" for r in records), encoding="utf-8")


def _rechain_from_genesis(records: list[dict]) -> list[dict]:
    """Rebuild a FRESH, internally-consistent chain: fix every prev_hash + hash."""
    head = ledger.GENESIS
    out: list[dict] = []
    for rec in records:
        new = dict(rec)
        new["prev_hash"] = head
        core = {k: v for k, v in new.items() if k != "hash"}
        new["hash"] = _sha(core)
        head = new["hash"]
        out.append(new)
    return out


def _build_valid_ledger(tmp: Path) -> tuple[Path, str]:
    """Write a real 4-event chain (allow + deny) via the production writer."""
    registry_path = tmp / "capability_registry.json"
    registry_path.write_text(json.dumps(mcp_gate.build_registry(), indent=2, sort_keys=True), "utf-8")
    ledger_path = tmp / "mcp-events.jsonl"

    calls = [
        ("impact_query", True, "authorize verdict=allow (ok)"),
        ("graph_status", True, "authorize verdict=allow (ok)"),
        ("impact_query", False, "authorize verdict=deny (agent_suspended)"),  # the deny we tamper
        ("minimal_context_query", True, "authorize verdict=allow (ok)"),
    ]
    for tool, allow, reason in calls:
        mcp_gate.emit_event(
            event_type="MCP_CALL",
            tool=tool,
            payload={"tool": tool, "allow": allow},
            allow=allow,
            reason=reason,
            ledger_path=ledger_path,
            registry_path=registry_path,
        )
    result = ledger.verify_ledger(ledger_path)
    assert result.ok, f"freshly-written ledger must verify: {result.reason}"
    return ledger_path, result.head  # head is the out-of-band anchor


def run_checks() -> list[str]:
    checks: list[str] = []

    def ok(name: str, cond: bool, detail: str = "") -> None:
        assert cond, f"FAILED: {name} {detail}"
        checks.append(f"PASS: {name}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        ledger_path, anchor = _build_valid_ledger(tmp)
        pristine = ledger._read_raw(ledger_path)
        ok("untampered ledger has 4 events", len(pristine) == 4, f"got {len(pristine)}")

        # -------- HAPPY PATH: untampered verifies ok, head == anchor. --------
        good = ledger.verify_ledger(ledger_path)
        ok("untampered -> verify ok", good.ok is True, str(good.reason))
        ok("untampered -> head == out-of-band anchor", good.head == anchor)
        ok("untampered -> verify_head ok against anchor",
           ledger.verify_head(ledger_path, expected_head=anchor).ok is True)
        ok("untampered -> read_all (verified) returns all 4",
           len(ledger.read_all(ledger_path)) == 4)

        # ============ (a) FLIP a deny event's decision to allow. ============
        tampered_a = [dict(r) for r in pristine]
        deny_idx = next(i for i, r in enumerate(tampered_a) if r["decision"]["allow"] is False)
        tampered_a[deny_idx] = dict(tampered_a[deny_idx])
        tampered_a[deny_idx]["decision"] = dict(tampered_a[deny_idx]["decision"])
        tampered_a[deny_idx]["decision"]["allow"] = True  # forge deny -> allow, keep old hash
        _write_lines(ledger_path, tampered_a)
        ra = ledger.verify_ledger(ledger_path)
        ok("(a) flipped deny->allow -> verify NOT ok", ra.ok is False, str(ra))
        ok("(a) break located at the forged record", ra.broken_index == deny_idx,
           f"got {ra.broken_index} want {deny_idx}")
        ok("(a) reason names bad event hash", "bad event hash" in (ra.reason or ""))
        raised = False
        try:
            ledger.read_all(ledger_path)  # verified read path must refuse
        except ledger.LedgerTamperError:
            raised = True
        ok("(a) verified read_all RAISES LedgerTamperError on the forgery", raised)

        # ================= (b1) DELETE a record. =================
        tampered_del = [dict(r) for r in pristine]
        del tampered_del[1]  # drop 2nd event -> event[2].prev_hash now dangles
        _write_lines(ledger_path, tampered_del)
        rb = ledger.verify_ledger(ledger_path)
        ok("(b1) deleted record -> verify NOT ok", rb.ok is False, str(rb))
        ok("(b1) reason names broken chain link", "broken chain link" in (rb.reason or ""))

        # ================= (b2) REORDER two records. =================
        tampered_ord = [dict(r) for r in pristine]
        tampered_ord[1], tampered_ord[2] = tampered_ord[2], tampered_ord[1]  # swap
        _write_lines(ledger_path, tampered_ord)
        rb2 = ledger.verify_ledger(ledger_path)
        ok("(b2) reordered records -> verify NOT ok", rb2.ok is False, str(rb2))
        ok("(b2) reorder breaks the chain link", "broken chain link" in (rb2.reason or ""))

        # ===== (c) TRUNCATE + REBUILD a fresh chain from GENESIS. =====
        # Change record 0's payload, then re-chain the whole file so it is
        # INTERNALLY consistent from GENESIS (a determined whole-file rewrite).
        forged = [dict(r) for r in pristine]
        forged[0] = dict(forged[0])
        forged[0]["payload_hash"] = _sha({"tool": "impact_query", "forged": True})
        forged = _rechain_from_genesis(forged)
        _write_lines(ledger_path, forged)
        rc = ledger.verify_ledger(ledger_path)
        # Honest residual: the rebuilt chain IS internally consistent.
        ok("(c) rebuilt-from-GENESIS chain is internally consistent (residual honesty)",
           rc.ok is True, str(rc.reason))
        ok("(c) but its head != the original anchor", rc.head != anchor)
        # The out-of-band anchor DETECTS the whole-file substitution.
        rc_anchored = ledger.verify_head(ledger_path, expected_head=anchor)
        ok("(c) verify_head against out-of-band anchor DETECTS substitution",
           rc_anchored.ok is False, str(rc_anchored))
        ok("(c) reason names head anchor mismatch",
           "head anchor mismatch" in (rc_anchored.reason or ""))

        # -------- Restore pristine -> everything verifies again. --------
        _write_lines(ledger_path, pristine)
        ok("restored pristine -> verify ok again", ledger.verify_ledger(ledger_path).ok is True)

    return checks


def test_ledger_tamper_is_detected() -> None:
    checks = run_checks()
    assert checks, "no checks ran"


def _main() -> int:
    checks = run_checks()
    for c in checks:
        print(c)
    print(f"\nALL {len(checks)} CHECKS PASSED — tamper-evidence FIRES (a),(b1),(b2),(c).")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
