"""Heartbeat-based liveness — an honest signal that the daemon is actually running.

The previous liveness probe was ``python -c "import automation.scheduler; print('ok')"``.
That passes whenever the module *imports*, regardless of whether any scheduler is
running — a control that cannot fail (green health, dead daemon). Here the running
daemon writes a heartbeat timestamp on every tick, and ``automation.healthz`` checks
that the heartbeat is *fresh*. A dead daemon stops beating, the heartbeat goes stale,
and the probe fails — which is the whole point of a liveness probe.
"""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

from automation.durable_queue import state_dir

# Default staleness bound: a heartbeat older than this means "not alive".
# Chosen well above a normal tick so a single slow cycle does not flap.
DEFAULT_MAX_AGE_SECONDS = 180.0

# The heartbeat says the daemon LOOP is turning; PROGRESS says the core decision cycle (the
# responder job) actually completed. A daemon whose every job crashes still beats — heartbeat
# fresh, no progress. Health degrades on stale progress, closing that residual "instruments lie"
# gap. The bound is longer than the 1-minute cycle so a couple slow ticks do not flap.
DEFAULT_PROGRESS_MAX_AGE_SECONDS = 300.0


def heartbeat_path() -> Path:
    env = os.environ.get("SOCIOSPHERE_HEARTBEAT_PATH")
    return Path(env) if env else state_dir() / "scheduler.heartbeat"


def progress_path() -> Path:
    env = os.environ.get("SOCIOSPHERE_PROGRESS_PATH")
    return Path(env) if env else state_dir() / "scheduler.progress"


def progress(path: "Path | None" = None) -> None:
    """Mark that the core decision cycle completed — call on responder-job success."""
    target = path or progress_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".pg-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(str(time.time()))
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        finally:
            raise


def progress_age_seconds(path: "Path | None" = None) -> "float | None":
    """Seconds since the last recorded progress, or None if there is none yet."""
    target = path or progress_path()
    try:
        written = float(target.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None
    return max(0.0, time.time() - written)


def beat(path: "Path | None" = None) -> None:
    """Write the current epoch seconds to the heartbeat file, atomically."""
    target = path or heartbeat_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".hb-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(str(time.time()))
            fh.flush()
            os.fsync(fh.fileno())
        os.rename(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        finally:
            raise


def age_seconds(path: "Path | None" = None) -> "float | None":
    """Seconds since the last heartbeat, or None if there is no heartbeat yet."""
    target = path or heartbeat_path()
    try:
        written = float(target.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None
    return max(0.0, time.time() - written)


def is_alive(max_age_seconds: float = DEFAULT_MAX_AGE_SECONDS, path: "Path | None" = None) -> bool:
    """True iff a heartbeat exists and is fresher than *max_age_seconds*."""
    age = age_seconds(path)
    return age is not None and age <= max_age_seconds
