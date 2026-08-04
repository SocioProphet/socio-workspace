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
| Honest liveness — heartbeat **+ progress** (`liveness.py`, `healthz.py`) | ✅ | ✅ compose + k8s probes | ✅ dead-daemon fails **and** alive-but-jobs-failing degrades | ✅ | `tests/test_liveness_healthz.py` |
| Real scheduler daemon (`scheduler.run`) | ✅ | ✅ `python -m automation.scheduler` | ✅ | ✅ (apscheduler-guarded) | `tests/test_scheduler_daemon.py` |
| Observe-and-beacon (`observe_and_beacon`) | ✅ | ✅ default handler | ✅ | ✅ | `tests/test_scheduler_daemon.py` |
| **Vendored semantic kernel** (`third_party/procyber/…`) | ✅ upstream | ✅ imported by responder | ✅ pin + tamper | ✅ | `tests/test_vendor_pin.py` |
| **Reasoned responder** (`responder.py`) | ✅ | ✅ scheduler `responder` job | ✅ act **and** refuse | ✅ | `tests/test_responder_integration.py` |
| Boundary fence (8 octonion axes) | ✅ | ✅ in `decide` | ✅ breach → human | ✅ | `test_boundary_breach_force_escalates…` |
| IRI / identity-risk gate | ✅ | ✅ in `decide` | ✅ high-IRI → human | ✅ | `test_high_iri_force_escalates` |
| Verdict = kernel `meet(Law, Evidence)` | ✅ | ✅ delegated, not reimplemented | ✅ equals kernel meet | ✅ | `test_verdict_is_the_vendored_kernel_meet` |
| **Evidence composition** (`decide_composed`, per-subject) | ✅ | ✅ `run_once` groups by subject | ✅ weak-compose **and** strict-Law fences | ✅ | `tests/test_evidence_composition.py` |
| **Canonical envelope + EpistemicLevel** (`envelope.py`) | ✅ | ✅ beacons + receipts stamped | ✅ trace propagates; graded by outcome | ✅ | `tests/test_envelope.py` |
| **Shared reasoning runtime** (`automation/reasoning/`) | ✅ | ✅ self-heal is its first adapter | ✅ decoupling proven in a fresh interpreter | ✅ | `tests/test_reasoning_core_decoupled.py` |
| **Crystal Atlas graph-upsert** (`crystal_atlas.py`) | ✅ | ✅ decision→claim+evidence, durable emit | ✅ conforms to vendored graph-upsert-request.v0 (jsonschema) | ✅ | `tests/test_crystal_atlas_conformance.py` |
| End-to-end inbox→responder→kernel→decisions | ✅ | ✅ | ✅ | ✅ | `test_end_to_end_inbox_to_decisions` |
| Responder canary (guaranteed in → provable verdict) | ✅ | ✅ | ✅ | ✅ | `test_canary_guaranteed_input…` |
| **Mirror-drift executor** (`executors.resync_mirror_drift`) | ✅ | ✅ scheduler runs `run_once(execute=True)` | ✅ heal **and** abort | ✅ | `tests/test_executor_integration.py` |
| Verify-the-artifact + rollback (executor) | ✅ | ✅ | ✅ corrupt source → good artifact preserved | ✅ | `test_resync_aborts_and_preserves…`, `test_verification_failure_after_write_rolls_back` |
| Live break→heal / break→abort | ✅ | ✅ | ✅ | ✅ | `test_resync_heals_drifted…`, `test_run_once_execute_escalates_when_executor_cannot_heal` |
| **Mirror-drift detector** (`detectors.detect_mirror_drift`) | ✅ | ✅ scheduler `detectors` job | ✅ evidence **and** warrantless-on-corrupt | ✅ | `tests/test_detector_integration.py` |
| **Full vertical slice** detect→decide→heal→verify | ✅ | ✅ | ✅ heal **and** escalate+preserve | ✅ | `test_full_loop_detect_decide_heal_verify`, `test_full_loop_corrupt_source_escalates_and_preserves` |
| **Generic reconciler** (`executors.reconcile`) | ✅ | ✅ both reconcilers use it | ✅ heal/noop/abort/rollback | ✅ | `tests/test_reconcile_generic.py` |
| **Vendored-graph slice** (detector+executor, real tools) | ✅ | ✅ scheduler jobs | ✅ live break→heal **and** break→escalate | ✅ | `tests/test_vendored_graph_slice.py` |
| **propose_pr executor** (`executors.propose_pr`) | ✅ | ✅ action-level dispatch | ✅ record/open **and** invalid→escalate | ✅ | `tests/test_propose_pr.py` |
| **Policy-bound governance** (`policy.ResponsePolicy`) | ✅ | ✅ daemon loads declared policy | ✅ governs decide **and** rejects invalid | ✅ | `tests/test_policy.py` |
| **stale_vendor detector** (`detectors.detect_stale_vendors`) | ✅ | ✅ scheduler `detectors` job | ✅ detect+escalate w/ report; waived not flagged | ✅ | `tests/test_stale_vendor_detector.py` |
| **Escalation suppression** (`suppression.Suppressor`) | ✅ | ✅ daemon passes to `run_once` | ✅ suppress within cooldown; re-arm after; durable | ✅ | `tests/test_suppression.py` |
| **quarantine executor** (`executors.quarantine`) | ✅ | ✅ action-level dispatch | ✅ isolate+record **and** subjectless→escalate | ✅ | `tests/test_canary_quarantine.py` |
| **canary_fix executor** (`executors.canary_fix`) | ✅ | ✅ action-level dispatch | ✅ canary-then-heal **and** failed-canary→untouched+escalate | ✅ | `tests/test_canary_quarantine.py` |
| **workspace-lock detector** (`detectors.detect_workspace_lock_drift`) | ✅ | ✅ scheduler `detectors` job (network-gated) | ✅ drift→propose; in-sync/no-resolver→none | ✅ | `tests/test_workspace_lock_detector.py` |
| **policy_violation detector** (`detectors.detect_policy_violations`) | ✅ | ✅ scheduler `detectors` job | ✅ blocking finding→quarantine; clean/no-report→none | ✅ | `tests/test_build_policy_detectors.py` |
| **build_failure detector** (`detectors.detect_build_failures`) | ✅ | ✅ scheduler `detectors` job (network-gated) | ✅ failed run→escalate; none/no-gh→none | ✅ | `tests/test_build_policy_detectors.py` |
| **Telemetry + alerting** (`telemetry.py`) | ✅ | ✅ scheduler `telemetry` job → metrics.prom + alert logs | ✅ alerts fire on real conditions **and** silent when clean | ✅ | `tests/test_telemetry.py` |
| **Learning recommendations** (`learning.py`) | ✅ | ✅ scheduler `learning` job (hourly, advisory) | ✅ demote on failures; none below-n/success/floor | ✅ | `tests/test_learning.py` |
| **k8s shared-state queue** (`deployment/kubernetes.yaml`) | ✅ | ✅ RWX volume in all 3 workloads | ✅ asserts PVC RWX + mounts + STATE_DIR | ✅ | `tests/test_k8s_shared_state.py` |
| **Deploy integrity** (image ships loop deps; `scheduler.preflight`) | ✅ | ✅ Dockerfile + fail-fast at boot | ✅ guard fires on the original broken image | ✅ | `tests/test_deploy_integrity.py` |

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

