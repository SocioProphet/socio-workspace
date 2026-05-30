# Workspace Context Fabric source exposure review v0.1

Status: active baseline
Scope: Workspace Context Fabric estate registration and topology

## Decision

Workspace Context Fabric introduces provider-facing context capture and projection surfaces, so the estate requires an explicit source-exposure posture.

## Baseline posture

1. Canonical workspace context remains in `prophet-workspace` domain objects.
2. External providers receive compiled projections, not canonical context graphs.
3. Provider-facing operations require MCP/A2A Zero Trust capability grants.
4. Policy Fabric decisions gate capture, projection, sharing, recall proposal, recall promotion, and continuation recording.
5. AgentPlane records execution evidence but does not own workspace semantics.
6. Agent Registry records agent/session/grant authority but does not own workspace semantics.
7. Memory Mesh receives review-only recall promotion packets by default.
8. Sociosphere records topology and estate registration only.

## Exposure classes

| Class | Description | Baseline decision |
| --- | --- | --- |
| Canonical context graph | Workroom-bound graph and refs | Internal workspace surface |
| Provider capture | Inbound context from provider or user handoff | Allowed only as workroom-bound captured context |
| Provider projection | Outbound provider-compatible view | Must be policy-checked and grant-bound |
| Share grant | Workspace access grant over a projection | Must be explicit and auditable |
| Recall candidate | Reviewable recall candidate from context | No automatic durable writeback |
| Recall promotion | Memory Mesh promotion packet | Review-only unless later approved |
| External continuation | Continuation outside the canonical workspace | Record lineage/evidence; do not assume revocation control |

## Required evidence

- Workroom or ProfessionalWorkroom ref
- ContextGraph ref when applicable
- Runtime binding ref when applicable
- Agent Registry authority binding ref for agent-mediated operations
- AgentPlane evidence ref for execution-mediated operations
- Policy Fabric decision ref for projection/share/recall operations
- MCP/A2A capability grant ref for mediated provider/tool/agent operations
- Platform record/evidence ref for runtime actions

## Open follow-up

The current lock uses `manifest_declared_refs_only`. A later network-aware materializer may add live commit SHA resolution, but that is out of scope for this baseline.
