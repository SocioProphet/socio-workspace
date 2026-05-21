# Integration Status

This file is the canonical current-state ledger for cross-repo integration
facts that were previously repeated in multiple places.

## Current state

### Epistemic Governance
- Canonical standard anchor: `standards/epistemic-governance/`
- Protocol surface: `protocol/epistemic-governance/v1/`
- Estate ownership map: `registry/epistemic-governance.yaml`
- Reference application lineage: Debater 2.0 / Argument Hygiene / Ruleset v1.3.0
- Status: proposed cross-repo standard and protocol surface
- Current scope: documentation, lifecycle law, promotion law, detector/counter-test bindings, topic catalog, run spec, migration ledger, and estate ownership map
- Non-scope in SocioSphere: downstream detector implementation, UI implementation, policy compiler implementation, SourceOS event-store implementation, HolographMe projection runtime, and DeliveryExcellence dashboards
- Downstream targets:
  - `SocioProphet/ProCybernetica` for epistemic control doctrine and discursive control node law
  - `SocioProphet/policy-fabric` for epistemic intervention, profile projection, retention, drift, and promotion policy as code
  - `SocioProphet/agentplane` for executable detector, counter-test, replay, fixture evaluation, and policy-backtest bundles
  - `SourceOS-Linux/sourceos-syncd` for local-first discourse events, SourceOS lane mapping, tombstones, repair events, and replayable state integrity
  - `SocioProphet/HolographMe` and/or `human-digital-twin` for consent-scoped Reasoning Calibration Projections
  - `SocioProphet/delivery-excellence` for evidence coverage, repair success, false-positive appeal rate, contradiction half-life, review fatigue, and release-readiness metrics
  - `SocioProphet/ontogenesis` for claim ontology, evidence classes, detector vocabulary, counter-test vocabulary, contradiction semantics, and repair-action semantics

### Agent Harness Delivery Routing
- Routing doc: `docs/integration/agent-harness-delivery-routing.md`
- Workspace topology owner: `SocioProphet/sociosphere`
- Delivery-performance owner: `SocioProphet/delivery-excellence`
- Delivery-automation owner: `SocioProphet/delivery-excellence-automation`
- Runtime evidence owner: `SocioProphet/agentplane`
- Policy/guardrail owners: `SocioProphet/policy-fabric` and `SocioProphet/guardrail-fabric`
- Security validation owners: `SocioProphet/SCOPE-D` and `SocioProphet/global-devsecops-intelligence`
- Status: routing baseline captured
- Current scope in SocioSphere: topology, dependency direction, source exposure, and integration status
- Non-scope in SocioSphere: scoreboards, KPI/OKR definitions, delivery operating cadence, runtime execution, and customer proof dashboards
- Downstream artifacts:
  - `SocioProphet/delivery-excellence#9` for the delivery operating model
  - `SocioProphet/delivery-excellence-automation#7` for machine-readable metric contracts and examples

### TritRPC
- Canonical upstream: `SocioProphet/TriTRPC`
- Workspace declaration: `manifest/workspace.toml` repo `tritrpc`
- Materialization path: `third_party/tritrpc`
- Status: active workspace dependency

### Trit-to-Trust
- Status: removed as an independent workspace dependency
- Notes/content: folded into TritRPC docs during de-commingling

### Edge capabilities upstream bindings
- Narrative binding doc: `docs/architecture/upstream-bindings-edge-capabilities.md`
- Machine-readable baseline map: `registry/upstream-bindings-edge-capabilities.yaml`
- Drift check tool: `tools/check_upstream_edge_capabilities.py`
- Airshare baseline: `KuroLabs/Airshare master @ 92a144dbf7af2d2a5fbcfbfb3078f4c9ecf86c13`
- cdncheck baseline: `projectdiscovery/cdncheck main @ 68bfbae83a4aad30d9cbb17c30bb44c32e10affb`
- papers baseline: `marawangamal/papers main @ 1ae5061b7ec9d2ab7d0e37ad254ad435a58fc5ec`
- Fast-LLM baseline: `ServiceNow/Fast-LLM main @ 7a7129d7775cea459cb19a48be0d831ccc7b4e7d`
- Status: captured in repo; policy disposition lives in the architecture note and operational baseline lives in the registry + drift check tool

## Resolved migration timeline

| Stage | Snapshot |
|---|---|
| Initial coupling | `tritrpc` + `trit-to-trust` tracked together |
| First pinning pass | both pinned at `v0.1.0` |
| Second pinning pass | `tritrpc v0.1.1 @ 6091e55`, `trit-to-trust v0.1.1 @ 68186ab` |
| De-commingled state | TritRPC retained, Trit-to-Trust removed from workspace deps |
| Current steady state | TritRPC remains as standalone core dependency |

## Interpretation rule

If another document references Trit-to-Trust as an active workspace dependency,
treat that content as historical context. Current behavior is defined by
`manifest/workspace.toml` + `manifest/workspace.lock.json`.

For edge-capability upstreams, treat the registry file plus drift-check tool as
the operational baseline, and treat the narrative binding doc as the policy /
disposition explanation.

For Epistemic Governance, treat `standards/epistemic-governance/` plus
`registry/epistemic-governance.yaml` as the SocioSphere standard/ownership
baseline. Downstream repos own implementation according to their canonical
namespace responsibilities.

For Agent Harness Delivery Routing, treat `docs/integration/agent-harness-delivery-routing.md`
as the routing baseline. SocioSphere records topology and owner-plane routing;
Delivery Excellence owns delivery metrics and scoreboards.
