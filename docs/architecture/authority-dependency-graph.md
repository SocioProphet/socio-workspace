# Authority Dependency Graph v0

Status: draft v0.1  
Owner: `SocioProphet/sociosphere`  
Tracking issue: `SocioProphet/sociosphere#326`  
Upstream reconciliation: `SocioProphet/ProCybernetica#49`

## Purpose

SocioSphere owns the estate topology and cross-repo control graph. The authority dependency graph is the authority-aware layer of that graph.

It records the specific cybernetic control path:

```text
source -> authority surface -> control effect -> target -> policy -> evidence -> cancellation / recovery
```

This is narrower than the general dependency graph. `registry/dependency-graph.yaml` records broad component dependency direction. `registry/authority-dependencies.yaml` records declared authority propagation: who or what may affect another target, under which policy, with which evidence, and with which cancellation semantics.

## Doctrine

The control law is:

```text
No invisible authority.
No undeclared control effect.
No control effect without policy reference.
No high-risk effect without evidence reference.
No revocable effect without cancellation binding.
No recovery without an explicit recovery or prove-clean path where applicable.
```

The authority dependency graph does not grant authority by itself. It makes declared authority inspectable, validates that references exist in the right ownership plane, and gives downstream systems a stable id for policy, evidence, and state-integrity binding.

## Ownership split

| Concern | Owner |
| --- | --- |
| Visible cognition/control loop and trust-surface seed | `SocioProphet/superconscious` |
| Estate authority-dependency registry and topology | `SocioProphet/sociosphere` |
| Policy admission, inheritance, cancellation, break-glass | `SocioProphet/policy-fabric` |
| Execution, run evidence, replay artifacts | `SocioProphet/agentplane` |
| Local state-integrity, diagnosis, repair, attestation | `SourceOS-Linux/sourceos-syncd` |
| Public cybernetic doctrine and conformance law | `SocioProphet/ProCybernetica` |

## Contract files

This tranche adds:

```text
docs/architecture/authority-dependency-graph.md
registry/authority-dependencies.yaml
schemas/authority-dependency.schema.json
examples/authority-dependencies/valid/agentplane-network-door.authority-dependency.json
examples/authority-dependencies/invalid/prose-only-authority.authority-dependency.json
tools/validate_authority_dependencies.py
```

## Object model

An `AuthorityDependency` has these required fields:

| Field | Meaning |
| --- | --- |
| `id` | Stable graph identifier. |
| `owner_repo` | Repo accountable for the edge. |
| `status` | Lifecycle state: `draft`, `active`, `deprecated`, or `blocked`. |
| `source` | Source repo/component/kind that can initiate the effect. |
| `target` | Target repo/component/kind that may be affected. |
| `authority_surface_refs` | Machine-readable refs to trust surfaces or equivalent authority declarations. |
| `control_effects` | Bounded effect vocabulary. |
| `policy_refs` | Policy or admission refs that govern the effect. |
| `evidence_refs` | Evidence contracts that prove use, denial, non-use, or replay posture. |
| `cancellation_binding_refs` | Policy/state refs that deny, revoke, quarantine, degrade, expire, or recover the effect. |
| `recovery_refs` | Recovery, repair, attestation, or prove-clean refs. |
| `related_refs` | Optional upstream issue, PR, ADR, or registry refs. |

## v0 control-effect vocabulary

The first vocabulary is deliberately small:

```text
read
write
execute
route
publish
persist_memory
promote
merge
deploy
replicate
quarantine
revoke
repair
model_route
network_egress
credential_access
browser_control
terminal_control
host_mutation
```

The vocabulary is not a permission system. It is a graph classification used to decide which references are mandatory.

## Effect-risk classes

For validation, these effects are high-risk in v0 and require explicit evidence references:

```text
execute
route
publish
persist_memory
promote
merge
deploy
replicate
quarantine
revoke
repair
model_route
network_egress
credential_access
browser_control
terminal_control
host_mutation
```

These effects are revocable in v0 and require cancellation bindings:

```text
execute
route
publish
persist_memory
promote
merge
deploy
replicate
model_route
network_egress
credential_access
browser_control
terminal_control
host_mutation
```

## Registry relationship

`registry/dependency-graph.yaml` remains the general dependency-direction registry.

`registry/authority-dependencies.yaml` is an overlay. It is used when a dependency carries authority, not merely implementation dependency.

For example:

```text
agentplane -> sourceos-syncd
```

as a general dependency might mean that AgentPlane consumes a SourceOS evidence contract.

The authority dependency overlay must say more:

```text
agentplane guarded invocation may request a SourceOS network-door plan
under a Policy Fabric policy reference
with AgentPlane evidence
and SourceOS state-integrity cancellation/recovery semantics.
```

## Validation expectations

`tools/validate_authority_dependencies.py` is dependency-free. It validates:

1. schema file shape;
2. registry file shape;
3. valid fixtures;
4. invalid fixtures;
5. required fields;
6. bounded status vocabulary;
7. bounded control-effect vocabulary;
8. high-risk effects have evidence refs;
9. revocable effects have cancellation bindings;
10. runtime-bearing or authority-bearing edges have authority-surface refs;
11. cancellation bindings preserve evidence by requiring at least one evidence ref;
12. prose-only authority is rejected.

## First fixture

The first valid fixture is intentionally cross-plane:

```text
AgentPlane guarded invocation
  -> SourceOS network-door plan
  -> Policy Fabric sourceos repo-context policy
  -> AgentPlane NetworkDoorPlanEvidence
  -> Policy Fabric cancellation binding
  -> SourceOS state-integrity recovery binding
```

This is a contract fixture, not a runtime mutation. It does not install a mesh, contact model providers, mutate firewall state, or perform host actions.

## Non-goals

- SocioSphere does not become the policy engine.
- SocioSphere does not become the execution engine.
- SocioSphere does not define Superconscious trust-surface semantics.
- SocioSphere does not define AgentPlane evidence artifact internals.
- SocioSphere does not define SourceOS local repair mechanics.
- This tranche does not implement runtime behavior.

## Next tranche

After this contract lands, downstream repos should add their side of the binding:

1. `SocioProphet/superconscious#10`: trust-surface authority-dependency binding.
2. `SocioProphet/policy-fabric#75`: cancellation binding contract.
3. `SocioProphet/agentplane#157`: authority-dependency evidence contract.
4. `SourceOS-Linux/sourceos-syncd#27`: state-integrity binding.
