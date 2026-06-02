# Privacy Non-Linkability Workspace Binding

Status: v0 workspace binding
Authority source: `SocioProphet/ontogenesis/docs/specs/privacy-nonlinkability-doctrine-v0.md`
Owning repo for this projection: `SocioProphet/sociosphere`
Scope: workspace controller, manifest, lock, runner, artifact, and cross-repo evidence surfaces

## Purpose

This document projects the Ontogenesis `DoNotLearn` / `DoNotLink` doctrine into the Sociosphere workspace controller.

Ontogenesis remains the semantic authority. Sociosphere does not redefine privacy vocabulary, legal basis, or product behavior. Sociosphere binds the doctrine into workspace mechanics: manifests, locks, runner artifacts, cross-repo adoption tracking, replay boundaries, and agent-plane handoff surfaces.

The immediate lesson from local OS hardening work is that systems can create privacy risk without an explicit user-facing action. Indexers, search stores, telemetry daemons, sync agents, profile subscribers, background task managers, and agent runners can convert source material into derived reusable state or hidden relation surfaces. Sociosphere must therefore treat derived workspace state as governed state, not incidental exhaust.

## Source doctrine summary

The imported distinction is:

- `DoNotLearn` governs representation formation.
- `DoNotLink` governs relation formation.

At workspace level this becomes:

- no training, embedding, durable summary, reusable memory, topic-pack promotion, profile construction, policy-learning input, or evaluation corpus update from protected workspace signals without an explicit privacy decision and receipt;
- no graph edge, join key, entity resolution, workroom bridge, source-context join, latent-neighbor bridge, topic-membership bridge, or provenance bridge across protected scopes without an explicit privacy decision and receipt.

## Workspace threat model

Sociosphere assumes the following failure modes are realistic even when every individual subsystem claims to be behaving normally:

1. A workspace runner writes derived artifacts that preserve protected content in a new location.
2. A search or memory subsystem embeds protected material into a reusable index.
3. A topic pack or registry entry becomes a hidden cross-workroom linking membrane.
4. A debugging, telemetry, or heartbeat artifact leaks source identity, device identity, workroom identity, or protected context.
5. A recovered work thread becomes durable memory without an explicit owner, return condition, or privacy disposition.
6. A cross-repo evidence reference creates a practical join path between protected domains.
7. Agent-plane action receipts record enough correlated identifiers to reconstruct a protected relation.
8. A policy, validation, or delivery metric silently learns from protected operator behavior.

The control objective is not to eliminate observability. The objective is to make observability explicit, scoped, minimized, receipt-bearing, and non-promotional by default.

## Workspace invariants

1. A workspace manifest entry is not permission to learn from the referenced repo, artifact, user, event, or workroom.
2. A lockfile reference is not permission to link across workrooms, tenants, devices, users, legal contexts, or evidence domains.
3. A runner artifact is not automatically admissible to memory, vector search, topic packs, delivery metrics, model governance, or policy-learning loops.
4. A recovery-ledger entry is not permission to promote protected material into reusable state.
5. A search result is not permission to create a graph edge.
6. A citation is not permission to embed or summarize the source into durable memory.
7. A successful validation gate is not permission to reuse protected signals outside the admitted scope.
8. Unknown privacy scope fails closed: deny, quarantine, redact, or require review according to consuming policy.
9. Privacy receipts must remain separate from authority receipts. Evidence that an operation happened is not authority to repeat, learn from, or link it.
10. Workspace UI and product surfaces consume privacy decisions; they do not outrank them.

## Required Sociosphere binding objects

Sociosphere should standardize the following artifact types:

### `PrivacyBoundaryProjectionArtifact`

Records how an Ontogenesis privacy boundary projects into a workspace manifest, lock, or resolved workspace view.

Required fields:

- `artifact_kind: PrivacyBoundaryProjectionArtifact`
- `authority_repo: SocioProphet/ontogenesis`
- `authority_doc_ref`
- `workspace_ref`
- `manifest_ref`
- `lock_ref`
- `protected_scope_refs`
- `non_learning_constraints`
- `non_linkability_constraints`
- `default_disposition`
- `evidence_refs`

### `WorkspacePrivacyDecisionRef`

References a policy decision over a proposed workspace learning or linking operation.

Required fields:

- `decision_ref`
- `operation_kind: learning | linking | both`
- `proposed_operation_ref`
- `protected_signal_refs`
- `privacy_boundary_refs`
- `decision: allow | deny | require_review | provisional`
- `decision_authority_ref`
- `receipt_expectation`

### `WorkspaceNonLearningReceipt`

Records enforcement of a `DoNotLearn` constraint.

Required fields:

