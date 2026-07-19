# Sociosphere Impulse / Reflection Model v0.1

## Purpose

The impulse / reflection model defines how Sociosphere receives work, decides whether to absorb it, deflect it, quarantine it, or reject it, and then records the resulting routing decision as auditable agent-DevOps control-plane evidence.

Sociosphere is the workspace controller and agent DevOps kernel. It should absorb structure and deflect component substance:

- absorb: topology, manifests, locks, standards, fixtures, schemas, validation, propagation, scheduling, coherence, source-exposure posture, and cross-repo coordination envelopes
- deflect: product behavior, service internals, component-local feature work, downstream CI implementation details, UI logic, model behavior, data ingestion code, and runtime implementation internals

The model prevents Sociosphere from becoming a feature junk drawer while preserving its role as the scheduler, interrupt membrane, queue-state ledger, and cross-repo coherence coordinator.

## Computational doctrine

This model is derived from the MIT 6.004 computation-structures ladder and translated into SocioProphet estate operations:

| Computation structures concept | Sociosphere control-plane equivalent |
| --- | --- |
| combinational logic | scope and policy predicates |
| sequential logic | finite work states and explicit commit edges |
| instruction set | small auditable agent-runtime primitive vocabulary |
| compiler / assembler | workflow lowering from intent to executable work orders |
| cache validity / dirty state | freshness, divergence, stale-read, and invalidation semantics |
| interrupts and SVC traps | external event ingress and controlled requests into the kernel |
| parallel consistency | distributed agent coherence, barriers, and propagation rules |

## Definitions

An `Impulse` is an inbound event or request that may require Sociosphere action. It may come from a human instruction, GitHub issue, PR, CI status, upstream release, policy update, capability event, artifact event, stale-cache signal, security alert, runtime request, or cross-repo architectural proposal.

A `ReflectionDecision` is Sociosphere's scoped decision about how the impulse should be handled. It records ownership, topology, propagation, risk, consistency requirements, evidence requirements, and the final routing decision.

## Decision classes

- `absorb`: Sociosphere owns and implements the work directly.
- `absorb_and_propagate`: Sociosphere owns the control-plane envelope and opens or links downstream work.
- `deflect`: the work belongs in another repo; Sociosphere routes it with constraints and acceptance criteria.
- `quarantine`: the work is under-specified, risky, stale, source-exposure-sensitive, or needs policy/security review.
- `reject`: the work violates topology, scope, source-exposure policy, or non-goals.

## Reflection gates

Each impulse should be evaluated by these gates before routing:

1. Canonical ownership gate: Which repo owns the namespace and implementation surface?
2. Topology gate: Does the impulse preserve Sociosphere's dependency direction and workspace-controller role?
3. Determinism gate: Does it affect manifest, lock, runner behavior, validation, fixtures, exact pins, or reproducibility?
4. Propagation gate: Does it trigger downstream notification, auto-PR, compatibility validation, or cascade-depth limits?
5. Execution contract gate: Does it define cross-repo build, test, deploy, adapter, or task semantics?
6. Risk/source-exposure gate: Does it expose restricted security, operational, personal, or publication-sensitive state?
7. Barrier gate: Does it require strong synchronization before promotion, release, merge, runtime admission, policy promotion, model route promotion, boot/trust publication, security revocation, or authoritative memory promotion?

## Work-state spine

Recommended state machine:

```text
impulse_received
  -> classified
  -> ownership_resolved
  -> risk_scored
  -> topology_checked
  -> reflection_decision
  -> absorbed | absorbed_and_propagated | deflected | quarantined | rejected
```

Absorbed work continues:

```text
spec_written -> validation_defined -> implementation_pr -> checks_pending -> reviewed -> merged -> propagated
```

Deflected work continues:

```text
child_issue_opened -> downstream_assigned -> blocked_on_child -> child_validated -> parent_reconciled
```

Quarantined work continues:

```text
needs_context -> needs_policy_review | needs_security_review | needs_source_exposure_review -> redesign_or_reject
```

## Absorption modes

- `hard_absorb`: direct Sociosphere implementation.
- `soft_absorb`: Sociosphere captures doctrine/spec, downstream repos implement.
- `absorb_as_pin`: Sociosphere records upstream baseline, disposition, lock/pin, and hardening posture.
- `absorb_as_fixture`: Sociosphere owns compatibility examples and fixture expectations.
- `absorb_as_barrier`: Sociosphere owns a promotion/release/admission barrier but not downstream feature code.

## Deflection modes

- `direct_deflection`: open/link work in the owning repo.
- `mediated_deflection`: keep a Sociosphere parent issue while downstream work completes.
- `policy_deflection`: downstream implements feature; Sociosphere retains policy/schema/barrier work.
- `quarantine_deflection`: hold until security, source-exposure, or policy concerns are resolved.
- `rejective_deflection`: close/no-op due to scope or topology violation.

## Required artifacts

This standard defines two schemas:

- `impulse.schema.v0.1.json`
- `reflection-decision.schema.v0.1.json`

Example fixtures live under `examples/`.

## Initial implementation boundary

This standard is documentation and schema first. Runtime automation should only follow after the reflection vocabulary, routing decisions, and evidence requirements are accepted across the agent DevOps mesh.

Refs: SocioProphet/sociosphere#315.
