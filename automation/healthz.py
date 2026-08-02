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

from automation.liveness import DEFAULT_MAX_AGE_SECONDS, age_seconds, is_alive


def main(argv: "list[str] | None" = None) -> int:
    max_age = float(os.environ.get("SOCIOSPHERE_HEARTBEAT_MAX_AGE", DEFAULT_MAX_AGE_SECONDS))
    age = age_seconds()
    if is_alive(max_age):
        print(f"alive (heartbeat age {age:.1f}s <= {max_age:.0f}s)")
        return 0
    if age is None:
        print("dead (no heartbeat: daemon has not started or never beat)", file=sys.stderr)
    else:
        print(f"dead (heartbeat age {age:.1f}s > {max_age:.0f}s: daemon stalled)", file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover - CLI glue
    raise SystemExit(main(sys.argv[1:]))
