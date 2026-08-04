# The shared reasoning runtime

`automation/reasoning/` is the **domain-agnostic core** of the self-heal loop, drawn out as a
stable, liftable surface. It is the running, fixture-tested reference implementation of the
graph-brain MLN / Debater 2.0 pattern — the thing both specs call for and say they lack
("wire a minimal reference implementation with fixture-based CI").

## Core vs. domain (the contract)

A **domain** supplies three things; the **runtime** provides everything else.

| A domain provides | The runtime provides |
|---|---|
| **Detectors** — callables that emit evidence-bearing beacons (`kind_class`, `system`, `evidence`, `detail`), stamped with the canonical envelope | Evidence composition per subject (`compose_evidence`), `meet(Law, ΣEvidence)` on the vendored kernel lattice (`decide_composed`) |
| **Executors** — callables keyed by `(kind_class, action)` that carry a decision out (verify + rollback) | Boundary/IRI fail-closed gates; the verdict→action mapping |
| **A policy** — `ResponsePolicy`, declared in a YAML and drift-guarded | Canonical envelope + EpistemicLevel grading (`stamp`, `epistemic_level_for`) |
| | Cooldown suppression (`Suppressor`), telemetry + alerting (`collect_metrics`, `alerts`), outcome-driven policy-demotion learning (`analyze_outcomes`) |

`tests/test_reasoning_core_decoupled.py` asserts — in a **fresh interpreter** — that importing
`automation.reasoning` pulls in **no** `automation.detectors` / `automation.executors` /
`engines` module. So the runtime is genuinely liftable into another repo the way
`third_party/procyber` (the kernel it delegates to) already is.

## How it maps to the canonical pattern

- **Detector → evidence predicate → MAP-threshold** (Debater2×MLN §9): `compose_evidence`
  sums evidence weights on the lattice; `decide_composed` thresholds the composite. Weak
  signals compose; the strictest class's Law fences the subject (contradiction tolerance).
- **The kernel** (`third_party/procyber.semantic`) is the typed MLN coordinate: verdict =
  weight sign, `BOTTOM` = the ZERO weight (abstention), `meet` = composition, `lift⊣ground` =
  the Galois weight-limit.
- **Canonical envelope + EpistemicLevel** (Stardust-successor / Debater 2.0 §5): every beacon
  and receipt carries `message_id`/`trace_id`/`span_id`/`content_sha256`, and every decision is
  graded `proved`/`bounded`/`empirical`/`synthetic`/`speculative`/`rejected`.
- **Longitudinal machinery** = the reliability twins of Debater's Drift Monitor / Bias
  Passports / small-N gasket — currently *quantized* (discrete lattice steps, static
  thresholds); the continuous-weight forms are the next convergence.

## What self-heal is, in these terms

The sociosphere self-heal loop is now **the first domain adapter** on this runtime: its
detectors (mirror-drift, vendored-graph, stale-vendor, workspace-lock, policy-violation,
build-failure) and executors (resync/reconcile/propose_pr/canary_fix/quarantine) plug into the
shared core. A future Debater 2.0 build supplies argument-hygiene detectors (LOGFALL/COGBIAS)
and counter-test executors against the **same** runtime.

## Still quantized / not yet lifted (honest)

The runtime lives *inside* `automation/` and is proven decoupled but not yet packaged for
cross-repo vendoring; the learning loop is discrete-lattice, not continuous-weight; and the
telemetry is produced but not yet scraped/routed (see the capability register's Deployment
reality section). These are the remaining convergence steps, not claims already met.
