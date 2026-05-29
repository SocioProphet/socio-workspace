# Environment Sandbox Parity Bridge Plan

Status: implementation bridge plan  
Plane: Sociosphere / workspace environment state  
Depends on: `docs/architecture/signadot-parity-gap.md`, `registry/environment-sandbox-profiles.yaml`

## Purpose

This document turns the Signadot-parity gap into an implementation bridge.

The current estate has SVF workspace-state semantics and the first environment/sandbox profile registry. It does not yet have executable sandbox runtime parity. This plan defines the minimum sequence required to bridge from registry intent to observed sandbox validation evidence.

## Non-negotiable boundary

Sociosphere owns workspace and environment state. It does not execute sandbox workloads.

AgentPlane owns execution records, replay records, run evidence, and validation artifacts.

Prophet Platform owns product/API invocation surfaces over Sociosphere and AgentPlane.

ProCybernetica owns authority semantics and policy primitives.

SourceOS / Agent Machine owns local runtime substrate, workspace activation, and local-to-cluster bridge contracts.

model-router and Superconscious consume environment state and evidence state. They do not define validity.

## Bridge phases

### P9 — Environment request contract

Add a machine-readable EnvironmentRequest shape with:

- repo;
- ref;
- change digest;
- requested environment profile;
- selected validation plans;
- requested isolation class;
- requested routing class;
- requested resource isolation class;
- actor identity;
- policy refs;
- non-claims.

Initial home: Sociosphere, because the request is selected from workspace/environment registry state.

### P10 — Sandbox run contract

Add a SandboxRun shape with:

- request ref;
- executor plane;
- run status;
- baseline ref;
- changed service refs;
- routing mode;
- async isolation mode;
- stateful resource mode;
- evidence refs;
- teardown state;
- non-claims.

Initial home: AgentPlane, because execution and evidence belong there.

### P11 — Synthetic execution adapter

Implement the first AgentPlane adapter as a synthetic no-network execution path.

It must not create real infrastructure. It should prove the lifecycle shape:

```text
EnvironmentRequest -> SandboxRun -> Evidence -> Sociosphere state update
```

Acceptance criteria:

- deterministic fixture;
- no network;
- no credentials;
- evidence artifact emitted;
- failed fixture rejects missing evidence;
- Sociosphere can consume the evidence ref as `environment_observed` or `environment_failed`.

### P12 — Prophet Platform `validate_change` v2

Upgrade `validate_change` from selection/readiness to request orchestration.

It may request environment validation through Sociosphere and AgentPlane. It may not directly execute infrastructure or bypass policy.

Minimum v2 response statuses:

- `environment_selected_missing_observation`;
- `environment_requested`;
- `environment_running`;
- `environment_observed`;
- `environment_failed`;
- `environment_stale`.

### P13 — Runtime adapter design

Only after P9-P12 are green, design real runtime adapters:

- Kubernetes namespace or overlay strategy;
- changed-service deployment contract;
- baseline fallback routing;
- HTTP/gRPC route propagation;
- queue/topic isolation;
- stateful resource plugin interface;
- teardown and TTL controller;
- quota and policy enforcement.

No real sandbox parity claim is allowed before this phase has execution evidence.

## Minimum end-to-end slice

The first credible bridge is not full parity. It is an end-to-end observed synthetic run:

1. Sociosphere selects an environment profile.
2. Prophet Platform submits an EnvironmentRequest.
3. AgentPlane emits a SandboxRun fixture and evidence artifact.
4. Sociosphere ingests evidence ref and reports `environment_observed`.
5. model-router constrains or relaxes routing based on the observed state.
6. Superconscious records validation history without granting authority.

## Feature parity gates

The estate may not claim Signadot-style parity until all gates below exist with observed evidence:

- PR-scoped environment lifecycle;
- changed-service-only deploy path;
- baseline fallback path;
- HTTP/gRPC route isolation;
- async queue/topic isolation;
- stateful resource isolation;
- validation job execution evidence;
- teardown/TTL evidence;
- policy/secret/data-boundary enforcement;
- agent-facing control surface.

## Immediate next issue set

1. Sociosphere: add EnvironmentRequest schema and fixtures.
2. AgentPlane: add SandboxRun schema and synthetic evidence fixture.
3. Prophet Platform: add `validate_change` v2 fixture that requests environment validation.
4. Sociosphere: add environment evidence ingestion state fixture.
5. model-router and Superconscious: add consumer fixtures for `environment_observed` and `environment_failed`.

## Non-claims

This plan does not certify parity.

This plan does not execute real sandbox infrastructure.

This plan does not authorize live cluster access.

This plan does not bypass SVF authority or policy gates.
