# Zachman / Agent-Unit / Civic Stack Alignment

Version: v0.1
Status: draft control-plane profile
Owner: SocioSphere

Source design input: Zachman Framework resynthesis; Agent-Unit ontology; Environment primitive; ORG/FOAF/FIBO integration; legacy SOA-to-agentic-enterprise synthesis.

## Purpose

This document aligns the Zachman 6x6 framework, the Agent-Unit ontology, the seventh Environment primitive, the ORG/FOAF/FIBO organizational stack, and the legacy SOA-to-agentic-enterprise migration into SocioSphere's civic-stack governance plane.

The Zachman matrix becomes a completeness and forensic-coverage discipline. It does not replace the Seven-Model Civic Stack. It supplies the orthogonal interrogation grid used to test whether a governance object is complete enough to be operational, evidentiary, and recursively composable.

## Core thesis

Every governable unit must be representable across:

```text
What, How, Where, Who, When, Why, Environment
```

and across viewpoint strata:

```text
Ecosystem / Scope / Business Model / System Model / Technology Model / Detailed Representations / Functioning Enterprise
```

The six classic Zachman interrogatives remain orthogonal. The seventh primitive, Environment, is the typed boundary through which exogenous conditions perturb all six. The Ecosystem suprarow is the row in which an enterprise becomes one agent inside a larger ecology of regulators, vendors, markets, infrastructure, adversaries, communities, and planetary constraints.

## Zachman primitives as Agent-Unit roots

| Zachman column | Agent-Unit primitive | Civic-stack binding | Examples |
|---|---|---|---|
| What | Artifact | DRM+, PRM+, TRM evidence | datasets, claims, model artifacts, SBOMs, certs, profiles, release manifests |
| How | Capability | SRM+, AgentPlane runtime | services, workflows, skills, tests, compiler adapters, OPC UA actions |
| Where | Locale | TRM+, EnRM, ORG Site | endpoints, topics, device paths, jurisdictions, edge nodes, cloud regions |
| Who | Principal | ORG/FOAF/FIBO, CGRM | people, service principals, organizations, posts, memberships, authorities |
| When | Event | PRM+, PROV/TIME, lifecycle | schedules, incidents, release trains, telemetry, change events, aperture events |
| Why | Motive | CGRM, PRM+, RationalGRL | policies, goals, softgoals, obligations, remedies, SLAs, adversary objectives |
| Environment | Environment / Aperture | EnRM, Gaia, SourceOS, ProCybernetica | regimes, hazards, quotas, norms, outages, market shocks, ecological constraints |

## Viewpoint strata

| Row | SocioSphere use |
|---|---|
| Ecosystem | Cross-estate and exogenous-field governance: regulators, vendors, standards bodies, communities, adversaries, infrastructure, planetary constraints |
| Scope | Controlled vocabulary, boundary conditions, glossary, investigation or project frame |
| Business Model | Duties, rights, promises, consent flows, product/service intent, accountability |
| System Model | Logical services, state transitions, trust zones, claims/tests/attestations |
| Technology Model | Protocols, versions, ciphers, endpoints, cloud/edge/runtime choices |
| Detailed Representations | Schemas, IDLs, IaC, policy bundles, certs, SBOMs, test vectors |
| Functioning Enterprise | Live telemetry, incidents, tickets, traces, support interactions, signed events |

## AgentUnit governance contract

Every AgentUnit must publish six bundles plus an Aperture bundle:

```yaml
agent_unit:
  id: string
  what_bundle: /state/ artifacts, schemas, content hashes, retention rules
  how_bundle: /cap/ capabilities, preconditions, effects, cost model
  where_bundle: /net/ endpoints, topics, trust zones, jurisdictions
  who_bundle: /id/ DID, keys, roles, responsible organization/post
  when_bundle: /time/ schedules, SLAs, event windows, time sync source
  why_bundle: /policy/ goals, constraints, decision policy, escalation logic
  environment_bundle: /aperture/ observables, commitments, hazards, quotas, jurisdictions, regime model
```

The required atomic proof tuple is:

```text
<Principal, Capability, ArtifactDelta, Locale, Event, Motive, Environment>
```

Operationally:

```yaml
principal_did: string
capability_id: string
artifact_delta_sha256: string
locale_uri: string
event_time: RFC3339
motive_id: string
environment_regime_id: string
kid: string
msgid: uuid
trace_id: uuid
```

## Environment and Aperture

Environment is the partially observed exogenous field in which agents operate: physical, ecological, economic, legal, infrastructural, cultural, and adversarial conditions.

