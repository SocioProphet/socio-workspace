"""Drain recorded Crystal Atlas graph-upserts and POST them to the shared graph.

The self-heal daemon records `graph-upsert-request.v0` payloads to `state/graph-upserts/` with
NO credentials (`crystal_atlas.emit_graph_upsert`). This job runs WITH a token, drains them, and
POSTs each to the Crystal Atlas graph endpoint. Bounded retry + dead-letter — no silent infinite
retry. Same produce/deliver split as the propose_pr / proposal-opener pair; the live endpoint +
token are deploy config (`$CRYSTAL_ATLAS_GRAPH_UPSERT_URL`, `$CRYSTAL_ATLAS_TOKEN`).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, List, Optional

from automation.durable_queue import DurableQueue, state_dir

MAX_ATTEMPTS = 5
ENDPOINT_ENV = "CRYSTAL_ATLAS_GRAPH_UPSERT_URL"
TOKEN_ENV = "CRYSTAL_ATLAS_TOKEN"


def _http_post(upsert: dict) -> int:
    """Default poster: POST the upsert as JSON to the configured endpoint; returns HTTP status."""
    url = os.environ.get(ENDPOINT_ENV)
    if not url:
        raise RuntimeError(f"{ENDPOINT_ENV} not set")
    headers = {"Content-Type": "application/json"}
    token = os.environ.get(TOKEN_ENV)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(upsert).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def drain_and_post(*, upserts_dir: Optional[Path] = None, dead_letter_dir: Optional[Path] = None,
                   poster: Optional[Callable[[dict], int]] = None,
                   max_attempts: int = MAX_ATTEMPTS) -> List[dict]:
    """Drain graph-upserts and POST each; dead-letter after max_attempts. Returns per-item results."""
    poster = poster or _http_post
    q = DurableQueue(upserts_dir if upserts_dir is not None else state_dir() / "graph-upserts")
    dead = DurableQueue(dead_letter_dir if dead_letter_dir is not None else state_dir() / "graph-upserts-dead")

    batch: List[dict] = []
    while not q.empty():
        try:
            batch.append(q.get_nowait())
        except Exception:
            break

    results: List[dict] = []
    for upsert in batch:
        rec = {"tenant_id": upsert.get("tenant_id"), "claims": len(upsert.get("claims", [])),
               "attempts": 0, "posted": False, "dead_lettered": False}
        last_err = None
        for attempt in range(1, max_attempts + 1):
            rec["attempts"] = attempt
            try:
                status = int(poster(upsert))
                if 200 <= status < 300:
                    rec["posted"], rec["status"] = True, status
                    break
                last_err = f"HTTP {status}"
            except Exception as exc:
                last_err = str(exc)
        if not rec["posted"]:
            rec["dead_lettered"], rec["error"] = True, last_err
            dead.put({"upsert": upsert, "error": last_err})
        results.append(rec)
    return results


def main(argv: Optional[List[str]] = None) -> int:
    if not os.environ.get(ENDPOINT_ENV):
        # network-gated: no endpoint configured -> nothing to do, and NOT a failure.
        print(f"skip: {ENDPOINT_ENV} not set (no Crystal Atlas graph endpoint configured)")
        return 0
    results = drain_and_post()
    posted = sum(1 for r in results if r["posted"])
    dead = [r for r in results if r["dead_lettered"]]
    print(f"posted {posted}/{len(results)} graph-upsert(s); dead-lettered {len(dead)}")
    return 1 if dead else 0


if __name__ == "__main__":  # pragma: no cover - CLI glue
    raise SystemExit(main())
