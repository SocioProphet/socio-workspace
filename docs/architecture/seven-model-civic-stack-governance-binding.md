# Seven-Model Civic Stack Governance Binding

Version: v0.1
Status: draft control-plane binding
Owner: SocioSphere

Tracking issue: SocioProphet/sociosphere#323

Semantic anchors:

- SocioProphet/ontogenesis#80 — civic ORG/FOAF/vCard alignment
- SocioProphet/ontogenesis#81 — RationalGRL and OQL/OAC follow-up
- SocioProphet/ontogenesis#83 — merged civic alignment tranche
- SocioProphet/ontogenesis#85 — merged seven-model domain layer

## Purpose

This document defines how SocioSphere consumes the Ontogenesis Seven-Model Civic Operating Architecture as governance objects, boards, routing rules, workflow triggers, and conformance expectations.

SocioSphere coordinates the estate. It does not own ontology definitions, service implementation, policy execution, Gaia facts, runtime action dispatch, score calculation, or graph storage. It owns the control-plane projection: workspace registry, governed object routing, board/workflow expectations, dependency direction, conformance expectations, and cross-repo evidence chains.

The binding makes this chain operational:

```text
actor/person -> role/membership/post -> authority/policy -> service -> dataset -> runtime -> attestation -> observation -> score -> externality -> governance decision
```

It also prepares the RationalGRL rationale chain:

```text
actor -> goal/softgoal -> task/resource -> contribution/decomposition/dependency -> assumption/defeater -> evidence -> decision
```

## Source of semantic truth

| Semantic family | Canonical repo | SocioSphere role |
|---|---|---|
| Civic stack alignment | `SocioProphet/ontogenesis` | Track consumed ontology artifacts |
| CGRM | `SocioProphet/ontogenesis` | Route policy/governance objects and ownership |
| EnRM | `SocioProphet/ontogenesis` | Route Gaia environmental facts into governance surfaces |
| PRM+ | `SocioProphet/ontogenesis` | Route Delivery Excellence score objects |
| SRM+ | `SocioProphet/ontogenesis` | Route service governance objects |
| DRM+ | `SocioProphet/ontogenesis` | Route data governance objects |
| TRM+ | `SocioProphet/ontogenesis` | Route runtime/attestation objects |
| RationalGRL | `SocioProphet/ontogenesis` + `socioprophet-standards-knowledge` | Route rationale objects after the standard lands |
| OQL/OAC | `SocioProphet/ontogenesis` + standards repos | Route artifact/compiler/deployment objects after the standard lands |
| Zero-trust P2P OSN profile | `SocioProphet/ontogenesis` + `SourceOS-Linux/sourceos-syncd` + standards repos | Route overlay/storage/social/metering governance objects |

## Board-routable object families

### Agent and organizational accountability

Objects include `foaf:Agent`, `foaf:Person`, `org:Organization`, `org:OrganizationalUnit`, `org:OrganizationalCollaboration`, `org:Membership`, `org:Role`, `org:Post`, `party:Party`, `party:NaturalPerson`, `party:Organization`, `party:RoleAssignment`, and `legal:LegalEntity`.

SocioSphere projection: owner, steward, responsible post, review actor, approval actor, escalation actor, accountable organization.

### Civic governance

Objects include `cgrm:Jurisdiction`, `cgrm:Authority`, `cgrm:Policy`, `cgrm:Right`, `cgrm:Obligation`, `cgrm:Permit`, `cgrm:Sanction`, `cgrm:LegalBasis`, `cgrm:AccessBasis`, `cgrm:PublicConsultation`, `cgrm:CivicDecision`, and `cgrm:PolicyChangeEvent`.

SocioSphere projection: policy governance board, legal/access-basis review, consultation workflow, decision ledger handoff, sanction/obligation routing, appeal/review dependency.

### Service governance

