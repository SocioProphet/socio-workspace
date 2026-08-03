# Capability Register — semantic self-healing

The honest scoreboard for the autonomous-reliability capability. One row per capability, four
truth columns. A claim only counts in the rightmost column it can honestly reach.

- **BUILT** — code exists and has unit tests (works in isolation).
- **WIRED** — a real consumer calls it in the running system (composition, not an island).
- **TESTED×2** — verified with teeth in *both* directions: it acts when it must, and it
  refuses/escalates when it must.
- **ON CI** — the above runs on every push/PR (`validate.yml` → `pytest -q`), so a regression
  goes red instead of rotting silently.

> Discipline (estate maxims): *a control that never fires is suspect*; *instruments lie —
> verify the artifact, not the exit code*; *a canary is a guaranteed input proving a
> guaranteed output*. Every row below either meets these or is marked as not yet meeting them.

## Register

| Capability | BUILT | WIRED | TESTED×2 | ON CI | Evidence |
|---|:---:|:---:|:---:|:---:|---|
| Durable cross-process queue (`durable_queue.py`) | ✅ | ✅ webhooks + scheduler | ✅ | ✅ | `tests/test_durable_queue.py` |
| Honest liveness / heartbeat (`liveness.py`, `healthz.py`) | ✅ | ✅ compose + k8s probes | ✅ dead-daemon fails | ✅ | `tests/test_liveness_healthz.py` |
| Real scheduler daemon (`scheduler.run`) | ✅ | ✅ `python -m automation.scheduler` | ✅ | ✅ (apscheduler-guarded) | `tests/test_scheduler_daemon.py` |
| Observe-and-beacon (`observe_and_beacon`) | ✅ | ✅ default handler | ✅ | ✅ | `tests/test_scheduler_daemon.py` |
| **Vendored semantic kernel** (`third_party/procyber/…`) | ✅ upstream | ✅ imported by responder | ✅ pin + tamper | ✅ | `tests/test_vendor_pin.py` |
| **Reasoned responder** (`responder.py`) | ✅ | ✅ scheduler `responder` job | ✅ act **and** refuse | ✅ | `tests/test_responder_integration.py` |
| Boundary fence (8 octonion axes) | ✅ | ✅ in `decide` | ✅ breach → human | ✅ | `test_boundary_breach_force_escalates…` |
| IRI / identity-risk gate | ✅ | ✅ in `decide` | ✅ high-IRI → human | ✅ | `test_high_iri_force_escalates` |
| Verdict = kernel `meet(Law, Evidence)` | ✅ | ✅ delegated, not reimplemented | ✅ equals kernel meet | ✅ | `test_verdict_is_the_vendored_kernel_meet` |
| End-to-end inbox→responder→kernel→decisions | ✅ | ✅ | ✅ | ✅ | `test_end_to_end_inbox_to_decisions` |
| Responder canary (guaranteed in → provable verdict) | ✅ | ✅ | ✅ | ✅ | `test_canary_guaranteed_input…` |
| **Mirror-drift executor** (`executors.resync_mirror_drift`) | ✅ | ✅ scheduler runs `run_once(execute=True)` | ✅ heal **and** abort | ✅ | `tests/test_executor_integration.py` |
| Verify-the-artifact + rollback (executor) | ✅ | ✅ | ✅ corrupt source → good artifact preserved | ✅ | `test_resync_aborts_and_preserves…`, `test_verification_failure_after_write_rolls_back` |
| Live break→heal / break→abort | ✅ | ✅ | ✅ | ✅ | `test_resync_heals_drifted…`, `test_run_once_execute_escalates_when_executor_cannot_heal` |
| **Mirror-drift detector** (`detectors.detect_mirror_drift`) | ✅ | ✅ scheduler `detectors` job | ✅ evidence **and** warrantless-on-corrupt | ✅ | `tests/test_detector_integration.py` |
| **Full vertical slice** detect→decide→heal→verify | ✅ | ✅ | ✅ heal **and** escalate+preserve | ✅ | `test_full_loop_detect_decide_heal_verify`, `test_full_loop_corrupt_source_escalates_and_preserves` |
| **Generic reconciler** (`executors.reconcile`) | ✅ | ✅ both reconcilers use it | ✅ heal/noop/abort/rollback | ✅ | `tests/test_reconcile_generic.py` |
| **Vendored-graph slice** (detector+executor, real tools) | ✅ | ✅ scheduler jobs | ✅ live break→heal **and** break→escalate | ✅ | `tests/test_vendored_graph_slice.py` |

