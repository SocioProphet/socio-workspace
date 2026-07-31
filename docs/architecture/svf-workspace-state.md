# SVF Workspace State

Status: Sociosphere workspace-control doctrine  
Plane: Sociosphere / workspace registry and stabilization  
Authority source: SocioProphet/ProCybernetica SVF policy primitive

## Purpose

Sociosphere owns workspace-level SVF selection and validation-state readout. It does not own downstream validation semantics, execute downstream repository commands, issue receipts, or certify downstream repository behavior.

The point of workspace state is to preserve the distinction between selected validation plans, expected commands, observed evidence, and missing observations.

## Core rule

Selection is not validation.

If a repository profile has an applicable plan and a validation command but no observed evidence or receipt reference, Sociosphere must represent the state as `selected_missing_observation` and preserve `validation_observation_missing`.

That state is validation debt. It is not success.

## Workspace state fields

A workspace state row may include:

- `profile_id`
- `repo`
- `owning_plane`
- `mode`
- `policy_ref`
- `default_plans`
- `contract_refs`
- `validation_command`
- `required_receipt_classes`
- `validation_status`
- `warnings`
- `observed_validation_commands`
- `receipt_refs`

## Initial statuses

- `selected_missing_observation` — a profile declares a validation command, but no observation has been attached.
- `not_configured` — a profile does not declare an executable validation command.

Future statuses may include `observed_pass`, `observed_fail`, and `stale_observation`, but those require evidence attachment rules and receipt verification rules first.

## Consumer boundaries

Prophet Platform may use Sociosphere workspace state to explain which SVF plans apply to a change.

Model Router may use Sociosphere workspace state to constrain autonomy or model-lane escalation.

Superconscious/Subconscious may use Sociosphere workspace state as validation-memory input.

None of these consumers may convert missing observations into validation success.

## Non-claims

This document does not execute validation commands.

This document does not issue receipts.

This document does not certify downstream repositories.

This document does not make Sociosphere the authority over SVF claim semantics.
