"""Collect the k3s master triad's Lazerus receipts into the file the detector reads.

The macro-triad self-heal loop has three parts. Two are shipped: the ACTUATOR (#587 —
assess_triad + propose_state_failback) and the SENSE wiring (#588 —
detectors.detect_macro_triad_divergence, which reads ``status/lazerus-triad-receipts.json``).
This is the third: the COLLECTOR that produces that file.

Each k3s HA master writes its OWN Integrity Receipt independently (one file per master — a
master cannot write another's, mirroring the on-cluster reality). The collector fans those in,
LINTS each against the Lazerus token grammar (automation.lazerus.lint_receipt), and assembles
the well-formed ones into the single document the detector consumes. It is fail-closed and
honest: a malformed receipt is NOT silently included — it is dropped and recorded under
``rejected`` (so a masters-side bug is visible, not swallowed), and the detector then sees a
short quorum rather than a forged one.

What this does NOT do: mint the BLS ``quorum_sigs`` — that signing step is blocked on pinning
the Lazerus BLS ciphersuite (see source-os quorumd::verify_bls_quorum), the same deferral as
the on-device verifier. The collector aggregates and validates SHAPE; it never fabricates a
signature it cannot produce. Until real signed receipts flow, the assembled file simply won't
carry a signable quorum, and the detector stays dormant — wired, honest, not theatrical.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from automation.lazerus import lint_receipt


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def collect_receipts(
    master_receipt_paths: Iterable[Path],
    *,
    repo: str,
    quorum: int = 2,
    out_path: Optional[Path] = None,
) -> dict:
    """Fan in per-master receipt files -> the triad document the detector reads.

    Reads each path as one master's Integrity Receipt, lints it, and keeps only the well-formed
    receipts. Returns the assembled document ``{repo, quorum, receipts, rejected, collected_at}``;
    when ``out_path`` is given it is also written there (atomically, via a temp file + replace, so
    the detector never reads a half-written file). Fail-closed: an unreadable or malformed receipt
    is dropped and recorded under ``rejected`` with the reason, never included as if valid.
    """
    receipts: List[dict] = []
    rejected: List[dict] = []
    seen_masters: set = set()

    for p in master_receipt_paths:
        p = Path(p)
        try:
            raw = json.loads(p.read_text("utf-8"))
        except (FileNotFoundError, ValueError) as exc:
            rejected.append({"path": str(p), "reason": f"unreadable: {exc}"})
            continue
        res = lint_receipt(raw)
        if not res.ok:
            cid = raw.get("cluster") if isinstance(raw, dict) else None
            rejected.append({"path": str(p), "cluster": cid, "reason": "; ".join(res.errors)})
            continue
        cluster = res.receipt.cluster
        if cluster in seen_masters:
            # Two receipts claiming the same master identity — a master signs itself once per
            # round. Keep the first, reject the duplicate (a replayed/forked master must not
            # inflate its own weight in the quorum).
            rejected.append({"path": str(p), "cluster": cluster, "reason": "duplicate master in this round"})
            continue
        seen_masters.add(cluster)
        receipts.append(raw)

    doc = {
        "repo": repo,
        "quorum": quorum,
        "receipts": receipts,
        "rejected": rejected,
        "collected_at": _now(),
    }

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(out_path)  # atomic: the detector sees the old or new file, never a partial one

    return doc
