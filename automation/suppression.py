"""Escalation suppression: decide a persistent condition once per window, not every cycle.

Detectors run every scheduler tick. A self-healing condition (mirror-drift, vendored-graph)
disappears once healed, so it never repeats. But a condition whose fix is NOT local — a stale
cross-repo vendor — is re-observed on every tick, and without suppression the daemon would
escalate the same thing every minute.

A beacon's FINGERPRINT identifies the condition (kind_class + system), not the observation
(timestamps, run ids are excluded). The `Suppressor` records, durably, when each fingerprint
was last decided; within the policy cooldown it reports the condition as already handled so the
responder skips it. Past the window it reports handled again and re-arms — so a still-open
condition is re-surfaced periodically, never silenced forever.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Optional


def fingerprint(beacon: dict) -> str:
    """Stable identity of the CONDITION a beacon reports (not the observation).

    kind_class + system is the identity: `system` already encodes the specific subject
    (e.g. `vendored:<artifact_id>`), and observation-varying fields (observed_at, run ids)
    are deliberately excluded so repeated observations of one condition collide.
    """
    kind = str(beacon.get("kind_class", "unknown"))
    system = str(beacon.get("system", ""))
    return f"{kind}::{system}"


class Suppressor:
    """Durable last-decided-at store, keyed by fingerprint, for cooldown suppression."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _load(self) -> dict:
        try:
            data = json.loads(self.path.read_text("utf-8"))
            return data if isinstance(data, dict) else {}
        except (FileNotFoundError, ValueError):
            return {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(self.path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, sort_keys=True)
            os.replace(tmp, self.path)  # atomic
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def should_process(self, fp: str, *, cooldown_seconds: float,
                       now: Optional[float] = None) -> bool:
        """True if this condition should be decided now; records the decision time when so.

        A cooldown of 0 always processes (suppression disabled). last-decided is updated ONLY
        when returning True, so repeated suppressed hits never extend the window.
        """
        if cooldown_seconds <= 0:
            return True
        now = time.time() if now is None else now
        data = self._load()
        last = data.get(fp)
        if isinstance(last, (int, float)) and (now - last) < cooldown_seconds:
            return False
        data[fp] = now
        self._save(data)
        return True
