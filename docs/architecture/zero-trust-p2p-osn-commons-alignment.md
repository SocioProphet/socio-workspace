# Zero-Trust P2P OSN / Commons Alignment

Version: v0.1
Status: draft control-plane profile
Owner: SocioSphere

Source research anchor: arXiv:2001.02611v1, *Peer-to-Peer based Social Networks: A Comprehensive Survey*.

## Purpose

This profile folds the P2P OSN survey requirements into the SocioProphet civic-stack program. It treats the platform as a zero-trust peer-to-peer online social network substrate for agentic commons, truth annealing, and falsifiable public knowledge work.

The profile is not an eighth reference model. It is a cross-cutting operating profile over TRM+, DRM+, SRM+, CGRM, PRM+, AgentPlane, SourceOS, PolicyFabric, ProCybernetica, HellGraph, Regis, and Delivery Excellence.

The central correction is:

```text
truth annealing is an application layer;
zero-trust P2P OSN / commons is the substrate profile.
```

## Four-fold architecture profile

The P2P OSN substrate is projected as four layers:

| Layer | SocioProphet mapping |
|---|---|
| Overlay | structured / unstructured / hybrid / multi-overlay routing, peer topology, churn handling, anti-eclipse posture |
| Storage + communication | SourceOS syncd, content addressing, replication, erasure coding, signed messages, pub/sub, unicast, multicast, access-controlled shared spaces |
| Social networking elements | identity, conversation, sharing, presence, relationships, groups, search, claims, tests, attestations, shared evidence spaces, slash topics |
| GUI | socioprophet-web, BearBrowser, SocioSphere views, operator dashboards |

## Required OSN primitives

SocioSphere should require every product-facing commons implementation to declare coverage for:

1. Identity.
2. Conversation.
3. Sharing.
4. Presence.
5. Relationships.
6. Groups.
7. Personal space management.
8. Social connection management.
9. Social graph traversal.
10. Synchronous and asynchronous communication.
11. Public and private communication.
12. Shared access-controlled spaces.
13. Search.

Knowledge artifacts must map into these primitives. A claim can be a post; a test can be a shared-space thread; an attestation can be a signed message; a replication log can be an async channel; an evidence workspace can be a shared group space.

## Non-functional requirement profile

The profile makes three bundles mandatory:

### Privacy

- confidentiality
- ownership privacy
- social-interaction privacy
- activity privacy

### Security

- channel availability
- channel authentication
- data integrity
- data authenticity
- non-repudiation only when it does not defeat anonymity requirements

### Metering

Metering is mandatory. Claims of decentralization, resilience, or privacy cannot be promoted unless the system emits measurements sufficient to falsify those claims.

Required metering classes:

- retrieval success rate
- bounded-hop lookup behavior
- update convergence
- stale-replica rate
- conflict rate
- search network cost
- churn impact
- availability under attack
- privacy/security test outcomes
- monitoring completeness

## Reputation rule

No global reputation oracle.

Reputation must be modeled as local/private inference plus cryptographic attestations, not a universal score. SocioSphere may route attestations and contextual trust signals, but it must not normalize them into platform-wide karma.

## Overlay/search/storage contracts

Every P2P commons implementation should declare:

```yaml
overlay:
  class: structured | unstructured | hybrid | multi-overlay
  routing_claim: string
  churn_claim: string
  eclipse_resistance_claim: string
search:
  mode: key_lookup | prefix | proximity | semantic | keyword | hybrid
  exact_lookup_claim: string
  network_cost_budget: string
storage:
  redundancy: replication | caching | erasure_coding | hybrid
  update_policy: pessimistic | optimistic | append_only | CRDT | event_sourced
  replica_discovery: coordinated | opportunistic | unknown
  conflict_policy: string
metering:
  required: true
  exported_signals: []
```

## Threat taxonomy

ProCybernetica should treat these as the initial canonical P2P OSN threat classes:

### Topology threats

- DoS
- DDoS
- MITM
- eclipse attack
- wrong routing forward / attrition
- identity theft
- churn attack

### Storage and lookup threats

