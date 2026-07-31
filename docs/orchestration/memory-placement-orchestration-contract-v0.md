# Memory and Placement Orchestration Contract v0.1

## Status

Draft implementation slice for SocioSphere issue #325.

## Purpose

This contract establishes the first deterministic control-loop layer for memory-aware task placement across the SocioProphet estate. It adapts the AICDQN edge/offload pattern into SocioProphet governance terms: forecast load, score priority, mask infeasible actions, choose placement, emit receipts, and replay outcomes. The contract is deliberately not reinforcement-learning-first. v0.1 is a governed deterministic interface that produces the telemetry and receipts required before learning-based placement can be trusted.

## Control-loop shape

The v0.1 loop is:

1. Intake a task, memory event, or runtime event.
2. Construct a `PlacementStateVector`.
3. Attach `PredictedLoad`, `RuntimeQueueState`, and `TaskPriorityScore`.
4. Ask Policy Fabric for an `ActionFeasibilityMask`.
5. Choose a `PlacementDecision` and optional `MemoryDecision`.
6. Emit an AgentPlane-compatible `PlacementReceipt`.
7. Convert the receipt and outcome into a `ReplayTrainingTuple`.
8. Report placement and memory metrics into Delivery Excellence.
9. Promote, evict, pin, or hydrate memory only through governed memory lifecycle events.

## Estate ownership

SocioSphere owns orchestration state, queue topology, registry visibility, and readiness validation. It does not own downstream implementation.

AgentPlane owns executable placement receipts, replay boundaries, runtime evidence, and trace-to-receipt conversion.

Memory Mesh owns memory lifecycle: observed, proposed, approved, promoted, pinned, evicted, redacted, tombstoned.

Policy Fabric owns feasibility masks, policy-denial reasons, approval obligations, and evidence-native policy binding.

SourceOS/sourceos-syncd owns local node facts: battery, CPU/GPU, local models, cache pressure, trust boundary, and local-first sync state.

Delivery Excellence owns metrics: placement latency, task success, cost, policy-denial rate, memory hit rate, replayability, and queue health.

Holmes, Sherlock, Ontogenesis, and Hellgraph provide evidence retrieval, semantic verification, ontology alignment, and claim grounding for evidence-sensitive placement.

## Required contract objects

- `PlacementStateVector`
- `PredictedLoad`
- `TaskPriorityScore`
- `ActionFeasibilityMask`
- `PlacementDecision`
- `MemoryDecision`
- `PlacementReceipt`
- `RuntimeQueueState`
- `PlacementRewardSignal`
- `ReplayTrainingTuple`
- `MemoryPromotionEvent`
- `MemoryEvictionEvent`
- `PolicyMaskedAction`

## Deterministic v0.1 policy

The first implementation must remain deterministic. Priority scoring may be weighted, but the weights must be declared. Feasibility masks are hard constraints, not reward hints. A learned policy may recommend a route only after the estate has stable receipts and replay tuples. Even then, learned output remains advisory until governance promotes it.

## Non-goals

- No autonomous self-modifying scheduler.
- No production DQN placement.
- No ungoverned memory promotion.
- No hidden training from private traces.
- No cloud routing around Policy Fabric masks.
- No SourceOS daemon acting as global orchestrator.

## Validation

Run:

```bash
python3 tools/validate_memory_placement_orchestration.py
```

The validator checks the registry, required object set, state fields, action vocabulary, priority components, feasibility mask reasons, positive fixtures, and negative fixtures.