- `receipt_kind: WorkspaceNonLearningReceipt`
- `operation_ref`
- `protected_signal_refs`
- `attempted_learning_surface`
- `decision_ref`
- `disposition: blocked | admitted | minimized | redacted | aggregated | anonymized | ephemeral_only | expired | require_review`
- `derived_artifact_refs`
- `cleanup_refs`
- `timestamp`

### `WorkspaceNonLinkabilityReceipt`

Records enforcement of a `DoNotLink` constraint.

Required fields:

- `receipt_kind: WorkspaceNonLinkabilityReceipt`
- `operation_ref`
- `left_scope_ref`
- `right_scope_ref`
- `attempted_link_surface`
- `decision_ref`
- `disposition: blocked | admitted | minimized | redacted | aggregated | anonymized | ephemeral_only | expired | require_review`
- `graph_edge_refs`
- `join_key_refs`
- `cleanup_refs`
- `timestamp`

## Manifest and lock implications

Workspace manifest and lock materialization should support privacy projection without making privacy optional metadata.

Minimum manifest fields:

- `privacy_scope_ref`
- `protected_signal_class`
- `learning_allowed_default: false`
- `linking_allowed_default: false`
- `privacy_authority_ref`
- `privacy_decision_refs`

Minimum lock fields:

- frozen privacy authority document ref;
- resolved protected scopes;
- resolved default dispositions;
- hash of privacy projection artifact;
- runner validation result for non-learning and non-linkability constraints.

## Runner implications

The Sociosphere runner should eventually expose a privacy projection check parallel to existing lock and protocol checks.

Target command:

```text
python3 tools/runner/runner.py privacy:project
```

Target behavior:

1. read manifest and resolved lock;
2. resolve privacy authority refs;
3. emit `PrivacyBoundaryProjectionArtifact`;
4. fail closed on missing protected-scope declarations for known privacy-sensitive workspace surfaces;
5. fail closed when a workspace action attempts learning or linking without a privacy decision ref;
6. emit non-learning and non-linkability receipts for denied or review-required operations.

## Cross-repo handoff map

| Repo | Sociosphere handoff |
| --- | --- |
| `SocioProphet/ontogenesis` | Semantic authority for vocabulary, SHACL, JSON-LD, and examples. |
| `SocioProphet/policy-fabric` | Runtime decision logic for privacy admission. |
| `SocioProphet/guardrail-fabric` | Guardrail checks for prompt, retrieval, RAG, and agent surfaces. |
| `SocioProphet/memory-mesh` | Recall/writeback gating; no durable memory without privacy decision refs. |
| `SocioProphet/agentplane` | Action proposal/admission/receipt binding for effectful learning or linking operations. |
| `SocioProphet/agent-registry` | Actor authority and tool grant binding for privacy-relevant actions. |
| `SocioProphet/model-governance-ledger` | Training, evaluation, model, dataset, drift, and feedback-loop receipts. |
| `SocioProphet/sherlock-search` | Candidate-only retrieval discipline; search result is not link permission. |
| `SocioProphet/slash-topics` | Topic-pack membrane; no hidden cross-scope topic bridge. |
| `SocioProphet/prophet-platform` | Workroom/product integration and user-facing privacy controls. |
| `SourceOS-Linux/sourceos-syncd` | Local-first sync policy and derived-state cleanup receipts. |

## Apple/macOS hardening lessons absorbed

The platform lessons being absorbed here are architectural, not empirical claims against a vendor.

1. Indexing is learning-adjacent: a local index can become reusable state even when framed as search.
2. Object identifiers and compressed content caches can become derived privacy surfaces.
3. Heartbeats and telemetry can reveal state, timing, topology, and operational context.
4. Profile, auth, and management substrates can be privileged while ordinary user-facing inspection remains partial.
5. Log routing can make ordinary logs incomplete as evidence.
6. Background agents and subscribers can create control-plane effects without explicit user intent.

Sociosphere response: every derived workspace artifact, index, receipt, heartbeat, replay packet, and cross-repo reference must declare whether it is learnable, linkable, both, or neither.

## Initial validation backlog

1. Add `PrivacyBoundaryProjectionArtifact` fixture.
2. Add denied `WorkspaceNonLearningReceipt` fixture for a protected artifact proposed for memory-mesh writeback.
3. Add review-required `WorkspaceNonLinkabilityReceipt` fixture for a cross-workroom topic bridge.
4. Add runner stub `privacy:project` that emits a machine-readable artifact.
5. Add CI gate that validates privacy projection fixtures.
6. Add workspace inventory annotations for repos that consume privacy decisions.
7. Add downstream issues in memory-mesh, agentplane, policy-fabric, guardrail-fabric, model-governance-ledger, sherlock-search, and prophet-platform.

## Claim boundary

This binding does not prove privacy compliance, anonymization, non-surveillance, or security against a malicious operator. It records workspace-level obligations derived from the Ontogenesis doctrine and makes those obligations concrete enough to implement, test, and audit.
