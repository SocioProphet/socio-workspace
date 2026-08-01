#!/usr/bin/env python3
"""GBRG governance ledger — the DURABLE, append-only, VERIFIED sink for decisions.

agent-registry's ``authorize.py`` *emits* a hashed decision receipt but is
explicitly read-only: it does **not** persist. ("It does not mutate authority …"
— see authorize.py NON_GOALS.) Persistence of every context inclusion/exclusion
decision — allow AND deny — is therefore GBRG's responsibility. This module is
that sink.

"No invisible authority": every decision to admit or refuse a cell into a review
context is written here as one JSONL line, each line carrying its own sha256
seal computed over its canonical content. The ledger is append-only (opened in
``"a"`` mode, never truncated).

Two record shapes are written into ledger files by two single-writer producers:

  * governance DECISION records (``gate.Decision``) carry a ``receipt`` — a
    sha256 over the decision ``core`` (:func:`gate.recompute_receipt`). These are
    RECEIPT-SEALED: each record proves its own content is intact.
  * MCP ledger EVENTS (``mcp_gate.emit_event``) additionally carry ``hash`` and
    ``prev_hash`` — a GENESIS-anchored HASH-CHAIN. These are chain-sealed: each
    record proves its content AND its position/predecessor.

TAMPER-EVIDENCE IS ENFORCED, NOT COSMETIC. :func:`verify_ledger` recomputes every
record's seal and walks the ``prev_hash`` chain from :data:`GENESIS`, failing on
the first bad seal, broken link, reorder, insertion, or deletion. The public read
paths (:func:`read_all`, :func:`iter_receipts`, :func:`read_verified`) verify
BEFORE returning and raise :class:`LedgerTamperError` on any break — callers never
silently trust the file on disk.

RESIDUAL (stated honestly): verification proves internal integrity. A determined
attacker with write access who rebuilds the ENTIRE file as a fresh, internally
consistent chain from GENESIS produces a ledger that :func:`verify_ledger` reports
as internally ``ok`` — because it is. Detecting that whole-file substitution
requires an OUT-OF-BAND anchor: pin the expected head hash somewhere the attacker
cannot also rewrite and compare it against ``VerifyResult.head`` (see
:func:`verify_head`). Chain-order tampers (reorder/insert/delete) and per-record
content tampers ARE detected without any anchor.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

# Default durable sink location: gbrg/governance/ledger/decisions.jsonl
LEDGER_DIR = Path(__file__).resolve().parent / "ledger"
DEFAULT_LEDGER = LEDGER_DIR / "decisions.jsonl"

# Canonical chain anchor. The first hash-chained event's ``prev_hash`` MUST equal
# this. Kept identical to the value the MCP writer used historically so existing
# chains verify. Single source of truth — mcp_gate imports it from here.
GENESIS = "sha256:" + hashlib.sha256(b"gbrg-mcp-ledger-genesis").hexdigest()


class LedgerTamperError(RuntimeError):
    """Raised by the verified read paths when the ledger fails verification."""


def _canonical(obj: Any) -> str:
    """Canonical JSON — sorted keys, tight separators — matching every writer."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def _sha(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()


def append(record: dict[str, Any], *, ledger_path: Path | str | None = None) -> Path:
    """Append one decision record as a single JSONL line. Returns the ledger path.

    Append-only by construction: the file is opened in ``"a"`` mode and flushed +
    fsync'd so the durable record survives a crash. The record is expected to
    already carry its seal (``receipt`` for governance decisions, ``hash`` +
    ``prev_hash`` for chained MCP events); we never rewrite or reorder lines.
    """
    path = Path(ledger_path) if ledger_path is not None else DEFAULT_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return path


