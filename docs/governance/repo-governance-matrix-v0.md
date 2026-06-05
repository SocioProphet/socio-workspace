# SocioProphet repository governance matrix v0

Status: draft
Date: 2026-04-26
Owner: Sociosphere governance layer

This matrix classifies current SocioProphet estate repositories by governance role. It prevents roadmap, standards, runtime, and provenance repositories from being treated as interchangeable authority sources.

## Governance classes

- `canonical`: authoritative repositories allowed to define current platform contracts, runtime behavior, release gates, transport semantics, execution semantics, ontology terms, public surface behavior, or governance state.
- `promotion-candidate`: active repositories that need scope hardening, canonical consumers, validation, or ADR/Sociosphere registration before becoming authority sources.
- `provenance-only`: historical, archival, salvage, mirror, or experimental material. Evidence, not authority.
- `archive-retire`: superseded repository that should be archived rather than mined, promoted, or reactivated. Evidence only; no active extraction backlog.

## Canonical repositories

| Repository | Primary function | Authority boundary |
|---|---|---|
| `SocioProphet/socioprophet` | Public/application surface, surface inventory, schemas, semantic registry, UI, control-plane material | Public surface behavior and repo-local contracts. Generalized standards should graduate out. |
| `SocioProphet/prophet-platform` | Core platform contracts, capabilities, release/publication gates, registry publication, platform services | Platform release and publication machinery. |
| `SocioProphet/sociosphere` | Workspace governance, decision-plane registration, build intelligence, propagation awareness | Cross-repo build intelligence and governance state. |
| `SocioProphet/agentplane` | Execution control plane: bundle, validate, place, run, evidence, replay | Agent execution and evidence semantics. |
| `SocioProphet/TriTRPC` | Deterministic authenticated RPC and transport semantics | Transport/protocol semantics. |
| `SocioProphet/ontogenesis` | RDF/OWL/JSON-LD ontology engineering, SHACL gates, contexts, ontology catalog | Ontology terms and SHACL validation. |

## Promotion candidates

| Repository | Function | Promotion condition | Risk |
|---|---|---|---|
| `SocioProphet/policy-fabric` | Cross-platform policy fabric | Promote when canonical repos import it as authoritative policy source or enforcement package. | Policy duplication across repos. |
| `SocioProphet/prophet-platform-standards` | Reusable platform standards | Promote when referenced by `prophet-platform` release gates and Sociosphere registration. | Standards drift from runtime platform. |
| `SocioProphet/prophet-workspace` | Workspace model and implementation lane | Promote when Sociosphere delegates concrete workspace behavior to this repo. | Scope overlap with `sociosphere`. |
| `SocioProphet/socioprophet-agent-standards` | Agent standards | Promote when adopted by `agentplane` and `socioprophet` as shared contract. | Competing with `agentplane` local definitions. |
| `SocioProphet/socioprophet-standards-storage` | Storage and incident-intelligence standards | Promote when storage contracts are imported by runtime or platform repos. | Storage semantics fragment across platform/app layers. |
| `SocioProphet/socioprophet-standards-knowledge` | Knowledge-context, publication, masking, tokenization standards | Promote when wired into `ontogenesis`, `socioprophet`, and knowledge surfaces. | Knowledge semantics split across docs/surfaces/ontology. |
| `SocioProphet/gaia-world-model` | Auditable world-model scaffolding | Promote when GAIA domain model is explicitly imported by platform or ontology spine. | Domain scope outpaces validation. |
| `SocioProphet/slash-topics` | Governed topic packs and semantic BI outputs | Promote when outputs feed live surface ontology, search, or analytics. | Topic taxonomy drift from `config/surfaces.json`. |

## Archive-retire repositories

| Repository | Use | Restriction |
|---|---|---|
| `mdheller/socioprophet-old` | Superseded historical implementation | Archive. Do not mine for current doctrine, do not promote, and do not treat as a salvage backlog source. |

## Provenance-only by default

| Repository/pattern | Use | Restriction |
|---|---|---|
| `SocioProphet/socioprophet-web-medium` | Historical web material | Must not define current public surface behavior. |
| `SocioProphet/tritrpc-notes-archive` | TriTRPC notes archive | Must not supersede `TriTRPC`. |
| WIP salvage or mirror branches/repos | Recovery and audit continuity | Must be explicitly promoted before use as authority. |
| One-off integration scaffolds | Experiment capture | Must not define global standards without ADR or Sociosphere registration. |

## Authority boundaries

1. Public surface behavior belongs in `socioprophet` unless it is reusable platform behavior.
2. Platform release gates and publication mechanics belong in `prophet-platform`.
3. Cross-repo awareness and build-intelligence registration belongs in `sociosphere`.
4. Agent execution semantics belong in `agentplane`.
5. Transport semantics belong in `TriTRPC`.
6. Ontology terms and SHACL validation belong in `ontogenesis`.
7. Standards repos require explicit import, ADR, or registration to be authoritative.
8. Provenance repos are evidence, not authority.
9. Archive-retire repos are not extraction backlogs; they should be archived unless a later explicit governance reversal is recorded.