This whole path is **governed by a declared policy** (`registry/self-heal-policy.yaml`, code
default `policy.DEFAULT_POLICY`): per-class Law ceilings, the verdict→action map, the IRI block
threshold, and the boundary axes are declared, not hardcoded. It ships an **opinionated
default** so the loop is governed out of the box; ops tighten or relax a single class by editing
the YAML (a partial override merges over the default and is validated on load). A test asserts
the committed file equals the code default, so declared governance and the default cannot drift.

- **Law** = the ceiling a failure *class* may reach (a reversible re-sync may reach `sealed`;
  a cross-repo change caps at `weak`; a policy breach never auto-fixes).
- **Evidence** = the warrant strength on the beacon (fresh+reproducible+detector = `sealed`;
  detector only = `probable`; bare signal = `weak`; nothing = BOTTOM).
- The meet cannot exceed either arm — weak evidence can *never* be talked up into an auto-fix,
  and a low-trust failure class can *never* be auto-fixed however strong the evidence.

**Evidence is composed per SUBJECT, not per beacon** (the graph-brain MLN's MAP-threshold model,
quantized to the verdict lattice). `run_once` groups the drained beacons by `system` and
`decide_composed` decides each subject once over its composed signals: **weak signals compose**
(three weak reach `sealed`-strength where one would only `propose_pr`), and the **effective Law
is the `meet` (most restrictive) across the kinds present**, so a strict class fences the whole
subject — a `mirror_drift` (sealed) that is *also* a `policy_violation` (quarantine) can never
auto-fix. A single-signal subject reduces exactly to per-beacon `meet(Law, Evidence)`. This is
convergence step 1 toward the shared Debater 2.0 / MLN reasoning core.

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

