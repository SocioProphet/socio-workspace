# Signadot synthetic bridge ledger

Status: synthetic bridge readout  
State authority: Sociosphere  
Scope: Prophet Platform validate_change v2 through AgentPlane, Sociosphere, Model Router, and Superconscious  
Runtime parity: not certified

## Purpose

This ledger records the end-to-end synthetic bridge completed for the Signadot-parity program. It is a cross-repo readout, not a runtime integration claim.

The completed bridge connects:

```text
Prophet Platform validate_change v2
  -> AgentPlane synthetic SandboxRun semantics
  -> Sociosphere environment evidence ingestion state
  -> Model Router environment-state routing posture
  -> Superconscious environment-state memory posture
```

## Landed PR chain

| Tranche | Repo | PR | Result |
|---|---|---:|---|
| 1 | SocioProphet/prophet-platform | #505 | validate_change v2 environment contract fixtures and validator |
| 2 | SocioProphet/prophet-platform | #508 | validate_change v2 API/gateway synthetic stub |
| 3 | SocioProphet/agentplane | #250 | synthetic SandboxRun schema, fixtures, validator, workflow |
| 4 | SocioProphet/prophet-platform | #513 | validate_change v2 to AgentPlane synthetic run-link fixture |
| 5 | SocioProphet/sociosphere | #415 | observed/failed environment evidence-ingestion state fixtures |
| 6a | SocioProphet/model-router | #16 | environment-state routing posture consumer |
| 6b | SocioProphet/superconscious | #62 | environment-state memory/planning posture consumer |

## Current semantic chain

### 1. Prophet Platform

Prophet Platform owns the product/API surface for `validate_change v2`. The current implementation exposes synthetic/no-network request and response contracts and an API/gateway stub. It may produce `environment_requested`, `environment_observed`, and `environment_failed` fixture semantics, but it does not execute live sandbox infrastructure.

### 2. AgentPlane

AgentPlane owns execution semantics. The current bridge defines synthetic `SandboxRun` states:

- `sandbox_requested`
- `sandbox_observed`
- `sandbox_failed`

This creates a shape-compatible execution evidence surface, but only for synthetic fixtures.

### 3. Sociosphere

Sociosphere owns workspace state and ingestion semantics. It consumes Prophet Platform / AgentPlane references and records transitions:

- `environment_requested` -> `environment_observed`
- `environment_requested` -> `environment_failed`

Sociosphere remains state authority only. It does not execute environment actions.

### 4. Model Router

Model Router consumes Sociosphere environment state as routing posture input.

For `environment_observed`:

- autonomy ceiling: `advisory`
- model lane ceiling: `standard`
- high-end/pro denied
- deterministic verification required

For `environment_failed`:

- autonomy ceiling: `report_only`
- model lane ceiling: `cheap`
- high-end/pro denied
- deterministic verification required

### 5. Superconscious

Superconscious/Subconscious consumes Sociosphere environment state as memory and planning context.

For `environment_observed`, it remembers observed state and stays advisory until runtime parity exists.

For `environment_failed`, it remembers failed state, recommends human review, and forces report-only planning bias.

Subconscious remains non-authority.

## Explicit non-claims

This ledger does not claim:

- live sandbox infrastructure exists;
- request-isolated environments are created;
- traffic is routed into ephemeral environments;
- queues, cron, async workers, stateful resources, databases, or caches are isolated;
- preview URLs, DNS, ingress, service mesh, or Kubernetes resources are provisioned;
- runtime parity with Signadot is certified;
- synthetic evidence can grant autonomous execution authority.

## Remaining gap to runtime parity

To approach runtime parity, the next program must add non-synthetic capabilities:

1. environment allocation and teardown;
2. service selection and dependency graph extraction;
3. traffic routing into isolated environments;
4. async and stateful-resource isolation;
5. evidence capture from actual runtime observations;
6. teardown verification and leak detection;
7. policy-bound promotion from synthetic observation to runtime observation;
8. operator-facing parity readout in Prophet Platform / Sociosphere.

Until those exist, the chain is a complete synthetic bridge, not a Signadot-equivalent runtime substrate.

## Completion statement

The synthetic bridge is complete when all listed PRs are merged and their focused validators are green. Runtime parity remains an open product tranche.
