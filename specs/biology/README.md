# Biological Analog Map (v0.1)

This folder is the **authoritative mapping** between our SourceOS + agentic stack and the reference biological signaling network (receptors → cascades → checkpoints → outcomes). The intent is not poetry; it is an **architecture contract** we can validate against.

## Why this exists
Cells stay alive by doing three things well:
1) Enforcing **typed ingress** (receptors)
2) Using **composable cascades** with explicit feedback/dampening
3) Making **irreversible commits** only behind hard checkpoints
4) Treating quarantine / apoptosis as a **success path**, not a failure

We mirror those properties with:
- TriTRPC adapters as receptors
- Event fabric (Kappa) as cytosolic signal field
- Promotion gates + policy-as-code as nucleus
- Kill-switch DAGs + containment as immune/apoptosis plane

## Files
- `pathway-map.v0.1.yaml` — machine-readable mapping: planes, receptors, pathways, checkpoints, and quarantine policy.

## Definition of Done (for this spec)
- All ingress classes we support are represented as receptors.
- Every pathway has explicit negative feedback controls.
- Every irreversible action is only possible via a checkpoint.
- Quarantine/apoptosis triggers and evidence requirements are explicit.