## What "integrated" means here (and what it did NOT mean before)

Before this change the kernel and the automation loop were **well-tested islands**: 388 unit
tests proved each piece worked in isolation, but *nothing consumed the kernel* — no non-test
code imported `procyber.semantic`, and the learning loop was disjoint from the reasoner. Green
tests, zero composition.

The responder is the first real consumer. It does not reimplement the verdict logic — it
delegates to the vendored kernel's `meet`, and `test_verdict_is_the_vendored_kernel_meet`
fails if that delegation is ever broken or forked. That is the integration contract: swap or
drift the kernel and CI goes red.

## The decision path (what the responder actually does)

```
beacon ─▶ boundary fence ─▶ IRI gate ─▶ meet(Law, Evidence) ─▶ action
             │ breach          │ ≥0.55        │
             ▼                  ▼              ├─ sealed    → auto_fix
          BOTTOM             BOTTOM            ├─ probable  → canary_fix
        (→ human)          (→ human)           ├─ weak      → propose_pr
                                               ├─ quarantine→ quarantine
                                               └─ refuse    → block
   no evidence anywhere on the path ─▶ BOTTOM (→ human, the consent-hole)
```

- **Law** = the ceiling a failure *class* may reach (a reversible re-sync may reach `sealed`;
  a cross-repo change caps at `weak`; a policy breach never auto-fixes).
- **Evidence** = the warrant strength on the beacon (fresh+reproducible+detector = `sealed`;
  detector only = `probable`; bare signal = `weak`; nothing = BOTTOM).
- The meet cannot exceed either arm — weak evidence can *never* be talked up into an auto-fix,
  and a low-trust failure class can *never* be auto-fixed however strong the evidence.

## The spine, and where it is whole

```
SENSE ─▶ BEACON ─▶ DECIDE ─▶ ACT ─▶ VERIFY ─▶ RECEIPT
 ✅(1)     ✅        ✅        ✅(1)    ✅         ✅
```

**Two** failure classes are now whole end-to-end — **mirror-drift** and the **vendored-artifact
graph** — both on one generic mechanism. `executors.reconcile(Reconciler)` is the reusable
shape ("a derived artifact drifted from its source; regenerate, then VERIFY, roll back on
failure"); a detector senses drift and emits an evidence-bearing beacon, the responder decides
`auto_fix` via the kernel `meet`, the reconciler regenerates, the checker re-verifies on disk,
and a receipt is recorded — with teeth both ways (a corrupt source of truth is escalated to a
human and the good artifact is preserved). The vendored-graph slice drives the *real* CLIs
(`check_vendored_artifact_graph.py`, `lift_vendor_freshness_to_graph.py`) as subprocesses and
verifies by re-running the check, never by trusting an exit code. Adding the Nth reconcilable
artifact is now a `Reconciler` registration plus a detector, not new verify/rollback code.
`(1)` on the spine now marks stages proven for **two** classes.

## Not yet on the board (honest gaps, ranked by leverage)

1. **Detector breadth beyond reconcilable artifacts (SENSE).** Two derived-artifact classes
   now self-heal on the generic reconciler. The remaining responder classes are a different
   shape — `build_failure` (observe CI), `stale_vendor` (cross-repo, caps at `propose_pr`),
   `policy_violation` — and have Law + evidence handling but no detector emits their beacons,
   so those decisions never fire. These need *action* machinery that does not yet exist
   (gap 2), so they are decision-only until paired with an executor.
2. **Executor breadth (ACT).** Only `auto_fix→resync_mirror_drift` is wired. `propose_pr`
   (open a PR), `canary_fix` (canary then apply), and `quarantine` (isolate) are decided but
   not carried out — those receipts are decisions, not yet remediations.
3. **Learning loop ↔ kernel.** `lawful_learning/loop.py` is validated but disjoint from the
   responder. It becomes meaningful now that the slice produces a real receipt stream to learn
   from — improve Law/threshold choices from observed outcomes.
4. **Telemetry / alerting.** Receipts land in `state/decisions/` as files; no Prometheus/Loki
   consumer or alert on escalations. We can heal silently but cannot yet *observe* healing.
5. **Cross-pod queue in k8s.** Compose shares state via a volume; the k8s manifest still needs
   an RWX PV or a Redis backend for the webhook and scheduler pods to share the queue. Required
   to *deploy* multi-pod, not to *prove* the loop.

Each gap is a row that has not yet earned its rightmost column. When it does, it moves — and a
test moves with it.
