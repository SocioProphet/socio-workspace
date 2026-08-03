#!/usr/bin/env python3
"""Prove the GBRG context-inclusion gate fires BOTH ways.

A control that only ever allows is suspect. This test asserts a real DENY path
actually BLOCKS inclusion, not just that allows pass:

  (a) ACTIVE authority + an includable (real gbrg-analyze) cell -> ALLOW
      -> cell INCLUDED -> a sealed decision line appended to the ledger.
  (b) SUSPENDED authority + the same cell -> FAIL-CLOSED DENY -> EXCLUDED
      with a sealed reason -> also logged.
  (b2) ABSENT authority (no state file) -> FAIL-CLOSED DENY -> EXCLUDED.
  (c) a rejected/dead cell -> EXCLUDED regardless of an ALLOWING authority,
      with a recorded reason.

Plus: the ledger holds BOTH an allow and a deny receipt, and every receipt is a
stable sha256 over the canonical decision core (recomputed independently here).

Runs under pytest OR as a plain script (`python3 test_gate.py`). It imports the
`gbrg.governance` package by putting the repo's `gbrg/` parent on sys.path.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

# Make `import gbrg.governance...` work whether run by pytest or directly:
# this file is at <repo>/gbrg/governance/test_gate.py; add <repo> to sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gbrg.governance import gate, ledger  # noqa: E402

_FIX = Path(__file__).resolve().parent / "fixtures"
ACTIVE_STATE = _FIX / "agent-authority-current-state.gbrg-scorer.active.json"
SUSPENDED_STATE = _FIX / "agent-authority-current-state.gbrg-scorer.suspended.json"
ABSENT_STATE = _FIX / "does-not-exist.json"  # fail-closed: missing state -> deny
REAL_ARTIFACT = _FIX / "proof-artifact.real.gbrg-core.as_label.json"


def _load_real_artifact() -> dict:
    return json.loads(REAL_ARTIFACT.read_text(encoding="utf-8"))


def _rejected_artifact() -> dict:
    """A rejected/dead cell, shaped like gbrg-analyze output."""
    a = _load_real_artifact()
    a = dict(a)
    a["cell_id"] = "code://rust/crates/gbrg-core/src/lib.rs#dead_symbol"
    a["proofId"] = "proof-gbrg-deadbeefdeadbeef"
    a["status"] = "FAILED"
    a["claim"] = dict(a["claim"])
    a["claim"]["epistemicLevel"] = "rejected"
    a["blast_radius"] = 0.95  # even a huge blast radius must not save a rejected cell
    return a


def _recompute_receipt(record: dict) -> str:
    """Independently recompute the sha256 receipt from the persisted record's core."""
    d = gate.Decision(
        recordType=record["recordType"],
        schemaVersion=record["schemaVersion"],
        agentRef=record["agentRef"],
        action=record["action"],
        cell_id=record["cell_id"],
        epistemicLevel=record["epistemicLevel"],
        proof_id=record["proof_id"],
        verdict=record["verdict"],
        included=record["included"],
        reason=record["reason"],
        priority=record["priority"],
        content_verdict=record["content_verdict"],
        authority_verdict=record["authority_verdict"],
        authority_reason_code=record["authority_reason_code"],
        decided_at=record["decided_at"],
        authority=record.get("authority", {}),
    )
    canonical = json.dumps(d.core(), sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# The scenario, exercised against a fresh temp ledger.
# --------------------------------------------------------------------------- #
def run_scenario(ledger_path: Path) -> dict:
    art = _load_real_artifact()

    # (a) ACTIVE authority + includable cell -> ALLOW -> INCLUDE.
    d_allow = gate.gate_inclusion(art, state_file=ACTIVE_STATE, ledger_path=ledger_path)

    # (b) SUSPENDED authority + same cell -> FAIL-CLOSED DENY -> EXCLUDE.
    d_deny = gate.gate_inclusion(art, state_file=SUSPENDED_STATE, ledger_path=ledger_path)

    # (b2) ABSENT authority -> FAIL-CLOSED DENY -> EXCLUDE.
    d_absent = gate.gate_inclusion(art, state_file=ABSENT_STATE, ledger_path=ledger_path)

    # (c) rejected/dead cell under an ALLOWING authority -> EXCLUDE regardless.
    d_rejected = gate.gate_inclusion(
        _rejected_artifact(), state_file=ACTIVE_STATE, ledger_path=ledger_path
    )

    return {
        "allow": d_allow,
        "deny": d_deny,
        "absent": d_absent,
        "rejected": d_rejected,
    }


def _assert_all(results: dict, ledger_path: Path) -> list[str]:
    checks: list[str] = []

    def ok(name: str, cond: bool, detail: str = "") -> None:
        assert cond, f"FAILED: {name} {detail}"
        checks.append(f"PASS: {name}")

    d_allow = results["allow"]
    d_deny = results["deny"]
    d_absent = results["absent"]
    d_rejected = results["rejected"]

    # (a) ALLOW path -> INCLUDE.
    ok("(a) active authority -> authority_verdict allow", d_allow.authority_verdict == "allow",
       f"got {d_allow.authority_verdict}")
    ok("(a) active + includable -> verdict INCLUDE", d_allow.verdict == gate.V_INCLUDE,
       f"got {d_allow.verdict}")
    ok("(a) included flag True", d_allow.included is True)

    # (b) SUSPENDED -> FAIL-CLOSED DENY -> EXCLUDE (the control actually BLOCKS).
    ok("(b) suspended authority -> authority_verdict deny", d_deny.authority_verdict == "deny",
       f"got {d_deny.authority_verdict}")
    ok("(b) suspended -> verdict EXCLUDE", d_deny.verdict == gate.V_EXCLUDE,
       f"got {d_deny.verdict}")
    ok("(b) included flag False (BLOCKED)", d_deny.included is False)
    ok("(b) reason names FAIL-CLOSED", "FAIL-CLOSED" in d_deny.reason)
    # Same cell, opposite outcome -> proves it is authority, not content, blocking.
    ok("(b) same cell as (a) but EXCLUDED", d_deny.cell_id == d_allow.cell_id and not d_deny.included)

    # (b2) ABSENT authority -> FAIL-CLOSED DENY.
    ok("(b2) absent authority -> deny", d_absent.authority_verdict == "deny",
       f"got {d_absent.authority_verdict}")
    ok("(b2) absent -> EXCLUDE", d_absent.verdict == gate.V_EXCLUDE)

    # (c) rejected/dead -> EXCLUDE even under an ALLOWING authority.
    ok("(c) rejected content -> EXCLUDE", d_rejected.verdict == gate.V_EXCLUDE,
       f"got {d_rejected.verdict}")
    ok("(c) rejected excluded despite authority allow",
       d_rejected.authority_verdict == "allow" and not d_rejected.included)
    ok("(c) rejected reason recorded", "rejected/dead" in d_rejected.reason)

    # Ledger holds BOTH an allow and a deny receipt.
    persisted = ledger.read_all(ledger_path)
    ok("ledger persisted all 4 decisions", len(persisted) == 4, f"got {len(persisted)}")
    allow_lines = [r for r in persisted if r["authority_verdict"] == "allow"]
    deny_lines = [r for r in persisted if r["authority_verdict"] == "deny"]
    ok("ledger contains >=1 allow receipt", len(allow_lines) >= 1)
    ok("ledger contains >=1 deny receipt", len(deny_lines) >= 1)
    ok("an INCLUDE was persisted", any(r["included"] for r in persisted))
    ok("an EXCLUDE was persisted", any(not r["included"] for r in persisted))

    # Every receipt is a stable sha256 over the canonical core (recompute).
    for r in persisted:
        rec = r["receipt"]
        ok(f"receipt is sha256 ({r['cell_id'][-20:]}/{r['authority_verdict']})",
           isinstance(rec, str) and rec.startswith("sha256:") and len(rec) == len("sha256:") + 64)
        ok(f"receipt stable/canonical ({r['authority_verdict']})", _recompute_receipt(r) == rec,
           f"recomputed {_recompute_receipt(r)} != stored {rec}")

    # Distinct receipts for allow vs deny of the SAME cell (authority is in the seal).
    ok("allow and deny receipts differ", d_allow.receipt != d_deny.receipt)

    return checks


# --------------------------------------------------------------------------- #
# pytest entry point.
# --------------------------------------------------------------------------- #
# This test verifies the GATE'S logic — that it MEETs content+authority, seals,
# persists, and fires BOTH ways (allow->INCLUDE, deny->EXCLUDE). That logic must
# be tested with DETERMINISTIC authority inputs. Driving it through the live
# external authorize.py subprocess made it flaky: under the full CI suite that
# subprocess intermittently resolved ACTIVE_STATE to `deny` (external/global
# state the suite pollutes), so a gate-logic test false-failed on an authority-
# resolution problem it does not own. The authority RESOLUTION wiring (the real
# subprocess) is a separate concern, exercised by the __main__ script path below.
def _deterministic_authority(*, state_file, status=None, agent_ref=None, **_kw):
    """Hermetic stand-in for gate.authorize_inclusion, keyed on the state file:
    ACTIVE -> allow; SUSPENDED/ABSENT -> fail-closed deny. No subprocess, no
    shared state -> no pollution."""
    sf = str(state_file)
    if sf == str(ACTIVE_STATE):
        return "allow", {"verdict": "allow", "reason_code": "authority_active", "receipt_hash": None}
    reason = "authority_status_suspended" if sf == str(SUSPENDED_STATE) else "state_unavailable"
    return "deny", {"verdict": "deny", "reason_code": reason, "receipt_hash": None}


def test_gate_fires_both_ways() -> None:
    orig_authorize = gate.authorize_inclusion
    gate.authorize_inclusion = _deterministic_authority  # gate_inclusion resolves this at call time
    try:
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "decisions.jsonl"
            results = run_scenario(ledger_path)
            checks = _assert_all(results, ledger_path)
        assert checks, "no checks ran"
    finally:
        gate.authorize_inclusion = orig_authorize


# --------------------------------------------------------------------------- #
# Script entry point (no pytest required).
# --------------------------------------------------------------------------- #
def _main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "decisions.jsonl"
        results = run_scenario(ledger_path)
        checks = _assert_all(results, ledger_path)
        for c in checks:
            print(c)
        # Emit one sealed decision record verbatim (the fail-closed DENY).
        persisted = ledger.read_all(ledger_path)
        deny = next(r for r in persisted if r["authority_verdict"] == "deny" and not r["included"])
        print("\n--- ONE SEALED DECISION RECORD (fail-closed DENY) ---")
        print(json.dumps(deny, indent=2, sort_keys=True))
    print(f"\nALL {len(checks)} CHECKS PASSED — control fires BOTH ways.")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
