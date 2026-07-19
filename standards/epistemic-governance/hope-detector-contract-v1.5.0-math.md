# HOPE ↔ Detector Contract v1.5.0-math

Status: draft extension  
Owner: SocioSphere  
Scope: cross-repo hypothesis evaluation, detector invocation, LR contribution, reversibility, replay, and audit contracts  
Non-scope: downstream detector implementation, model internals, private tenant data, product-specific UI implementation, and runtime deployment

## Purpose

This document registers the HOPE ↔ Detector contract as a SocioSphere Epistemic Governance extension.

A `hyp:HypothesisRun` evaluates a pre-registered hypothesis against an explicit negation, invokes governed detector and counter-test workloads under capability scope, converts calibrated detector outputs into hypothesis-family-specific likelihood-ratio contributions, and publishes a reversibility report that can be audited, appealed, and replayed.

The contract upgrades the current Epistemic Governance detector/counter-test standard from argument-hygiene signaling into a full hypothesis-evaluation path without changing the core rule that detector findings are hypotheses rather than verdicts.

## Relationship to existing SocioSphere standards

This contract composes existing SocioSphere standards rather than replacing them.

| Existing surface | Role in this contract |
|---|---|
| `standards/epistemic-governance/` | Claim, detector, counter-test, repair, appeal, promotion, and reversal law. |
| `protocol/epistemic-governance/v1/` | Topic identity, fixture contract, replay expectations, and compatibility policy. |
| `standards/qes/` | Event, run, evidence, provenance, deterministic replay, and topic discipline. |
| `standards/proof-apparatus/` | Claim-boundary, non-claim, gate, promotion, and obstruction discipline. |
| `standards/source-exposure/` | Public/restricted publication and export safety discipline. |
| `standards/angel-of-the-lord/` | Adversarial hardening posture and evidence-gap critique. |
| `protocol/agentic-workbench/v1/` | Governed workflow, artifact, approval, policy-pack, trust-profile, and execution-envelope shape. |

## Canonical object kinds

The controller recognizes these object kinds for HOPE v1.5.0-math.

| Object | Meaning |
|---|---|
| `hyp:HypothesisRun` | Pre-registered hypothesis evaluation run with explicit negation, time window, requested detectors, requested spheres, model version, and thresholds. |
| `tm:CapabilityToken` | Signed authority artifact binding a HOPE runner to detector workloads, sphere versions, policy hash, attestation digests, export obligations, and reversibility commitments. |
| `ds:DetectorEvent` | Single detector invocation result with raw score, calibrated probability, calibration sphere, counter-test outcomes, joint-inference data, severity decision, provenance, and privacy metadata. |
| `hyp:EvidenceContribution` | HOPE-level transformation of a detector event into a log-likelihood-ratio contribution for a specific hypothesis family. |
| `ds:LRCalibrationArtifact` | Content-addressed calibration map from detector probability to family-specific likelihood ratio, including uncertainty, corpus size, ECE, Brier score, and training attestation. |
| `hyp:ReversibilityReport` | Mandatory publication artifact disclosing run provenance, decision rule, evidence summary, reversibility distance, minimal counter-evidence set, top evidence, small-N flags, joint inference, fairness/calibration, governance compliance, notarization, and appeal channel. |
| `exp:ExportReceipt` | Guard-produced receipt proving redaction, privacy-tier, differential-privacy, and egress obligations were applied before cross-sphere export. |

## Mandatory invariants

A conforming HOPE ↔ Detector run must satisfy all invariants below.

1. **Explicit negation.** `H` and `not-H` are both supplied by the requester and hashed independently. The negation is not inferred by the system.
2. **Frozen thresholds.** `tau_accept_log_lr` and `tau_reject_log_lr` are frozen at pre-registration. Changes create a new run ID.
3. **Policy pin.** Every run, token, detector event, contribution, report, export receipt, and policy decision cites the same `policy_hash` unless a policy update creates a new run.
4. **Sphere version pin.** Every data sphere and calibration sphere is addressed by immutable `sphere_version`.
5. **Detector attestation.** Every detector invocation cites a workload attestation digest allowed by the governing policy.
6. **No ambient detector access.** HOPE invokes detectors only through scoped capability tokens. Child tokens may only reduce scope.
7. **LR calibration is family-specific.** Detector probabilities do not become likelihood ratios without a calibration artifact for the relevant hypothesis family.
8. **Uncertain calibration cannot contribute decisive evidence.** If the CI for a detector's log LR crosses zero in the production firing range, the finding is informational only for that family.
9. **Per-evidence clipping.** No single evidence contribution may exceed the configured per-evidence log-LR bound.
10. **Dependency down-weighting.** Correlated detector firings must be adjusted through the declared joint-inference method before aggregation.
11. **Counter-tests are governed activities.** CTEST/TTEST outcomes are child provenance activities of detector events and must carry evidence or waiver records.
12. **Reversibility is mandatory.** A published HOPE report must disclose reversibility distance and a minimal counter-evidence set or it is non-conforming.
13. **Export guard before egress.** Any report leaving the authoring sphere must carry an export receipt from the required guard workload.
14. **Appeal path.** Detector findings, evidence contributions, report decisions, evidence authority classifications, export decisions, and profile-affecting updates are appealable unless a higher safety/legal policy explicitly forbids appeal.
15. **Replay manifest.** Every run must preserve enough input references, artifact digests, model hashes, calibration versions, and policy hashes for deterministic or evidence-only replay.
16. **Small-N discipline.** Small-N evidence follows the existing Epistemic Governance policy: `N <= 10` enumerates examples and forbids generalization; `10 < N < 30` requires shrinkage and widened uncertainty.