1. **Detector breadth (SENSE) — complete.** Every policy class now has a detector:
   `mirror_drift`/`vendored_graph_drift` (auto-heal), `stale_vendor` (escalate w/ report),
   `workspace_lock_drift` (network-gated propose), `policy_violation` (source-exposure
   gate → quarantine), `build_failure` (network-gated failed-run → escalate). Every SENSE
   class flows end-to-end.
2. **Executor breadth (ACT) — complete.** Every action now has an executor: `auto_fix`
   (`resync`/`reconcile`), `propose_pr` (record; open via an injected credentialed opener),
   `canary_fix` (prove the mechanism on a guaranteed-input→provable-output canary, then apply;
   escalate if unproven), `quarantine` (isolate + record), and `block` (terminal — refusing is
   the action). No decision silently dead-ends: an executor that does not resolve escalates.
3. **Learning loop ↔ kernel — done (advisory).** `learning.py` observes per-class outcomes in
   the receipt stream and recommends DEMOTING a class's Law one step down the kernel verdict
   lattice when its fixes are not verifying (with a minimum-sample gate) — so a class that can't
   heal cleanly stops auto-acting and starts proposing/escalating. It learns only in the safe
   direction (never promotes) and never mutates governance: recommendations are recorded and
   logged for a human to apply by editing the declared policy. Auto-application is deliberately
   NOT wired — governance stays human-owned.
4. **Telemetry — PRODUCED, not yet OBSERVED (honest correction).** `telemetry.py` writes
   `state/metrics.prom` and logs alerts, and the CLI `--alerts` probe has teeth. But **nothing
   scrapes the metrics file and nothing routes the alert logs** — no Prometheus textfile
   collector / node_exporter sidecar, no Loki/Alertmanager wiring in the manifest. So today the
   signal is real but lands in the void. Done on the produce side; the observe/route side is open.
5. **Cross-pod queue in k8s — manifest fixed, not proven live.** `deployment/kubernetes.yaml`
   declares a ReadWriteMany `automation-state` PVC in all three workloads (asserted by
   `tests/test_k8s_shared_state.py`). But it is a *manifest*, not a running deployment — see the
   deployment-reality gaps below.

## Deployment reality (the honest, unglamorous part)

The reasoning core is real and connected to live estate state (`detect_stale_vendors()` flags 3
actual stale vendored deps right now). But being *tested green* is not being *running in the
estate*. Open, in order of how badly they bite:

- **No image build/push pipeline.** The manifest references `sociosphere/automation:latest`, but
  **no workflow builds or pushes that image**. Until it does, the manifest cannot deploy.
- **No running instance.** There is no evidence any `automation.scheduler`/`webhooks` daemon is
  deployed and beating. The loop is dormant code + a manifest, not a live control plane.
- **Liveness reflects job health — done.** `scheduler.preflight` crashes a *broken image* loudly
  at boot; and now the responder job records **progress** each cycle, so a daemon that beats but
  whose decision cycle crashes every tick reads **degraded** (`healthz` fails), not green — the
  residual "instruments lie" gap is closed (`tests/test_liveness_healthz.py`).
- **Metrics/alerts unobserved** (gap 4 above) — still open; routing to WordOps is the fix.

Each gap is a row that has not yet earned its rightmost column. When it does, it moves — and a
test moves with it. The `Deploy integrity` row above earned its column by *failing on the actual
broken image first*, then passing — a control proven to fire, not merely present.
