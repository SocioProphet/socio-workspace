# Sovereign Validation Fabric Workspace Layer

Status: proposal-candidate for Sociosphere implementation  
Issue: #394  
Upstream authority: SocioProphet/ProCybernetica#100  
Plane: Sociosphere / workspace controller

## Purpose

This document defines the Sociosphere side of Sovereign Validation Fabric (SVF): workspace registry, plan discovery, changed-path selection, local runner contract, and receipt verification entrypoint.

SVF is not a vendor integration and is not an arbitrary command runner. Sociosphere consumes the ProCybernetica SVF policy primitive and routes validation through registered Plans and Actions.

## Scope boundary

Sociosphere owns:

- workspace-level SVF registry;
- repo-to-plan mapping;
- changed-path plan selection;
- runner command contract;
- local backend contract;
- receipt artifact location conventions;
- receipt verification entrypoint;
- Sociosphere dogfood Plan.

Sociosphere does not own:

- SVF authority vocabulary;
- claim-scope taxonomy;
- side-effect taxonomy;
- production-environment policy;
- downstream repo-specific validation implementation;
- agent-plane UX;
- model-router autonomy policy;
- Subconscious memory interpretation.

Those remain in their owning planes.

## Authority dependency

The authoritative schema family is defined upstream in ProCybernetica:

- `svf_validation_action.v1.json`
- `svf_validation_plan.v1.json`
- `svf_validation_capability_policy.v1.json`
- `svf_validation_run.v1.json`
- `svf_validation_receipt.v1.json`

Sociosphere must treat those schemas as imported authority. Local registry validation may add Sociosphere-specific structure, but it may not weaken the upstream policy primitive.

## Workspace registry

The first registry should live under:

`registry/sovereign-validation-fabric.yaml`

The registry maps repositories to validation profiles. A profile declares:

- repo identity;
- owning plane;
- local path hint;
- default Plans;
- changed-path selectors;
- advisory vs blocking mode;
- required receipt classes;
- policy profile reference;
- execution backend class;
- upstream policy schema references.

The registry is a discovery surface. It does not certify execution by itself.

## Runner contract

The first CLI contract should be implemented as:

```text
python3 tools/svf_runner.py list
python3 tools/svf_runner.py select --repo <owner/name> --changed-path <path> [--changed-path <path> ...]
python3 tools/svf_runner.py run --plan <plan-id>
python3 tools/svf_runner.py verify-receipt <receipt-path>
python3 tools/svf_runner.py explain <receipt-path>
```

The first implementation may support `list`, `select`, and `verify-receipt` before `run`. Running Actions requires stricter local execution controls and should be staged after registry and selector validation are stable.

## Local backend rule

The local backend may execute only registered Actions admitted by an upstream CapabilityPolicy. It must reject ad hoc commands. If a requested backend, credential mode, network mode, or filesystem scope cannot be enforced locally, the runner must fail closed with `not_configured` rather than silently ignoring policy.

## Receipt location

The default workspace receipt location should be:

`artifacts/svf/receipts/`

Receipts should be ignored or treated as generated artifacts unless a specific receipt fixture is intentionally committed under `tests/fixtures/`.

## Dogfood plan

The first Sociosphere dogfood plan should validate:

- `registry/sovereign-validation-fabric.yaml` shape;
- repo profile entries;
- changed-path selector examples;
- receipt example shape;
- rejection of malformed registry entries.

This dogfood plan proves workspace registration and selection. It does not prove downstream repository correctness.

## First repo profile targets

Initial profiles should be advisory or blocking as follows:

| Repo | Plane | Initial mode | Purpose |
|---|---|---:|---|
| SocioProphet/sociosphere | workspace controller | blocking | Dogfood registry/selector/receipt shape |
| SocioProphet/ProCybernetica | policy fabric | blocking | SVF schema and fixture conformance |
| SocioProphet/SCOPE-D | defensive assurance | advisory first | Defensive validation plan registration |
| SocioProphet/ontogenesis | ontology | advisory first | Semantic validation plan registration |

SourceOS and SociOS profiles should follow after the local runner and receipt verifier are stable.

## Non-claims

This document does not certify that any validation Plan has run.

This document does not implement runtime execution of Actions.

This document does not authorize production-environment validation.

This document does not create agent-plane autonomy. Agent invocation remains downstream.