def _read_raw(ledger_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Parse every JSONL record WITHOUT verification (empty list if absent).

    Low-level reader used by :func:`verify_ledger` itself and by the writer to
    compute the next ``prev_hash``. Application code should prefer the verified
    read paths (:func:`read_all` / :func:`read_verified` / :func:`iter_receipts`).
    """
    path = Path(ledger_path) if ledger_path is not None else DEFAULT_LEDGER
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# --------------------------------------------------------------------------- #
# Verification — the enforced tamper-evidence.
# --------------------------------------------------------------------------- #
@dataclass
class VerifyResult:
    """Typed outcome of :func:`verify_ledger`.

    ok=True  -> ``head`` is the seal (chain head hash, or last receipt) of the
                verified ledger; ``broken_index``/``reason`` are None.
    ok=False -> ``broken_index`` is the 0-based index of the FIRST record that
                failed and ``reason`` explains why; ``head`` is None.
    """

    ok: bool
    records: int
    head: str | None = None
    broken_index: int | None = None
    reason: str | None = None


def _recompute_event_hash(record: dict[str, Any]) -> str:
    """Recompute a chained MCP event's ``hash`` over its core (everything but hash)."""
    core = {k: v for k, v in record.items() if k != "hash"}
    return _sha(core)


def verify_ledger(
    ledger_path: Path | str | None = None,
    *,
    genesis: str = GENESIS,
) -> VerifyResult:
    """Verify the WHOLE ledger file. Recompute every seal, walk the chain.

    For each record, in file order:
      * chained MCP event (has ``hash`` + ``prev_hash``): its ``prev_hash`` must
        equal the running chain head (``genesis`` for the first chained record,
        else the previous event's ``hash``), and its ``hash`` must recompute from
        its core. A reorder, insertion, or deletion breaks a ``prev_hash`` link;
        a content edit breaks the recomputed ``hash``.
      * governance decision (has ``receipt``): its ``receipt`` must recompute from
        the decision core (:func:`gate.recompute_receipt`). Receipt-sealed but not
        chain-ordered (see module RESIDUAL).
      * anything else: unknown record type -> fail.

    FAILS on the FIRST break, returning its index + reason. Never raises for a
    tampered file (that is a verification *result*, ok=False, not an error); only
    genuinely malformed JSON would surface from the raw read.
    """
    records = _read_raw(ledger_path)
    chain_head = genesis
    last_seal: str | None = None

    for i, rec in enumerate(records):
        if "hash" in rec and "prev_hash" in rec:
            if rec["prev_hash"] != chain_head:
                return VerifyResult(
                    ok=False,
                    records=len(records),
                    broken_index=i,
                    reason=(
                        f"broken chain link at index {i}: prev_hash="
                        f"{rec['prev_hash']!r} != expected {chain_head!r} "
                        "(reorder / insertion / deletion / wrong genesis)"
                    ),
                )
            recomputed = _recompute_event_hash(rec)
            if recomputed != rec["hash"]:
                return VerifyResult(
                    ok=False,
                    records=len(records),
                    broken_index=i,
                    reason=(
                        f"bad event hash at index {i}: recomputed {recomputed} "
                        f"!= stored {rec['hash']} (record content was altered)"
                    ),
                )
            chain_head = rec["hash"]
            last_seal = rec["hash"]
        elif "receipt" in rec:
            # Lazy import avoids a load-time cycle (gate imports ledger).
            from . import gate  # noqa: PLC0415

            try:
                recomputed = gate.recompute_receipt(rec)
            except (KeyError, TypeError) as exc:
                return VerifyResult(
                    ok=False,
                    records=len(records),
                    broken_index=i,
                    reason=f"undecodable decision record at index {i}: {exc}",
                )
            if recomputed != rec["receipt"]:
                return VerifyResult(
                    ok=False,
                    records=len(records),
                    broken_index=i,
                    reason=(
                        f"bad decision receipt at index {i}: recomputed {recomputed} "
                        f"!= stored {rec['receipt']} (record content was altered)"
                    ),
                )
            last_seal = rec["receipt"]
        else:
            return VerifyResult(
                ok=False,
                records=len(records),
                broken_index=i,
                reason=f"unknown record type at index {i} (no 'hash'/'prev_hash' or 'receipt')",
            )

    return VerifyResult(ok=True, records=len(records), head=last_seal)


def verify_head(
    ledger_path: Path | str | None = None,
    *,
    expected_head: str,
    genesis: str = GENESIS,
) -> VerifyResult:
    """Verify internal integrity AND that the head matches an OUT-OF-BAND anchor.

    Closes the whole-file-substitution residual: even a fresh, internally
    consistent chain rebuilt from GENESIS is rejected unless its head equals the
    ``expected_head`` you pinned somewhere the writer cannot reach.
    """
    result = verify_ledger(ledger_path, genesis=genesis)
    if not result.ok:
        return result
    if result.head != expected_head:
        return VerifyResult(
            ok=False,
            records=result.records,
            broken_index=None,
            reason=(
                f"head anchor mismatch: verified head {result.head!r} != "
                f"expected {expected_head!r} (whole-file substitution / rollback)"
            ),
        )
    return result


# --------------------------------------------------------------------------- #
# Verified read paths — do not silently trust the file.
# --------------------------------------------------------------------------- #
def read_verified(ledger_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Verify the chain, then return every record. Raise on tamper.

    :raises LedgerTamperError: if :func:`verify_ledger` reports any break.
    """
    result = verify_ledger(ledger_path)
    if not result.ok:
        raise LedgerTamperError(
            f"ledger verification FAILED at index {result.broken_index}: {result.reason}"
        )
    return _read_raw(ledger_path)


def read_all(
    ledger_path: Path | str | None = None, *, verify: bool = True
) -> list[dict[str, Any]]:
    """Read every decision record back from the ledger (empty list if absent).

    Verifies the chain first by default (``verify=True``) and raises
    :class:`LedgerTamperError` on tamper — the read path does NOT silently trust
    the file. Pass ``verify=False`` only for the low-level raw read used while
    computing the next chain link.
    """
    if verify:
        return read_verified(ledger_path)
    return _read_raw(ledger_path)


def iter_receipts(ledger_path: Path | str | None = None) -> Iterator[str]:
    """Yield the seal (``receipt`` or chained ``hash``) of every persisted record.

    Verifies the chain before yielding anything (raises
    :class:`LedgerTamperError` on tamper). Tolerates BOTH record shapes: governance
    decisions expose ``receipt``, MCP events expose ``hash`` (L7 fix — the previous
    ``record["receipt"]`` crashed on chained events, and ``_prev_hash``'s
    ``record["hash"]`` crashed on decisions). Single-writer-per-file remains the
    intended invariant; verification just no longer assumes it.
    """
    for record in read_verified(ledger_path):
        seal = record.get("receipt") or record.get("hash")
        if seal is not None:
            yield seal
