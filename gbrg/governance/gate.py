#!/usr/bin/env python3
"""GBRG context-inclusion gate — no invisible authority.

Every decision to INCLUDE or EXCLUDE a semantic cell from a review/analysis
context is a DECLARED, SEALED, PERSISTED action. This module is the shared
foundation reused by both the GBRG governance layer and the MCP surface.

Two authorities must agree before a cell enters context (fail-closed MEET):

  1. CONTENT proposal (:func:`decide_inclusion`) — reads the cell's GBRG
     ``BlastRadiusProofArtifact`` (produced by ``gbrg-analyze``) and forms an
     include/exclude *proposal* from its epistemic evidence and blast radius.

  2. AUTHORITY gate (:func:`authorize_inclusion`) — calls the agent-registry
     fail-closed authorize surface (``tools/authorize.py``) to ask whether the
     producing agent (``agent-registry://gbrg/scorer``) is even *authorized* to
     admit content into context right now. A suspended/absent/invalid authority
     denies — regardless of how includable the content looks.

The final verdict is the MEET (the stricter) of the two: content EXCLUDE or
authority DENY both block inclusion. Only an includable proposal under an
allowing authority yields INCLUDE. Every resulting :class:`Decision` is sealed
with a sha256 receipt over its canonical core and persisted to the durable
append-only ledger (see :mod:`ledger`).

--------------------------------------------------------------------------------
ACTION-DIMENSION MAPPING (documented choice)
--------------------------------------------------------------------------------
agent-registry's authorize.py has five FIXED action dimensions
(tool / memory / autonomous / route / egress). "Include a cell into review
context" is admitting external content into the agent's working context/memory —
a read-into-memory authority. It is NOT a tool invocation (``tool``), autonomous
side-effecting action (``autonomous``), work-routing eligibility (``route``), or
data exfiltration (``egress``). We therefore map context inclusion onto the
``memory`` dimension (``authorityEffects.memoryAccess``). A suspended agent
(global authority_status deny) is blocked on every dimension, so a quarantined
scorer can never smuggle a cell into context.

--------------------------------------------------------------------------------
INCLUSION RULE (documented choice) — see :func:`decide_inclusion`
--------------------------------------------------------------------------------
The context being assembled is a *human/agent REVIEW* context: it should surface
the cells that most need scrutiny and suppress noise and dead code.

  * EXCLUDE, always — a ``rejected`` epistemicLevel or a dead/failed status
    (``FAILED`` / ``BLOCKED``). Rejected or dead cells carry no warrant and must
    never occupy review attention. This fires regardless of authority.
  * INCLUDE, high priority — high-blast-radius, low-evidence cells: a large
    ``blast_radius`` with weak epistemic backing (no ``test_coverage_reach``, or
    a ``speculative`` / ``synthetic`` / ``empirical`` level). These are the
    dangerous unknowns a reviewer must see.
  * INCLUDE, normal — any other live cell whose ``blast_radius`` clears the
    inclusion floor.
  * DEPRIORITIZE (still included, lower priority) — ``generated`` (codegen)
    cells: real but machine-authored, so they should not crowd out
    human-authored risk. ``generated`` is the separate top-level boolean, NOT
    the ``synthetic`` epistemicLevel (which means synthetic DATA).
  * EXCLUDE, normal — live but low-blast-radius, well-evidenced cells: nothing
    for a reviewer to worry about.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import ledger

# --------------------------------------------------------------------------- #
# Wiring to the consumed (never-modified) agent-registry authorize surface.
# --------------------------------------------------------------------------- #
AGENT_REF = "agent-registry://gbrg/scorer"

# Context inclusion is a read-into-memory authority -> the `memory` dimension.
INCLUSION_ACTION = "memory"

# Located relative to this file: sociosphere/gbrg/governance -> dev/agent-registry.
# gate.py is at .../dev/sociosphere<...>/gbrg/governance/gate.py; agent-registry
# is a sibling checkout under ~/dev. Resolved by walking up to `dev/`.
def _find_agent_registry() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "agent-registry" / "tools" / "authorize.py"
        if candidate.exists():
            return candidate
    # Fall back to the canonical estate path.
    return Path.home() / "dev" / "agent-registry" / "tools" / "authorize.py"


AUTHORIZE_PY = _find_agent_registry()

# authorize.py exit codes (fail-closed): 0=allow, 3=require-review, 1=deny/error.
EXIT_ALLOW = 0
EXIT_DENY = 1
EXIT_REVIEW = 3

# Content-proposal verdicts.
INCLUDE = "INCLUDE"
EXCLUDE = "EXCLUDE"

# Final sealed verdicts.
V_INCLUDE = "INCLUDE"
V_EXCLUDE = "EXCLUDE"

# Inclusion floor for blast radius (0.0-1.0). At/above -> a live cell is worth
# a reviewer's context; below -> excluded as low-consequence noise. Set low (0.20)
# because gbrg-analyze's blast_radius is a normalised score whose mass, on real
# trees, sits in the low band; only near-zero-blast cells are true noise.
BLAST_INCLUDE_FLOOR = 0.20
# A cell at/above this blast radius with weak evidence is a high-priority unknown.
BLAST_HIGH_RISK = 0.60


@dataclass
class Proposal:
    """The CONTENT-only inclusion proposal derived from a ProofArtifact."""

    verdict: str  # INCLUDE | EXCLUDE
    priority: str  # "high" | "normal" | "deprioritized" | "n/a"
    reason: str


@dataclass
class Decision:
    """A sealed, persist-ready context inclusion/exclusion decision.

    Shaped to reference agent-registry's TrustOpsAgentAuthorityDecision: it carries
    the ``authority`` sub-record (the raw authorize.py decision, with its own
    receipt) and adds GBRG's cell-level context verdict on top, then seals the
    whole core with its own ``receipt``.
    """

    recordType: str
    schemaVersion: str
    agentRef: str
    action: str
    cell_id: str
    epistemicLevel: str
    proof_id: str
    verdict: str  # V_INCLUDE | V_EXCLUDE
    included: bool
    reason: str
    priority: str
    content_verdict: str
    authority_verdict: str
    authority_reason_code: str
    decided_at: str
    authority: dict[str, Any] = field(default_factory=dict)
    receipt: str = ""

    def core(self) -> dict[str, Any]:
        """The canonical, receipt-sealed core (stable subset, sorted at hash)."""
        return {
            "recordType": self.recordType,
            "schemaVersion": self.schemaVersion,
            "agentRef": self.agentRef,
            "action": self.action,
            "cell_id": self.cell_id,
            "epistemicLevel": self.epistemicLevel,
            "proof_id": self.proof_id,
            "verdict": self.verdict,
            "included": self.included,
            "reason": self.reason,
            "priority": self.priority,
            "content_verdict": self.content_verdict,
            "authority_verdict": self.authority_verdict,
            "authority_reason_code": self.authority_reason_code,
            "authority_receipt": self.authority.get("receipt_hash"),
            "decided_at": self.decided_at,
        }

    def seal(self) -> "Decision":
        """Compute the sha256 receipt over the canonicalized core (sorted keys)."""
        canonical = json.dumps(self.core(), sort_keys=True, separators=(",", ":"))
        self.receipt = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return self

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# 1. CONTENT proposal.
# --------------------------------------------------------------------------- #
def decide_inclusion(proof_artifact: dict) -> Proposal:
    """Form the include/exclude CONTENT proposal for a cell from its ProofArtifact.

    See the module docstring for the full documented rule. This is content-only;
    it does not consult the authority gate.
    """
    claim = proof_artifact.get("claim", {}) or {}
    level = claim.get("epistemicLevel", "")
    status = proof_artifact.get("status", "")
    blast = float(proof_artifact.get("blast_radius", 0.0) or 0.0)
    tested = bool(proof_artifact.get("test_coverage_reach", False))
    generated = bool(proof_artifact.get("generated", False))

    # (c) rejected / dead -> EXCLUDE regardless.
    if level == "rejected" or status in {"FAILED", "BLOCKED"}:
        return Proposal(
            verdict=EXCLUDE,
            priority="n/a",
            reason=f"rejected/dead cell (epistemicLevel={level!r}, status={status!r}) — no warrant to review",
        )

    weak_evidence = (not tested) or level in {"speculative", "synthetic", "empirical"}

    # High-blast-radius + weak evidence -> the dangerous unknowns. INCLUDE high.
    if blast >= BLAST_HIGH_RISK and weak_evidence:
        return Proposal(
            verdict=INCLUDE,
            priority="high",
            reason=(
                f"high blast_radius={blast:.3f} with weak evidence "
                f"(test_coverage_reach={tested}, epistemicLevel={level!r}) — must be reviewed"
            ),
        )

    # Live cell clearing the inclusion floor.
    if blast >= BLAST_INCLUDE_FLOOR:
        priority = "deprioritized" if generated else "normal"
        gen_note = " (generated/codegen — deprioritized)" if generated else ""
        return Proposal(
            verdict=INCLUDE,
            priority=priority,
            reason=f"blast_radius={blast:.3f} at/above inclusion floor {BLAST_INCLUDE_FLOOR}{gen_note}",
        )

    # Live, low-consequence, adequately evidenced -> EXCLUDE as noise.
    return Proposal(
        verdict=EXCLUDE,
        priority="n/a",
        reason=f"low blast_radius={blast:.3f} below inclusion floor {BLAST_INCLUDE_FLOOR} — not review-worthy",
    )


# --------------------------------------------------------------------------- #
# 2. AUTHORITY gate — subprocess the fail-closed agent-registry surface.
# --------------------------------------------------------------------------- #
def authorize_inclusion(
    *,
    state_file: str | Path | None,
    status: str | None = None,
    agent_ref: str = AGENT_REF,
    action: str = INCLUSION_ACTION,
    authorize_py: Path = AUTHORIZE_PY,
) -> tuple[str, dict[str, Any]]:
    """Call agent-registry's authorize.py FAIL-CLOSED. Returns (verdict, raw_decision).

    verdict is one of "allow" / "require-review" / "deny". Any non-zero /
    unexpected exit, missing state, or unparseable output collapses to "deny"
    (fail-closed) — a control that cannot resolve authority must not permit.
    """
    cmd = [
        "python3",
        str(authorize_py),
        "check",
        agent_ref,
        "--action",
        action,
    ]
    if state_file is not None:
        cmd += ["--state-file", str(state_file)]
    if status is not None:
        cmd += ["--status", status]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(authorize_py.parent),  # authorize.py imports sibling helpers.
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError) as exc:  # fail closed
        return "deny", {
            "verdict": "deny",
            "reason_code": "authorize_invocation_failed",
            "error": str(exc),
            "receipt_hash": None,
        }

    # Map exit code -> verdict, fail-closed on anything unexpected.
    exit_verdict = {
        EXIT_ALLOW: "allow",
        EXIT_REVIEW: "require-review",
        EXIT_DENY: "deny",
    }.get(proc.returncode, "deny")

    try:
        raw = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        raw = {}

    # Trust the exit code as the authoritative gate signal (fail-closed).
    if not raw:
        raw = {
            "verdict": exit_verdict,
            "reason_code": "no_decision_payload",
            "receipt_hash": None,
            "exit_code": proc.returncode,
            "stderr": proc.stderr.strip(),
        }
    # If exit code and payload disagree, the stricter (deny) wins.
    payload_verdict = raw.get("verdict", exit_verdict)
    if "deny" in {exit_verdict, payload_verdict}:
        verdict = "deny"
    elif exit_verdict == payload_verdict:
        verdict = exit_verdict
    else:
        verdict = "deny"  # disagreement -> fail closed
    return verdict, raw


# --------------------------------------------------------------------------- #
# 3. The gate: MEET(content, authority) -> sealed, persisted Decision.
# --------------------------------------------------------------------------- #
def gate_inclusion(
    proof_artifact: dict,
    *,
    state_file: str | Path | None,
    status: str | None = None,
    ledger_path: Path | str | None = None,
    agent_ref: str = AGENT_REF,
    persist: bool = True,
) -> Decision:
    """Decide, SEAL, and PERSIST the context inclusion verdict for one cell.

    Final verdict = MEET(content proposal, authority verdict):
      * content EXCLUDE  -> EXCLUDE (dead/rejected/noise, regardless of authority)
      * authority not "allow" -> EXCLUDE (fail-closed DENY blocks inclusion)
      * otherwise -> INCLUDE
    Every decision (INCLUDE and EXCLUDE) is sealed and appended to the ledger.
    """
    claim = proof_artifact.get("claim", {}) or {}
    proposal = decide_inclusion(proof_artifact)
    authority_verdict, authority_raw = authorize_inclusion(
        state_file=state_file, status=status, agent_ref=agent_ref
    )

    # MEET: both must be permissive to include.
    if proposal.verdict == EXCLUDE:
        final = V_EXCLUDE
        reason = f"content: {proposal.reason}"
    elif authority_verdict != "allow":
        final = V_EXCLUDE  # fail-closed: authority denied / review / unresolved
        reason = (
            f"FAIL-CLOSED: authority verdict={authority_verdict!r} "
            f"({authority_raw.get('reason_code')}) blocked inclusion; "
            f"content proposal was {proposal.verdict}: {proposal.reason}"
        )
    else:
        final = V_INCLUDE
        reason = f"authority allowed + content: {proposal.reason}"

    decision = Decision(
        recordType="ContextInclusionDecision",
        schemaVersion="gbrg.governance.context-inclusion-decision.v0.1",
        agentRef=agent_ref,
        action=INCLUSION_ACTION,
        cell_id=proof_artifact.get("cell_id", ""),
        epistemicLevel=claim.get("epistemicLevel", ""),
        proof_id=proof_artifact.get("proofId", ""),
        verdict=final,
        included=(final == V_INCLUDE),
        reason=reason,
        priority=proposal.priority if final == V_INCLUDE else "n/a",
        content_verdict=proposal.verdict,
        authority_verdict=authority_verdict,
        authority_reason_code=str(authority_raw.get("reason_code", "")),
        decided_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        authority=authority_raw,
    ).seal()

    if persist:
        ledger.append(decision.to_dict(), ledger_path=ledger_path)

    return decision
