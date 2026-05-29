# Signadot Parity Gap for SVF Workspace State

Status: next-tranche planning note  
Plane: Sociosphere / workspace state and environment planning  
Current tranche dependency: SVF workspace registry and workspace-state readout

## Purpose

This document records the gap between the current Sociosphere SVF workspace-state tranche and the broader Signadot-style parity target.

The current tranche establishes registry-derived validation state. It does not yet provide request-isolated sandbox environments, changed-service deployment, traffic routing, stateful resource isolation, or agent-invoked live validation.

## Current completed layer

Sociosphere now provides the estate control-plane substrate for:

- registered validation profiles;
- selected plans;
- expected repo-local validation commands;
- advisory versus blocking posture;
- explicit missing-observation state;
- workspace-state readout semantics for downstream consumers.

The key state is:

```text
selected_missing_observation
```

with warning:

```text
validation_observation_missing
```

This means validation is selected but not observed. It is validation debt, not success.

## Parity target

The next tranche should add an environment/sandbox capability layer that can eventually support:

- PR-scoped environment creation;
- inner-loop changed-service validation against live dependencies;
- changed-service-only deployment with baseline fallback;
- HTTP/gRPC request routing into sandbox versus baseline;
- asynchronous queue/topic isolation;
- stateful resource isolation for databases and similar resources;
- validation jobs and plans backed by real execution evidence;
- agent-facing invocation through Prophet Platform and AgentPlane;
- observed evidence attachment back into Sociosphere workspace state.

## Proposed estate placement

Sociosphere owns:

- environment profile registry;
- workspace topology;
- environment selection;
- sandbox state readout;
- missing-observation and stale-observation state.

AgentPlane owns:

- execution records;
- replay/evidence artifacts;
- validation run records;
- evidence attachment for observed sandbox jobs.

Prophet Platform owns:

- product/API-facing `validate_change` and environment request surfaces;
- agent interaction contract over Sociosphere and AgentPlane.

SourceOS / Agent Machine owns:

- local runtime substrate;
- developer/agent workspace activation;
- local-to-cluster bridge contracts.

Model-router and Superconscious consume:

- Sociosphere workspace state;
- observed/stale/failed validation state;
- autonomy and planning constraints derived from evidence state.

## Non-claims

This document does not implement sandbox execution.

This document does not certify Signadot feature parity.

This document does not authorize downstream validation execution.

This document does not change the current SVF missing-observation semantics.

## Recommended next tranche

The next tranche should be opened as a separate implementation stream:

```text
P9 — Environment Profile Registry
P10 — Sandbox Runtime Contract
P11 — AgentPlane Validation Execution Adapter
P12 — Prophet Platform validate_change v2
P13 — Consumer status expansion
```

The current chat should retire after the SVF workspace-state closeout and this parity gap is recorded.
