# Design note — the Reasoned Responder (closing sociosphere's self-heal loop)

Status: DESIGN v0.1 · Scope: `automation/` responder + a vendored kernel dependency
Companion to: `fix/automation-real-daemon-honest-liveness` (Tier 1)

## 0 · The gap this closes

After Tier 1 the loop runs and is honest, but it is still **open**:

```
detect (validators / drift / webhook)  →  emit beacon (state/beacons/*.json)  →  (nobody)
```

`observe_and_beacon` deliberately takes no world-action, because *choosing* the action
is the hard part sociosphere has never had: **a reasoned responder** that, given a
failure beacon, decides `auto-fix ∣ alert ∣ escalate ∣ withhold`. Today that decision is
either a static keyword lookup (`_classify_change`) or a human review queue. This note
specifies the responder and binds it to a reasoning kernel rather than more static rules.

## 1 · The pipeline

```
beacon  ──►  Observation  ──►  meet(Law, Evidence)  ──►  verdict  ──►  gated action
              (typed)          (verdict lattice)         ∈ 5 levels     (+ rollback)
                                   │
                    IRI / daat safety gate  ──►  octonion boundary fence
```

A responder process (a scheduler job, or a small daemon) drains `state/beacons/` — the
`DurableQueue` inbox Tier 1 already writes to — and for each beacon runs the decision
below. No new transport is needed; the inbox exists.

## 2 · The reasoner is the semantic kernel (`procyber.semantic`)

This is the first real **consumer** of the sovereign kernel (ProCybernetica), closing the
"shipped library, not yet used" gap. The mapping is one-to-one:

- **Observation.** Each beacon becomes a `SemanticAddress`: `term` = the failure *kind*
  (drift / stale-vendor / build-fail / policy-violation …), `iri` = the affected system,
  `warrant` = the evidence (which detector, telemetry, provenance). A beacon with
  insufficient evidence addresses to **`BOTTOM`** (a consent-hole): the responder may ask,
  it may not guess.
- **Law × Evidence.** The verdict is `meet(law, evidence)` on the kernel's verdict lattice
  `{refuse < quarantine < weak < probable < sealed}` (`Truth = Law × Evidence`, `×=MEET`).
  *Law* is the policy: what class of failure is permitted to auto-remediate at all (the
  `pullback` onto the allowed-action cone). *Evidence* is the beacon's warrant strength.
  The meet cannot exceed either — you cannot `sealed`-auto-fix on `weak` evidence.
- **Verdict → action** (the fix-vs-alert-vs-escalate chooser sociosphere lacks):

  | verdict | action |
  |---|---|
  | `sealed` | auto-remediate (execute the playbook), rollback armed |
  | `probable` | auto-remediate **behind a canary/rollback**, record receipt |
  | `weak` | do **not** act — open a proposal PR + alert; await human |
  | `quarantine` | isolate the affected unit, page on-call, no fix |
  | `refuse` | block + page; the action is not permitted here |
  | **`BOTTOM`** | route to the human governance queue (the consent-hole) |

## 3 · The two safety gates (a verdict is necessary, not sufficient)

1. **IRI / daat gate.** Even a `sealed` verdict is refused auto-action when the **Identity
   Risk Index** (α·EntropyUniqueness + β·InjectionNormativity − γ·ConsentHoleCredits, from
   the Boundary SPEC) is above the block threshold — i.e. when the disposition is far from
   the identity (`daat` large). High IRI ⇒ escalate to human regardless of verdict. This is
   the "share iff at identity" rule applied to *acting on the world*.
2. **Octonion boundary fence.** From Ring-1's eight non-negotiable axes — legality,
   containment, provenance, privacy, performance, reproducibility, licensing, governance —
   **no auto-action may cross a boundary norm ‖b‖ ≥ 1.** Any remediation whose plan touches
   a boundary axis (e.g. would open egress, or act without provenance) is force-escalated,
   never auto-executed. This is the "never auto-act across this line" fence.

Order of evaluation is fixed and fail-closed: `boundary → IRI → verdict → action`. Any
gate that cannot be evaluated ⇒ `BOTTOM` ⇒ human.

## 4 · Failure-mode → playbook binding

The existing runbooks (`docs/runbooks/*`) are prose. This responder gives each failure
mode an **executable playbook** *plus* a reasoned *selector*: the mode is detected, the
verdict + gates choose whether and how to run its playbook. Playbooks are the existing
remediation primitives, now invoked under a decision instead of ad hoc:

- **mirror drift `behind`** → re-sync playbook (currently `mirror_drift_engine` only
  records; the playbook is the `--write` re-sync, gated by verdict).
- **stale vendored dep** → the re-vendor plan (`vendor-freshness-detect` already emits it);
  the responder is the missing executor, gated + rollback-armed.
- **propagation cascade** → the real `PropagationHandler.rollback` path, invoked only on a
  `sealed`/`probable` verdict inside the boundary fence (never unconditionally).

