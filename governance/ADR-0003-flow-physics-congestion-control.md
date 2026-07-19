# ADR-0003 — Flow Physics, Congestion Control, and Fair Scheduling

Status: draft  
Date: 2026-05-04

## Context

The portfolio already has a decision-plane registry, execution timing telemetry, and Lattice observability/SRE registration. Those artifacts establish a strong governance and evidence substrate, but they do not yet make queueing physics, class isolation, overflow behavior, or citizen-visible congestion explanations portfolio-canonical.

Existing execution timing records include queue and run timestamps, retry count, evidence references, and replay references, but they do not yet define service classes, admission decisions, per-class buffers, utilization estimates, Little's Law audits, or overflow receipts.

Existing Lattice observability requires logs, metrics, traces, receipts, health checks, SLOs, alerts, runbooks, control loops, and incident artifacts across the product planes, but it does not yet require queueing-specific metric families such as attempted/admitted/rejected arrivals, queue depth, in-service count, configured servers, configured buffers, queue wait histograms, service-time histograms, utilization estimates, or Little's Law error ratios.

## Decision

We add **SDP-8 — Flow Physics, Congestion Control, and Fair Scheduling** to the strategic decision-plane registry.

This plane owns the portfolio vocabulary and release gates for treating the citizen fog commons as a measured flow system. The plane is not a replacement for governed execution, deterministic transport, observability, or policy. It binds them together around operational capacity, fairness, queueing, and overload behavior.

## Scope

SDP-8 covers:

- canonical `Job` and `ServicePool` definitions
- service classes and class isolation
- arrival, admission, rejection, deferral, spillover, degradation, and completion accounting
- lambda, mu, mean service time, configured servers, configured buffers, and utilization estimates
- Little's Law audit checks
- queue discipline vocabulary, including EDF, DRR, WFQ, aging, and preemptible background work
- overflow outcomes and required receipt payloads
- retry-after, idempotency, retry budgets, and anti-bullwhip controls
- spillover-disabled-by-default posture until trust, privacy, and capacity attestation are specified
- citizen-facing queue status, wait explanations, and receipt surfaces

## Anchor mapping

- `SocioProphet/sociosphere`: portfolio registry, release vocabulary, adoption reporting, and cross-repo conformance view
- `SocioProphet/socioprophet-standards-storage`: normative flow physics standard, measurement contracts, schemas, and semantic conventions
- `SocioProphet/policy-fabric`: class isolation, retry, fairness, overflow, and spillover policy bundles
- `SocioProphet/prophet-platform`: runtime reference implementation for admission, scheduling, telemetry, and receipts
- `SocioProphet/agentplane`: admission, overflow, timing, execution, evidence, and replay artifact extension
- `SourceOS-Linux/sourceos-spec`: edge-node contract binding
- `SourceOS-Linux/sourceos-shell`: local citizen/operator queue status and receipt presentation
- `SourceOS-Linux/agent-machine`: agent-side retry, idempotency, admission-token, and degrade compliance

## Required gates

1. **flow-standard-defined** — a canonical standard defines objects, metrics, units, class taxonomy, Little's Law invariant, and receipt requirements.
2. **queueing-semconv-present** — observability artifacts and runtime services emit required queueing metric families with stable units and bounded labels.
3. **admission-overflow-receipts-emitted** — every admission, rejection, deferral, degradation, spillover, or human-escalation decision emits a signed receipt.
4. **little-law-audit-green** — per-class and per-node audits validate `L ≈ lambda_out * W` within declared tolerance windows.
5. **class-isolation-policy-green** — policy bundles define service classes, utilization targets, buffer caps, retry budgets, fairness rules, and overflow policies.
6. **spillover-disabled-until-attested** — fog-to-fog spillover remains disabled unless privacy scope, trust domain, and capacity attestation gates pass.

## Non-goals

- This ADR does not implement the runtime scheduler.
- This ADR does not define the full spillover protocol.
- This ADR does not claim portfolio-wide conformance.
- This ADR does not replace existing Lattice observability or Agentplane execution telemetry.

## Implications

- Average latency alone is insufficient; p95/p99, variance, queue depth, rejection, deferral, and overflow behavior become governance-relevant.
- Hidden queues are not acceptable for citizen-facing services.
- Agents may request urgency, but the control plane must validate and enforce service class admission.
- Spillover is explicitly unsafe until privacy, trust, and capacity claims are attestable.
- Citizen-facing explanations become part of the control loop because unexplained or seemingly unfair waits degrade legitimacy.

## Follow-on implementation sequence

1. Add the normative standard and schemas in `socioprophet-standards-storage`.
2. Extend Lattice Observability SRE with the congestion-health-loop and queueing metric families.
3. Extend Agentplane timing records with admission, service class, queue depth, buffer, utilization, and receipt references.
4. Add Policy Fabric bundles for class isolation, retry budgets, fairness, and overflow.
5. Add a Prophet Platform local admission controller reference implementation with metrics and receipts.
6. Add Sociosphere adoption scanning for cross-repo compliance.
7. Bind SourceOS-Linux edge/node/agent surfaces.
8. Add citizen-facing queue status and receipt views.