- low-quality or degraded content
- false labeling
- worm propagation
- rational/free-rider attack
- storage attack
- retrieval attack
- index poisoning
- pollution attack
- query flooding

## Requirement to mechanism to measurement chain

Every major P2P commons claim should use this evidence shape:

```yaml
requirement: string
mechanism: string
measurement: string
adversarial_test: string
evidence_ref: string
policy_basis: string | null
owner: string
responsible_repo: string
```

Example:

```yaml
requirement: Rare artifact retrieval must work under churn.
mechanism: Structured overlay with coordinated replication and signed content-addressed artifact references.
measurement: Retrieval success rate, hop count, timeout rate, stale-replica rate, conflict rate.
adversarial_test: churn plus eclipse plus index poisoning.
evidence_ref: urn:evidence:p2p-osn:retrieval-under-churn:v0
policy_basis: urn:policy:p2p-osn:metering-required:v0
owner: SocioSphere
responsible_repo: SourceOS-Linux/sourceos-syncd
```

## Repo ownership map

| Concern | Canonical / primary repo | SocioSphere expectation |
|---|---|---|
| P2P OSN ontology/profile | `SocioProphet/ontogenesis` | Add overlay, peer, replication, search, monitoring, and threat semantics |
| Control-plane routing | `SocioProphet/sociosphere` | Maintain this profile and board/workflow routing |
| Local-first sync substrate | `SourceOS-Linux/sourceos-syncd` | Implement replication/update/conflict and local custody surfaces |
| Security/threat tests | `SocioProphet/ProCybernetica` | Maintain P2P threat taxonomy and test harness mapping |
| Metrics | `SocioProphet/delivery-excellence` | Score retrieval, convergence, privacy/security, and metering claims |
| Policy | `SocioProphet/policy-fabric` | Enforce access control, anonymity/non-repudiation tradeoffs, and placement/visibility rules |
| Runtime agents | `SocioProphet/agentplane` | Run truth-annealing agents as scoped plugins over shared spaces |
| Graph reasoning | `SocioProphet/hellgraph` | Query claim lattice and evidence graph |
| Entity registry | `SocioProphet/regis-entity-graph` | Register peer nodes, overlays, signed messages, claims, tests, indexes, and threat scenarios |
| Standards | `socioprophet-standards-knowledge`, `socioprophet-standards-storage`, `prophet-platform-standards` | Define portable schemas and contracts |

## Board projections

SocioSphere should route P2P OSN objects to these boards:

| Board | Objects |
|---|---|
| Overlay Governance | overlay class, peer topology, routing claims, churn claims |
| Storage and Replication | replicas, erasure policies, update propagation, conflict surfaces |
| Search and Retrieval | indexes, exact lookup claims, keyword/semantic search claims, network cost budgets |
| Privacy and Security | access control, anonymity, signatures, channel/authentication/integrity claims |
| Metering and Falsification | monitoring signals, measurement completeness, requirement-mechanism-measurement claims |
| Threat Validation | topology/storage/search threat scenarios and adversarial test results |
| Social Primitives | identity, conversations, sharing, presence, relationships, groups, shared spaces |

## Cross-stack binding

| Seven-model layer | P2P OSN profile binding |
|---|---|
| TRM+ | overlay, peer nodes, routing, anonymous channels, signed messages, attestation |
| DRM+ | personal spaces, shared folders/walls/forums, replication policy, content hashes, provenance, consent |
| SRM+ | identity, conversation, sharing, presence, relationships, groups, search, shared evidence workspaces |
| CGRM | access control, lawful basis, anonymity/non-repudiation tradeoff, community moderation without operator privilege |
| PRM+ | retrieval latency, hop count, availability, convergence, privacy/security tests, metering completeness |
| BRM+ | user, steward, verifier, relay, storage contributor, moderation participant, agent plugin |
| EnRM | edge locality, energy cost of replication/search, infrastructure exposure, device/network availability |

## Non-goals

This profile does not mandate one overlay implementation, one search mechanism, one incentive scheme, or one storage engine. It mandates that those choices be explicit, measurable, adversarially testable, and governable.
