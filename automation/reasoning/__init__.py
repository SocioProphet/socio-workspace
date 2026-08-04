"""The shared reasoning runtime — the domain-agnostic core of the self-heal loop.

Convergence step 3. Steps 1–2 turned the self-heal loop into an instance of the graph-brain
MLN / Debater 2.0 pattern (evidence composition + MAP-threshold, canonical envelope +
EpistemicLevel). This package draws the boundary explicitly: everything re-exported here is
**domain-agnostic** — it knows nothing about mirror-drift, vendors, CI, or any sociosphere
detector/executor. A *domain* (self-heal, or a future Debater 2.0 build) supplies only:

  - DETECTORS: callables that emit evidence-bearing beacons (stamped via `stamp`);
  - EXECUTORS: callables keyed by (kind_class, action) that carry a decision out;
  - a POLICY (`ResponsePolicy`, declared + drift-guarded).

The runtime provides the rest: compose evidence per subject, `meet(Law, ΣEvidence)` on the
vendored kernel lattice, boundary/IRI gates, the canonical envelope + EpistemicLevel grading,
cooldown suppression, telemetry/alerting, and outcome-driven policy-demotion learning.

`tests/test_reasoning_core_decoupled.py` proves — in a fresh interpreter — that importing this
package pulls in NO sociosphere-specific detector/executor/engine module, so it is genuinely
liftable into another repo the way `third_party/procyber` (the kernel) already is.
"""

from __future__ import annotations

# --- provenance vocabulary ---------------------------------------------------
from automation.envelope import (
    EPISTEMIC_LEVELS,
    SCHEMA_VERSION,
    content_hash,
    epistemic_level_for,
    stamp,
    ulid,
)

# --- declared governance -----------------------------------------------------
from automation.policy import (
    ACTIONS,
    DEFAULT_POLICY,
    VERDICTS,
    ResponsePolicy,
    load_policy,
    policy_from_mapping,
    validate_policy,
)

# --- the decision engine (evidence -> composed -> meet(Law, Evidence) -> action) ---
from automation.responder import (
    boundary_breaches,
    compose_evidence,
    compute_iri,
    decide,
    decide_composed,
    effective_law,
    evidence_verdict,
    run_once,
)

# --- longitudinal machinery --------------------------------------------------
from automation.learning import analyze as analyze_outcomes
from automation.suppression import Suppressor, fingerprint
from automation.telemetry import alerts, collect as collect_metrics, render_prometheus

__all__ = [
    # envelope
    "stamp", "epistemic_level_for", "content_hash", "ulid",
    "EPISTEMIC_LEVELS", "SCHEMA_VERSION",
    # policy
    "ResponsePolicy", "DEFAULT_POLICY", "load_policy", "policy_from_mapping",
    "validate_policy", "VERDICTS", "ACTIONS",
    # decision engine
    "decide_composed", "decide", "compose_evidence", "effective_law",
    "evidence_verdict", "compute_iri", "boundary_breaches", "run_once",
    # longitudinal
    "Suppressor", "fingerprint", "collect_metrics", "render_prometheus",
    "alerts", "analyze_outcomes",
]