## End-to-end choreography

A conforming implementation follows this control sequence.

1. Register the hypothesis run with `H`, explicit `not-H`, time window, requested detectors, requested sphere versions, HOPE model version, and thresholds.
2. Compile the run into a signed policy record and notarize the pre-registration commitment.
3. Mint a capability token scoped to the exact detector/sphere pairs allowed for the run.
4. Verify detector workload attestations before invocation.
5. Enumerate scoped discourse or evidence move IDs from the KG or sphere boundary.
6. Invoke detector workloads with child tokens that reduce scope to the relevant detector and move batch.
7. Apply counter-test gating and joint-inference dependency handling.
8. Convert detector outputs into family-specific likelihood-ratio contributions using calibration artifacts.
9. Maintain cumulative log likelihood, e-process state, and anytime-valid stopping metadata.
10. Assemble the reversibility report.
11. Invoke export guard before any cross-sphere egress.
12. Publish and notarize the report bundle with provenance and appeal metadata.

## Hypothesis families

Initial LR calibration families:

| Family | Description |
|---|---|
| `F_epistemic-soundness` | Whether a claim or argument is epistemically sound in context. |
| `F_deception` | Whether a speaker or agent is deliberately misleading about a topic. |
| `F_group-pattern` | Whether a group exhibits a reasoning or bias pattern over a topic. |
| `F_forensic-claim` | Whether an event occurred with a given mechanism, time, or causal account. |

Each detector may have different LR weight by family. For example, a `LOGFALL.STRAWMAN` finding is strong evidence against argument soundness but weak evidence that a specific external event occurred.

## Required downstream ownership

SocioSphere owns this standard, protocol registration, fixtures, registry mapping, and workspace validation. Implementation remains downstream.

| Concern | Canonical downstream owner |
|---|---|
| Detector and counter-test execution bundles | `SocioProphet/agentplane` |
| Policy thresholds, severity, appeal, export, retention, drift freeze, and promotion gates | `SocioProphet/policy-fabric` |
| Runtime services, platform-facing contracts, evidence APIs, report publication services | `SocioProphet/prophet-platform` |
| Capability token, grant, attestation, authority, quorum, and ledger handoff | `SocioProphet/mcp-a2a-zero-trust` |
| Ontology terms for claims, evidence, detectors, counter-tests, LR calibration, reversibility, and appeals | `SocioProphet/ontogenesis` |
| Local-first discourse event integrity, SourceOS lanes, tombstones, repairs, replay state | `SourceOS-Linux/sourceos-syncd` and `SourceOS-Linux/sourceos-spec` |
| Reasoning Calibration Projection linkage | `SocioProphet/HolographMe` and `SocioProphet/human-digital-twin` |
| Metrics, release-readiness, appeal rate, repair success, calibration drift, audit completeness | `SocioProphet/delivery-excellence` |
| Reference UI surfaces for reports, top evidence, reversibility distance, and appeal workflow | `SocioProphet/socioprophet` |

## Minimum viable slice

MVS-HOPE-1 is intentionally small.

1. One `hyp:HypothesisRun` fixture with explicit negation and frozen thresholds.
2. One scoped capability-token fixture.
3. One `LOGFALL.STRAWMAN.V3` detector event fixture.
4. One `CTEST.STEELMAN.CONFIRM.V2` outcome fixture.
5. One `hyp:EvidenceContribution` fixture using LR clipping and dependency down-weighting.
6. One `hyp:ReversibilityReport` fixture with reversibility disclosed and appeal path present.
7. One negative fixture proving missing explicit negation is rejected.
8. One SocioSphere validator proving fixture conformance.

## Compatibility and versioning

This is an additive Epistemic Governance extension with a new ruleset label: `1.5.0-math`.

The extension is non-breaking for existing `1.3.0` detector/counter-test consumers because it does not remove existing detector IDs, counter-test IDs, lifecycle states, privacy tiers, or repair IDs. It does add stricter conformance rules for systems claiming HOPE-level hypothesis evaluation.

A downstream implementation may continue to emit `hygiene.detect.v1` without being HOPE-conformant. A downstream implementation may claim HOPE conformance only if it emits the run, token, detector, evidence-contribution, reversibility, export, and audit artifacts required here.

## Publication rule

A HOPE report must never be published as a final institutional conclusion unless it carries:

- explicit hypothesis and explicit negation hashes;
- pre-registered decision thresholds;
- sphere versions;
- detector attestations;
- calibration artifact references;
- evidence contribution chain;
- reversibility distance and minimal counter-evidence set;
- small-N caveats when applicable;
- governance compliance and export receipt when applicable;
- appeal channel;
- notarization or equivalent audit anchor.

If any required field is redacted, the field key remains present and the redaction reason is recorded.
