"""A durable, cross-process file-backed FIFO event queue.

Why this exists
---------------
The webhook handler (``automation.webhooks``) and the scheduler
(``automation.scheduler``) run as *separate processes*. The previous design shared
an in-process ``queue.Queue()`` between them, which is unreachable across process
boundaries — so webhook events were enqueued into a queue that the scheduler could
never drain. Combined with the scheduler having had no entrypoint at all, this is
why nothing was ever processed (``metrics/automation-summary.yaml`` records
``runs_total: 0``).

This queue persists each event as one JSON file in a shared directory. A producer
(webhook) ``put()``s; a consumer (scheduler) ``get_nowait()``s the oldest file.
It is duck-type compatible with the ``queue.Queue`` surface the scheduler uses
(``put`` / ``get_nowait`` / ``empty`` / ``qsize``) so it is a drop-in replacement.

Scope / limits (honest)
-----------------------
File-backed sharing works when both processes see the same directory: a shared
volume (docker-compose) or the same host. For Kubernetes pods on different nodes,
the directory must be an RWX PersistentVolume, or a network broker (e.g. Redis)
backend should be used instead. That backend is intentionally NOT implemented here;
see the deployment notes.
"""

from __future__ import annotations

import json
import os
import queue
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict


def state_dir() -> Path:
    """Root writable state directory.

    Deployment MUST set ``SOCIOSPHERE_STATE_DIR`` to a durable, *shared* path (a
    mounted volume) so the webhook and scheduler processes see one queue. When it
    is unset (dev / tests / CI), fall back to a per-host temp directory that is
    always writable — so importing this module never fails on a read-only FHS path.
    """
    env = os.environ.get("SOCIOSPHERE_STATE_DIR")
    return Path(env) if env else Path(tempfile.gettempdir()) / "sociosphere-state"


def default_queue_dir() -> Path:
    """Shared event-queue directory (env ``SOCIOSPHERE_QUEUE_DIR``)."""
    env = os.environ.get("SOCIOSPHERE_QUEUE_DIR")
    return Path(env) if env else state_dir() / "queue"


class DurableQueue:
    """A minimal persistent FIFO backed by one JSON file per entry.

    Ordering is by filename, which is ``<monotonic-ns>-<uuid>.json`` so lexical
    sort == arrival order. Writes are atomic (temp file + ``os.rename``), so a
    crash mid-write never leaves a half-written entry visible to the consumer.
    """

    def __init__(self, directory: "os.PathLike[str] | str | None" = None) -> None:
        self.directory = Path(directory) if directory is not None else default_queue_dir()
        self.directory.mkdir(parents=True, exist_ok=True)

    # -- producer ------------------------------------------------------------
    def put(self, entry: Dict[str, Any]) -> str:
        """Persist *entry*; returns the queue-item id. Atomic and durable."""
        item_id = f"{time.monotonic_ns():020d}-{uuid.uuid4().hex}"
        target = self.directory / f"{item_id}.json"
        fd, tmp = tempfile.mkstemp(dir=self.directory, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(entry, fh, ensure_ascii=False)
                fh.flush()
                os.fsync(fh.fileno())
            os.rename(tmp, target)  # atomic within the same directory
        except BaseException:
            try:
                os.unlink(tmp)
            finally:
                raise
        return item_id

    # -- consumer ------------------------------------------------------------
    def _pending(self) -> list[Path]:
        return sorted(
            p for p in self.directory.glob("*.json") if not p.name.startswith(".tmp-")
        )

    def get_nowait(self) -> Dict[str, Any]:
        """Return and remove the oldest entry, or raise ``queue.Empty``.

        The file is claimed by renaming it out of the visible set first, so two
        consumers cannot process the same item. If claiming loses the race, we
        try the next file.
        """
        for path in self._pending():
            claim = path.with_suffix(".claimed")
            try:
                os.rename(path, claim)  # atomic claim; loser gets FileNotFoundError
            except FileNotFoundError:
                continue
            try:
                data = json.loads(claim.read_text(encoding="utf-8"))
            finally:
                claim.unlink(missing_ok=True)
            return data
        raise queue.Empty

    def empty(self) -> bool:
        return not self._pending()

    def qsize(self) -> int:
        return len(self._pending())

    def peek_all(self) -> list[Dict[str, Any]]:
        """Read every pending entry WITHOUT removing it (for telemetry / inspection).

        Non-destructive: unlike ``get_nowait`` it never claims a file, so a scraper can read
        the accumulated receipts while the queue keeps its contents. Entries removed or written
        concurrently are skipped rather than raising.
        """
        out: list[Dict[str, Any]] = []
        for path in self._pending():
            try:
                out.append(json.loads(path.read_text(encoding="utf-8")))
            except (FileNotFoundError, ValueError):
                continue
        return out
