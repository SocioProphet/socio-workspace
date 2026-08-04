"""Lazerus (Evidence-First Integrity) receipt ingest + lint — the *meter* half of the bridge.

Lazerus is the sensor: it watches a running system with cryptographic rigor and emits an
**Integrity Receipt** — a signed statement of "this replica's state committed to <state_root>,
co-signed by a BLS validator quorum, and here is a quarantine token (koe_id) if it disagrees
with its peers." Lazerus is deliberately *not the map*: it names sickness, it does not fail the
system back. This module is the conforming ingest — it parses a receipt and LINTS every field
against the published Lazerus token grammar, **fail-closed**: a receipt with one malformed token
is not "mostly fine", it is rejected, and a rejected receipt can never count toward a healthy
quorum (see automation/macro_triad.assess_triad).

We CONFORM to the grammar, we do not invent it (the estate rule: the shape authority owns the
shape). If Lazerus later ships a JSON Schema / AttestationBundle, this linter is where that
schema plugs in — the callers (macro_triad, beacon_producers.propose_state_failback) stay put.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# --- the published Lazerus token grammar (regexes verbatim from the framework brief) ---------
RE_TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
RE_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
RE_PILL_ID = re.compile(r"^urn:lz:pill:ctx@\d{4}\.\d{2}:n\d+k\d+:m\d+:r\d+:rho\d+of\d+:tau\d+$")
RE_LZ_ID = re.compile(r"^urn:lz:(bie|nie|cie|rie|report|mix):[A-Za-z0-9._\-]{6,}$")
# koe_id (quarantine token) extends the urn:lz: family; the brief names it but omits it from the
# id-class list, so we pin its own pattern rather than silently widening RE_LZ_ID.
RE_KOE_ID = re.compile(r"^urn:lz:koe:[A-Za-z0-9._\-]{6,}$")
RE_DID = re.compile(r"^did:(web|key):[A-Za-z0-9:._\-/%#]+$")
RE_FLOW_5T = re.compile(r"^5T:\d{1,3}(\.\d{1,3}){3}:\d{1,5}:\d{1,3}(\.\d{1,3}){3}:\d{1,5}:(TCP|UDP|QUIC)$")
# BLS12-381 quorum signature: G1 sig = 48 bytes (96 hex), G2 = 96 bytes (192 hex). Accept either.
RE_BLS_SIG = re.compile(r"^bls:[0-9a-f]{96}(?:[0-9a-f]{96})?$")
# A git commit the state_root was produced from — the failback target (short or full sha).
RE_GIT_SHA = re.compile(r"^[0-9a-f]{7,40}$")


@dataclass(frozen=True)
class ClusterReceipt:
    """A Lazerus Integrity Receipt for ONE k3s master-cluster's deployed state.

    The three fields the macro-triad turns on: ``state_root`` (what state this replica commits to
    — clusters agreeing on it form the healthy quorum), ``commit`` (the git sha that produced that
    state — the failback *target*), and ``koe_id`` (a quarantine token — when present this replica
    has already been fenced by Lazerus for disagreeing with its peers, so it is sick by decree).
    ``writer_principal`` / ``replica_principal`` must differ: Lazerus requires the thing that wrote
    a state and the thing that attests it be distinct, so a liar cannot self-certify.
    """
    cluster: str                 # did: — the k3s master/control-plane identity
    receipt_id: str              # urn:lz:rie:… — this evidence record
    issued_at: str               # RFC3339 Z
    state_root: str              # sha256: — Merkle commitment of the deployed desired-state
    commit: str                  # git sha the state_root was produced from (failback target)
    writer_principal: str        # did: — who wrote the state
    replica_principal: str       # did: — who attests it (MUST differ from writer)
    quorum_sigs: tuple = ()      # bls:… BLS quorum signatures over state_root
    koe_id: Optional[str] = None # urn:lz:koe:… quarantine token (present => already fenced)


@dataclass(frozen=True)
class LintResult:
    ok: bool
    receipt: Optional[ClusterReceipt] = None
    errors: tuple = field(default=())

    @property
    def quarantined(self) -> bool:
        """Well-formed AND carrying a koe_id — Lazerus already fenced this replica."""
        return self.ok and self.receipt is not None and self.receipt.koe_id is not None


def lint_receipt(raw: object) -> LintResult:
    """Parse + validate one Integrity Receipt against the Lazerus grammar. Fail-closed.

    Returns a ``LintResult`` — ``ok`` only when every present token matches its pattern, the
    required fields are all present, the quorum carries at least one signature, and the writer
    and replica principals are distinct. A non-dict, a missing field, or one malformed token
    fails the whole receipt (a partially-valid receipt is not admissible evidence).
    """
    errors: list = []
    if not isinstance(raw, dict):
        return LintResult(ok=False, errors=(f"receipt must be an object, got {type(raw).__name__}",))

    def check(name: str, pattern: re.Pattern, *, required: bool = True) -> Optional[str]:
        val = raw.get(name)
        if val is None:
            if required:
                errors.append(f"{name}: missing (required)")
            return None
        if not isinstance(val, str) or not pattern.match(val):
            errors.append(f"{name}: {val!r} does not match {pattern.pattern}")
            return None
        return val

    cluster = check("cluster", RE_DID)
    receipt_id = check("receipt_id", RE_LZ_ID)
    issued_at = check("issued_at", RE_TIME)
    state_root = check("state_root", RE_SHA256)
    commit = check("commit", RE_GIT_SHA)
    writer = check("writer_principal", RE_DID)
    replica = check("replica_principal", RE_DID)
    koe_id = check("koe_id", RE_KOE_ID, required=False)

    sigs = raw.get("quorum_sigs", [])
    if not isinstance(sigs, list) or not sigs:
        errors.append("quorum_sigs: must be a non-empty list of bls: signatures")
        sigs = []
    else:
        for s in sigs:
            if not isinstance(s, str) or not RE_BLS_SIG.match(s):
                errors.append(f"quorum_sigs: {s!r} is not a bls: signature")

    if writer and replica and writer == replica:
        errors.append("writer_principal == replica_principal: a replica may not self-attest")

    if errors:
        return LintResult(ok=False, errors=tuple(errors))

    return LintResult(
        ok=True,
        receipt=ClusterReceipt(
            cluster=cluster,
            receipt_id=receipt_id,
            issued_at=issued_at,
            state_root=state_root,
            commit=commit,
            writer_principal=writer,
            replica_principal=replica,
            quorum_sigs=tuple(sigs),
            koe_id=koe_id,
        ),
    )
