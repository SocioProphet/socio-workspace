# SVF Workspace State Readout

Status: Sociosphere workspace-control primitive  
Plane: Sociosphere / workspace registry and stabilization  
Authority source: SocioProphet/ProCybernetica SVF policy primitive

## Purpose

Sociosphere owns the estate-level workspace state for Sovereign Validation Fabric (SVF) adoption.

The workspace state readout is not a CI matrix and not a downstream validator. It is a registry-derived control surface that records which profiles exist, which plans are selected, which repo-local commands are expected, and which observations are still missing.

## Correct boundary

Sociosphere may:

- register SVF profiles;
- select plans from changed paths;
- expose repo-local validation commands;
- record missing observations as validation debt;
- preserve advisory/blocking mode;
- provide workspace-level readouts to Prophet Platform, model-router, Superconscious, and AgentPlane.

Sociosphere must not:

- certify downstream repository behavior from selection alone;
- convert missing observations into success;
- issue or verify semantic receipt truth beyond committed receipt-shape checks;
- silently promote advisory profiles to blocking gates;
- replace ProCybernetica as SVF authority.

## Current state semantics

A profile with a declared `validation_command` but no attached observation is reported as:

```text
selected_missing_observation
```

The corresponding warning is:

```text
validation_observation_missing
```

A profile without a declared validation command is reported as:

```text
not_configured
```

## Local surfaces

```text
registry/sovereign-validation-fabric.yaml
tools/svf_runner.py
tools/svf_workspace_state.py
tools/check_svf_workspace_state.py
.github/workflows/svf-validation.yml
```

## Non-claims

This readout does not execute downstream validation commands.

This readout does not certify downstream repositories.

This readout does not issue ValidationReceipts.

This readout exists so consumers do not confuse plan selection with validation success.