## 5 · Teeth (proof obligations, both ways)

The responder is itself a control, so it must be shown to *refuse*, not only to act:

- a beacon with weak evidence must be **shown** to produce `weak`/`BOTTOM` → no auto-fix;
- a beacon crossing a boundary axis must be **shown** to force-escalate even at `sealed`;
- a high-IRI beacon must be **shown** to escalate even at `sealed`;
- and at least one honest `sealed`+low-IRI+in-bounds case must auto-remediate — a responder
  that never acts is as suspect as one that always acts.

## 6 · What this is not (honest scope)

- It does **not** grant sociosphere new credentials. Where the fix is cross-repo (the
  vendor-freshness executor), the responder emits a *decided, signed plan*; the consumer
  repo still opens the PR with its own token. The reasoning is centralized; the authority
  is not.
- It does **not** replace human governance. `BOTTOM` and boundary/IRI escalations route to
  the existing agent-reliability queue — the responder decides *when* a human is required,
  it does not remove them.
- The kernel dependency is **vendored, pinned** (`procyber.semantic`, SPEC_VERSION), not
  forked — consistent with the estate's derived-not-authored discipline.

## 7 · Build order

1. Vendor `procyber.semantic` into sociosphere (pinned) — the first consumer.
2. `automation/responder.py`: drain `state/beacons/`, build the `SemanticAddress`, evaluate
   `boundary → IRI → meet → action`, emit a decision receipt to `state/decisions/`.
3. Wire the responder as a scheduler job (it now has a real daemon to host it).
4. Bind three playbooks (drift re-sync, re-vendor plan, propagation rollback) behind the
   decision, each with the both-ways tests of §5.
5. Only then remove `observe_and_beacon`'s "deferred" default.

## v0.1.1 — closing the loop: recorded proposal → opened fix PR

The responder decides `propose_pr` and records a proposal, but recording is not
remediation until a PR actually exists. The credential split makes that safe:

- **The daemon has no credentials.** `propose_pr` durably records the proposal
  (branch, base, files, title, body, provenance) to the state volume and returns
  `proposed: true`. It never touches a remote.
- **A credentialed CronJob opens it.** `automation.open_recorded_proposals` drains
  recorded proposals and, for each, checks out the target repo and calls
  `automation.pr_opener.open_pr` — create branch from base, write the proposed
  files, commit, push `--force-with-lease`, `gh pr create`. It **opens, never
  merges**, so every self-healed change still passes human review, and the
  CI-workflow / token-change review guardrail is never bypassed.

Properties:

- **Fail-closed.** Any git/gh non-zero exit raises; a partial push never reports
  success. A proposal whose files escape the repo, or that is malformed, is rejected.
- **Idempotent.** Re-running reuses an existing open PR for the branch and rewrites
  the same files — the same proposal converges on one PR.
- **Bounded retry, then dead-letter.** A transient failure is re-queued for the next
  run; after `MAX_ATTEMPTS` it moves to a dead-letter queue and the run fails loudly.
  This is the deliberate refusal of the "retry masquerades as a fix" trap — a proposal
  can never silently retry forever while looking healthy.

This is what makes *"the next red opens its own fix PR"* real: a detected failure
becomes a beacon, the responder reasons a verdict, and — for classes it caps at
`propose_pr` — a reviewable fix PR appears, on a human's desk, with provenance.

Remaining wiring: the per-class **beacon producers** that turn a specific CI-red
shape (name/version drift, moving-tag, lockfile break, layout) into a proposal with
a concrete patch. The mechanism is now in place for them to target.

## v0.1.2 — one sealed control model (synthesis of the two self-heal arms)

Two arms grew in parallel: **ControlLoop** (bounded/convergent/fail-closed,
verify-by-re-observe, sealed trace) and the **PR opener** (real actuation,
credential-split, dead-letter). Rather than pick one, `automation/self_heal.py`
composes them on a single insight:

> **Opening a reviewable fix PR *is* convergence** — the target is "a remediation
> the system cannot apply autonomously now exists on a human's desk."

So both remediation modes are the *same* loop with different invariants:

| action | invariant (error → 0) | converged means | not converged → |
|---|---|---|---|
| `auto_fix` | the artifact is in sync | healed in place | `quarantine-escalate` |
| `propose_pr` | a reviewable PR exists | PR opened for review | fail-close to human (carrying the PR if one was opened) |

`remediate(beacon, receipt, …)` routes to the right invariant and **always returns one
sealed `LoopResult`** (`trace_hash` provenance) — the responder, the daemon, and the
audit trail speak one language. Genes kept from each arm: ControlLoop's verify-by-
re-observe + seal; the opener's real actuation and fail-closed-*with-the-error-detail*
(the loop swallows-and-re-observes, but the operator still gets the reason). The drainer
now runs every proposal through this model, so each opened PR carries a sealed trace.