Objects include `srm:Service`, `srm:ServiceComponent`, `srm:Interface`, `srm:SLA`, `srm:PolicyGuard`, `srm:LifecycleStage`, `srm:Dependency`, `srm:ProviderBinding`, `srm:ConsumerBinding`, and `srm:ServiceChangeEvent`.

SocioSphere projection: service ownership board, dependency risk board, lifecycle promotion workflow, SLA review workflow, interface change workflow, policy guard review.

### Data governance

Objects include `drm:Dataset`, `drm:Record`, `drm:Identifier`, `drm:Provenance`, `drm:Consent`, `drm:AccessBasis`, `drm:QualityMetric`, `drm:DataContract`, `drm:DataAccessGrant`, `drm:LineageEvent`, and `drm:DataSubject`.

SocioSphere projection: data stewardship board, access-basis workflow, lineage/provenance review, data contract workflow, quality remediation queue.

### Environment governance

Objects include `enrm:EnvironmentFactor`, `enrm:ResourceStock`, `enrm:CarryingCapacity`, `enrm:Externality`, `enrm:Exposure`, `enrm:Hazard`, `enrm:Vulnerability`, `enrm:CriticalInfrastructure`, `enrm:GridCarbonIntensity`, `enrm:EmissionsEstimate`, and `enrm:EnvironmentalEvidence`.

SocioSphere projection: Gaia overlay board, environmental externality review, infrastructure exposure board, environmental evidence review, public-value impact workflow.

### Performance and delivery governance

Objects include `prm:Outcome`, `prm:PublicValueOutcome`, `prm:Indicator`, `prm:Target`, `prm:Observation`, `prm:Scorecard`, `prm:MetricContract`, `prm:EquityMetric`, `prm:ResilienceMetric`, `prm:TrustMetric`, `prm:EnvironmentalExternalityMetric`, and `prm:AuditCompletenessMetric`.

SocioSphere projection: Delivery Excellence scorecard board, target breach workflow, scorecard review, evidence completeness queue, public-value outcome review.

### Runtime and attestation governance

Objects include `trm:Runtime`, `trm:Workload`, `trm:TrustAnchor`, `trm:Attestation`, `trm:NetworkSlice`, `trm:EdgeNode`, `trm:ObservabilitySignal`, `trm:PolicyEnforcementPoint`, `trm:Deployment`, `trm:SupplyChainEvidence`, and `trm:ArtifactDigest`.

SocioSphere projection: runtime assurance board, attestation review workflow, deployment evidence workflow, policy enforcement point review, observability signal routing.

### Rationale governance

Expected objects after the RationalGRL track lands: Actor, Goal, Softgoal, Task, Resource, Contribution, Decomposition, Dependency, Argument, Assumption, Defeater, Satisfaction.

SocioSphere projection: rationale board, architecture decision evidence review, softgoal trade-off workflow, defeater/blocker queue, dependency propagation graph.

### Artifact and compiler governance

Expected objects after the OQL/OAC track lands: OQLPlan, OACManifest, CompilerAdapter, Artifact, EvidenceVaultRecord, Placement, Status, Signature, SBOM, Attestation.

SocioSphere projection: artifact admission board, compiler adapter review, provenance completeness workflow, federation placement workflow, evidence vault verification queue.

### Zero-trust P2P OSN / commons governance

Expected objects from the P2P OSN profile: Overlay, PeerNode, StorageReplica, ReplicationPolicy, ErasureCodingPolicy, SearchIndex, SharedSpace, SignedMessage, PresenceEvent, RelationshipEdge, Group, MonitoringSignal, ThreatScenario, RequirementClaim, MechanismClaim, MeasurementClaim.

SocioSphere projection: overlay governance board, search/retrieval test board, storage/replication health board, privacy/security claim board, metering completeness board, threat-model validation queue.

## Board types

