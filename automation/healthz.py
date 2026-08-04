"""Liveness CLI for the scheduler daemon — exit 0 if alive, 1 if not.

Usage (e.g. as a Kubernetes exec liveness probe):

    python -m automation.healthz

Honest by construction: it checks that the daemon has written a *fresh* heartbeat
(see ``automation.liveness``), not merely that a module imports. Staleness bound is
``SOCIOSPHERE_HEARTBEAT_MAX_AGE`` seconds (default 180).
"""

from __future__ import annotations

import os
import sys

from automation.liveness import (
    DEFAULT_MAX_AGE_SECONDS,
    DEFAULT_PROGRESS_MAX_AGE_SECONDS,
    age_seconds,
    is_alive,
    progress_age_seconds,
)


def main(argv: "list[str] | None" = None) -> int:
    max_age = float(os.environ.get("SOCIOSPHERE_HEARTBEAT_MAX_AGE", DEFAULT_MAX_AGE_SECONDS))
    prog_max = float(os.environ.get("SOCIOSPHERE_PROGRESS_MAX_AGE", DEFAULT_PROGRESS_MAX_AGE_SECONDS))

    # 1. Is the daemon LOOP alive? (heartbeat) — a stalled/absent loop is dead.
    age = age_seconds()
    if not is_alive(max_age):
        if age is None:
            print("dead (no heartbeat: daemon has not started or never beat)", file=sys.stderr)
        else:
            print(f"dead (heartbeat age {age:.1f}s > {max_age:.0f}s: daemon stalled)", file=sys.stderr)
        return 1

    # 2. Is the core decision cycle actually WORKING? (progress) — a daemon that beats but whose
    #    responder job crashes every tick is alive-but-dead; report DEGRADED so the probe fails.
    prog = progress_age_seconds()
    if prog is None or prog > prog_max:
        detail = "never" if prog is None else f"{prog:.1f}s > {prog_max:.0f}s"
        print(f"degraded (heartbeat fresh but no decision-cycle progress in {detail}: "
              f"jobs are failing behind a live loop)", file=sys.stderr)
        return 1

    print(f"alive (heartbeat {age:.1f}s <= {max_age:.0f}s, progress {prog:.1f}s <= {prog_max:.0f}s)")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI glue
    raise SystemExit(main(sys.argv[1:]))
