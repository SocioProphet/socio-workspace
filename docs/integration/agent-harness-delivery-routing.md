# Agent Harness Delivery Routing

Status: v0.1 routing baseline  
Owner plane: SocioSphere for topology and workspace routing  
Metrics authority: `SocioProphet/delivery-excellence` and `SocioProphet/delivery-excellence-automation`

## Purpose

This document records the cross-estate routing decision for the Aden/Hive-derived agent harness lessons.

The lessons are useful across the estate, not only development. Runtime execution, policy gates, browser/terminal surfaces, memory, security checks, product proof, customer-safe readouts, bounties, inner-source collaboration, and corporate scoreboards all need a common operating loop.

SocioSphere records the topology and dependency direction. Delivery Excellence owns the performance stack, metrics, KPI/OKR scoreboards, operating cadence, work packaging, and customer-proof readouts.

## Routing decision

Use this authority split:

| Plane | Canonical authority | Role |
|---|---|---|
| Workspace topology | `SocioProphet/sociosphere` | declares repo roles, dependency direction, cross-estate routing, source exposure, and integration status |
| Delivery performance | `SocioProphet/delivery-excellence` | owns KPI/OKR definitions, scoreboards, operating cadence, work packaging, and proof-of-value readouts |
| Delivery automation | `SocioProphet/delivery-excellence-automation` | owns machine-readable contracts for recent repo activity, delivery metrics, scoreboards, customer proof, human-control events, and skill/MCP scoring |
| Runtime execution | `SocioProphet/agentplane` | owns bundles, execution, placement, run control, evidence, replay, session, promotion, and reversal artifacts |
| Policy and guardrails | `SocioProphet/policy-fabric`; `SocioProphet/guardrail-fabric` | owns policy gates, admission, grants, guardrails, judge/eval posture, and promotion policy |
| Agent identity and authority | `SocioProphet/agent-registry`; `SocioProphet/socioprophet-agent-standards`; `SourceOS-Linux/agent-machine` | owns agent identities, grants, activation decisions, revocation, and host/runtime activation semantics |
| Memory and context | `SocioProphet/memory-mesh` | owns recall/writeback, memory profiles, context packs, artifact pointers, and retention/sensitive-payload posture |
| Browser surface | `SourceOS-Linux/BearBrowser`; `SociOS-Linux/browser-use` | owns governed browser automation, browser events, credential posture, and browser evidence |
| Terminal/operator surface | `SourceOS-Linux/TurtleTerm`; `SourceOS-Linux/agent-term`; `SociOS-Linux/workstation-contracts` | owns operator commands, shell receipts, IPC conformance, terminal evidence, and local operator smoke paths |
| Security validation | `SocioProphet/SCOPE-D`; `SocioProphet/global-devsecops-intelligence` | owns skill/MCP/tool/browser/memory/graph risk validation and defensive security evidence |
| Product/customer surfaces | `SocioProphet/socioprophet`; `SocioProphet/prophet-platform`; `SocioProphet/prophet-workspace`; `mdheller/socioprophet-web`; `SociOS-Linux/socioslinux-web` | owns customer/operator-facing UX, proof surfaces, and product demos |

## Operating loop

The shared cross-estate loop is:

```text
Outcome -> Work Item -> Plan Graph -> Policy Gate -> Run -> Evidence -> Scoreboard -> Review -> Evolution Patch -> Promotion Gate
```

Delivery Excellence consumes evidence from runtime, policy, SourceOS, security, browser, terminal, memory, and product repos, then emits management-facing and customer-safe readouts.

SocioSphere should never duplicate Delivery Excellence scoreboards. It should link to them and enforce that repos are routed to the correct owner plane.

## Initial consumed signals

Delivery Excellence should consume at least these signal families:

- recent repo activity from GitHub commits, PRs, issues, releases, and workflow runs
- AgentPlane validation/run/replay/session/promotion artifacts
- Policy Fabric decisions, reports, exceptions, and promotion gates
- SourceOS activation decisions, release evidence, local-first service manifests, and shell receipts
- BearBrowser browser events, credential posture, automation compatibility, and build readiness
- TurtleTerm/agent-term operator smoke events, terminal receipts, and IPC/workstation conformance
- Memory Mesh context-pack refs, recall/writeback posture, and sensitive-payload decisions
- SCOPE-D security assessments for skills, MCP servers, tools, memory, browser, graph robustness, and prompt/tool poisoning
- product proof, demo readiness, and customer-safe readout artifacts

## Current integration artifacts

- `SocioProphet/delivery-excellence#9` — adds the agent harness delivery operating model.
- `SocioProphet/delivery-excellence-automation#7` — adds machine-readable agent harness metric contracts and examples.

## Non-goals

- Do not move scoreboards or KPI/OKR definitions into SocioSphere.
- Do not move runtime execution into Delivery Excellence.
- Do not make delivery metrics depend on proprietary cloud services.
- Do not count logs as evidence unless they are linked to validated evidence artifacts.
- Do not treat generated agent work as complete unless acceptance criteria and validation pass.

## Next routing tasks

1. Register Delivery Excellence as the explicit performance-stack owner in the integration ledger.
2. Register the agent harness metric contracts as a cross-estate consumed contract family.
3. Require new agent-harness work to declare owner plane, signal producer, scoreboard consumer, and proof-of-value readout path.
4. Generate a first cross-estate scoreboard snapshot from recent repo activity and known evidence refs.