Every AgentUnit must declare an Aperture. An Aperture is the explicit boundary interface between the AgentUnit and its Environment.

Required Aperture fields:

```yaml
aperture_id: string
observables: []
commitments: []
exposures: []
controls: []
quotas: []
jurisdictions: []
regime_model: string
```

Regime switches emit signed Aperture Events. They bind exogenous changes to endogenous behavior changes, which prevents inside-only causal fallacies.

## ORG/FOAF/FIBO integration

SocioSphere should project organizational facts as Agent-Unit Who/Where/Why evidence:

| ORG / FOAF / FIBO term | AU primitive | SocioSphere projection |
|---|---|---|
| `foaf:Agent` | Principal | actor or service principal |
| `org:Organization` | Principal | accountable organization |
| `org:FormalOrganization` + FIBO | Principal | legal entity with identifiers and jurisdiction |
| `org:OrganizationalUnit` | Principal | internal responsibility boundary |
| `org:Membership` | Who relation | role-bearing assignment and duty path |
| `org:Role` | Who / How | responsibility semantics and capability constraint |
| `org:Post` | Who / How | office/position that can own authority independent of incumbent |
| `org:Site` + vCard/GeoSPARQL | Locale | jurisdiction, placement, exposure, environment boundary |
| `org:ChangeEvent` + PROV/TIME | Event | dated organizational or authority transition |

## Economic and industry extensions

Formal organizations should carry standard identifiers where available:

- LEI: `^[A-Z0-9]{18}[0-9]{2}$`
- DUNS: `^[0-9]{9}$`
- EIN: `^[0-9]{2}-[0-9]{7}$`
- VAT/EORI/CAGE/ABN/Companies House/RN/BN as scheme-tagged identifiers

Industry classifications should be SKOS concepts where possible:

- NAICS
- ISIC
- NACE
- schema.org / GoodRelations for public commerce interoperability
- FIBO/LCC for legal and jurisdictional semantics

## Legacy SOA migration rule

Legacy ESB/SOA components are not discarded. They are agentized.

| Legacy SOA object | Agentic replacement |
|---|---|
| WebSphere Messaging Engine | event fabric + attestation bus |
| ModelStore | knowledge graph + content-addressed model/artifact registry |
| ModelServices | AgentUnit capabilities with pre/postconditions |
| KPI Runtime Services | PRM+ Objective / Scorecard AgentUnits |
| Event Correlation Services | evidence/risk/incident correlation AgentUnits |
| OPC UA Proxy / Wrapper | OPC UA bridge AgentUnits |
| Database / WebService / OPC adapters | typed adapter AgentUnits with provenance and policy guards |
| SPARQL endpoint | retained as semantic query surface, extended through HellGraph |

## Required governance boards

This profile adds three board families to the civic-stack binding:

| Board | Objects | Purpose |
|---|---|---|
| Completeness Matrix Board | Zachman cell coverage records | Find missing What/How/Where/Who/When/Why/E evidence across rows |
| AgentUnit Assembly Board | AU bundles, Apertures, lifecycle states | Govern agent construction, attestation, deployment, degradation, retirement |
| SOA Modernization Board | legacy components, agentized wrappers, proof tuples | Track migration from ESB/adapters to event fabric and attested AgentUnits |

## Validation expectations

SocioSphere should later validate:

1. Every AgentUnit has six bundles plus an Aperture.
2. Every Capability has preconditions, effects, fallback behavior, and regime applicability.
3. Every action emits the atomic proof tuple.
4. Every org:Site has placement, jurisdiction, and environment exposure.
5. Every org:ChangeEvent has PROV/TIME and evidence linkage.
6. Every service has legal basis, responsible post, interface, SLA, and attestation.
7. Every dataset/model has content hash, lineage, and access basis.
8. Every low-count PRM observation follows small-n discipline.

## Relation to the Seven-Model Civic Stack

| Seven-model layer | Zachman/AU binding |
|---|---|
| EnRM | Environment, Aperture, Ecosystem row |
| CGRM | Why/Motive, Who/Principal, policy and duty paths |
| PRM+ | When/Event, What/Artifact, observations and scorecards |
| BRM+ | Who/Principal, Why/Motive, value network and economic roles |
| SRM+ | How/Capability, Where/Locale, services and interfaces |
| DRM+ | What/Artifact, provenance, identifiers, datasets, lineage |
| TRM+ | Where/Locale, How/Capability, Event/Attestation, runtimes |

## Non-goals

SocioSphere does not define the Zachman/AU ontology modules. Ontogenesis should own canonical terms. SocioSphere owns control-plane projection, board routing, gap visibility, and conformance expectations.