| Board | Primary objects | Producer repos | Consumer repos |
|---|---|---|---|
| Service Governance | `srm:Service`, `srm:Dependency`, `srm:SLA` | Ontogenesis, Prophet Platform, AgentPlane | Delivery Excellence, HellGraph |
| Policy Governance | `cgrm:Policy`, `cgrm:LegalBasis`, `cgrm:Obligation` | Ontogenesis, PolicyFabric | AgentPlane, ProCybernetica |
| Data Governance | `drm:Dataset`, `drm:DataContract`, `drm:LineageEvent` | Ontogenesis, Regis, Prophet Core | PolicyFabric, HellGraph |
| Environment Governance | `enrm:Exposure`, `enrm:Externality`, `enrm:EnvironmentalEvidence` | Ontogenesis, Gaia | Delivery Excellence, SocioSphere UI |
| Delivery Governance | `prm:Target`, `prm:Observation`, `prm:Scorecard` | Delivery Excellence | SocioSphere boards, ProCybernetica |
| Runtime Assurance | `trm:Runtime`, `trm:Workload`, `trm:Attestation` | AgentPlane, ProCybernetica | PolicyFabric, HellGraph |
| Rationale Governance | Goal/Softgoal/Task/Resource/Contribution/Dependency | Ontogenesis, standards-knowledge | Delivery Excellence, SocioSphere boards |
| Artifact Governance | OQL/OAC artifact/evidence/placement objects | AgentPlane, standards-storage, platform-standards | PolicyFabric, HellGraph, Regis |
| P2P Commons Governance | overlay/storage/social/metering/threat objects | SourceOS, Ontogenesis, standards repos | ProCybernetica, Delivery Excellence, HellGraph |

## Required object envelope

Every board-routable object must be projectable into this envelope:

```yaml
id: string
type: string
semantic_ref: string
canonical_repo: string
producer_repo: string
consumer_repos: []
owner: string
responsible_post: string | null
policy_basis: string | null
service_ref: string | null
dataset_ref: string | null
runtime_ref: string | null
overlay_ref: string | null
gaia_environment_ref: string | null
delivery_score_ref: string | null
evidence_ref: string | null
provenance_ref: string | null
lifecycle_state: draft | proposed | active | blocked | superseded | retired
risk_state: nominal | watch | degraded | blocked | incident
created_at: string
updated_at: string
```

## Workflow triggers

SocioSphere should route workflows from these triggers:

1. Ontogenesis ontology or shape change.
2. PolicyFabric policy decision or denial.
3. AgentPlane runtime action dispatch, run capsule, delegation, or attestation.
4. Delivery Excellence score breach or missing evidence.
5. Gaia environmental exposure or externality threshold breach.
6. ProCybernetica incident, control failure, or evidence-pack update.
7. Regis entity/relationship registration or split/merge event.
8. HellGraph query validation failure or SHACL failure visibility event.
9. RationalGRL defeater/blocker once #81 lands.
10. OQL/OAC artifact admission or placement status once #81 and standards land.
11. P2P overlay/storage/search/privacy/security/metering test failure once the zero-trust commons profile lands.

## Cross-repo invariants

1. Ontogenesis owns semantics.
2. SocioSphere owns control-plane routing and conformance projection.
3. Delivery Excellence owns score contracts and delivery metrics.
4. Gaia owns environmental facts and world-model overlays.
5. PolicyFabric owns executable policy decisions.
6. AgentPlane owns runtime action evidence.
7. ProCybernetica owns assurance, risk, control, incident, threat-model, and evidence-pack doctrine.
8. HellGraph owns graph query/reasoning substrate.
9. Regis owns concrete entity and relationship registration.
10. Prophet Platform standards own cross-platform contract packaging.
11. SourceOS owns local-first P2P storage/communication substrate implementation.

## Non-goals

SocioSphere does not define the ontology classes, implement service runtime behavior, calculate Delivery Excellence scores, supply Gaia environmental facts, execute policies, or implement P2P overlay/storage mechanics.

SocioSphere makes those objects governable, routable, reviewable, and visible across the estate.
