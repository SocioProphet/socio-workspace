#!/usr/bin/env python3
"""GBRG governance ledger — the DURABLE, append-only sink for inclusion decisions.

agent-registry's ``authorize.py`` *emits* a hashed decision receipt but is
explicitly read-only: it does **not** persist. ("It does not mutate authority …"
— see authorize.py NON_GOALS.) Persistence of every context inclusion/exclusion
decision — allow AND deny — is therefore GBRG's responsibility. This module is
that sink.

"No invisible authority": every decision to admit or refuse a cell into a review
context is written here as one JSONL line, each line carrying the sha256 receipt
computed over its canonical decision core. The ledger is append-only (opened in
``"a"`` mode, never truncated) so the record of what authority did is durable and
replayable.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterator

# Default durable sink location: gbrg/governance/ledger/decisions.jsonl
LEDGER_DIR = Path(__file__).resolve().parent / "ledger"
DEFAULT_LEDGER = LEDGER_DIR / "decisions.jsonl"


def append(record: dict[str, Any], *, ledger_path: Path | str | None = None) -> Path:
    """Append one decision record as a single JSONL line. Returns the ledger path.

    Append-only by construction: the file is opened in ``"a"`` mode and flushed +
    fsync'd so the durable record survives a crash. The record is expected to
    already carry its ``receipt`` (sha256 over the canonical core); we never
    rewrite or reorder existing lines.
    """
    path = Path(ledger_path) if ledger_path is not None else DEFAULT_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return path


def read_all(ledger_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Read every decision record back from the ledger (empty list if absent)."""
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


def iter_receipts(ledger_path: Path | str | None = None) -> Iterator[str]:
    """Yield the sha256 receipt of every persisted decision, in append order."""
    for record in read_all(ledger_path):
        yield record["receipt"]
