# EMVI Trust and Action Classes

Status: Draft v0.1

## Purpose

The shell must distinguish parsing from execution and observation from side effects.
This document defines the minimum action-trust ladder for ActionSpecs.

## Core rule

Parsing intent is not execution.
Every state-changing path must first become an ActionSpec with an explicit trust class.

## Action classes

### Observe
Read-only inspection with no state change.
Examples:
- search
- open preview
- inspect ledger
- query graph

### Capture
Create a new shell-facing representation without mutating the external target.
Examples:
- capture page into collection
- capture snippet
- snapshot collection

### Draft
Prepare a proposed change but do not commit it.
Examples:
- generate a patch draft
- stage a note draft
- prepare an export artifact before publish

### ReversibleWrite
A state-changing action with an expected rollback path.
Examples:
- append collection member
- update a mutable metadata field
- reversible local mutation

### IrreversibleWrite
A state-changing action with no guaranteed rollback.
Examples:
- destructive deletion
- external send/post without undo
- irreversible remote mutation

### PrivilegedExecute
An action requiring elevated capability, boundary crossing, or sensitive target access.
Examples:
- protected host action
- privileged shell operation
- sensitive policy-governed remote mutation

### DelegatedProposal
An agent or planner proposes an action but does not execute it.

### DelegatedExecute
An agent executes under an approved delegation envelope.

## Required ActionSpec fields

Every ActionSpec must declare:
- normalized intent
- target objects
- action class
- service-family routing
- placement expectation
- preview availability
- confirmation requirement
- rollback expectation
- provenance sink

## Confirmation model

Suggested default policy:
- Observe: no confirmation unless context requires it
- Capture: normally no confirmation, but must remain inspectable
- Draft: no destructive confirmation; review surface encouraged
- ReversibleWrite: confirmation depends on policy and target sensitivity
- IrreversibleWrite: explicit confirmation required
- PrivilegedExecute: explicit confirmation and policy approval required
- DelegatedProposal: human review required before execution
- DelegatedExecute: requires prior approved delegation policy

## Plan review rule

Any action class above Observe may route through PLAN_REVIEW.
PrivilegedExecute and high-risk IrreversibleWrite must do so.

## Invariants

1. No state-changing path bypasses ActionSpec creation.
2. Trust class is explicit, never inferred only from UI wording.
3. Provenance is required for all nontrivial action classes.
4. Agent proposals and agent executions are different classes.
5. Host-boundary ownership can still deny execution even after parsing succeeds.
