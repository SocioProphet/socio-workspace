# HELL-ER Protocol

## Hazard-Governed Entity Resolution for Identity Is Prime

Status: Draft v0.1  
Home: `protocol/identity-is-prime/hell-er/`  
Parent workstream: Identity Is Prime  
Service role: Symbiotic service function paired with the core prime identity substrate  
Release posture: Review draft / synthetic fixtures only

## Purpose

HELL-ER is the hazard-governed entity-resolution and identity-release service function for the Identity Is Prime protocol.

Identity Is Prime defines the doctrine: identity is not a flat record. Identity is a context-scoped, time-versioned, policy-constrained composition of prime identity atoms.

HELL-ER defines the operating service: how identity evidence is classified, resolved, contradicted, transformed, redacted, released, revoked, and reviewed.

The system exists to prevent unsafe identity collapse, unsafe release, and unsafe recomposition.

HELL-ER is not a standalone product. It is a protocol and service layer inside the Identity Is Prime workstream.

## Name and lineage

The name **HELL-ER** is intentional.

It is a play on:

- **HADES** — the high-assurance desensitization lineage and predecessor pattern;
- **Hell / Heller** — the Heller-derived mnemonic and authorial lineage;
- **ER** — Entity Resolution, the operational kernel.

The intended parse is:

```text
HADES -> HELL
HELLER -> HELL-ER
ER -> Entity Resolution
```

The architecture keeps the HADES discipline of deterministic, policy-bound, auditable transformation, but moves the governed unit from sensitive fields to identity-bearing graph slices.

Short form:

> HADES protected data values. HELL-ER governs identity meaning.

Canonical form:

> PIF/HELL-ER is the HADES-descended, Heller-derived architecture for context-scoped identity resolution, contradiction preservation, and policy-bound release.

## Relationship to Identity Is Prime

HELL-ER belongs inside Identity Is Prime but remains a distinct service function.

| Layer | Responsibility |
|---|---|
| Identity Is Prime | Doctrine, conformance lane, prime identity semantics |
| PIF | Ontology of prime atoms, context, assurance, release, and contradiction |
| HELL-ER | Hazard classification, entity resolution, contradiction preservation, leakage/lifecycle control, release-pack generation |
| Regis Entity Graph | Graph substrate for identity states, concordance links, ledgers, and certificates |
| ACR | Authority concordance, source-to-canonical crosswalks, golden projections, and point-in-time proofs |
| Holmes | Investigation, contradiction review, and evidence-case construction |
| Sherlock Search | Retrieval over evidence, source records, graph pointers, ledger pointers, and proof artifacts |
| Agent Registry | Least-privilege agents for observation, resolution, proof, search, review, and audit |

HELL-ER is symbiotic with the core identity model:

- Identity Is Prime defines what identity is.
- HELL-ER decides how identity evidence may be resolved and released.

## Service boundary

Recommended service methods:

```text
heller.classify_hazard
heller.resolve_subject
heller.record_contradiction
heller.evaluate_release
heller.emit_release_pack
heller.redact_for_audience
heller.register_redress
heller.revoke_or_expire_atom
heller.evaluate_merge
heller.evaluate_split
```

These methods should be represented as protocol fixtures first, then TriTRPC fixtures, then runtime service endpoints where needed.

## Core concepts

### Prime atom

A prime atom is the smallest identity-bearing assertion treated as atomic for a declared context and purpose.

A prime atom carries an atom id, atom type, context, provenance, sensitivity class, assurance state, lifecycle state, and policy tags. No atom is admissible without provenance.

### Context

A context declares the purpose, audience, served population, policy regime, and operational setting for identity resolution. The same subject may resolve differently in different contexts.

### Hazard envelope

The hazard envelope is the first governance gate. It classifies release and resolution risk before identity evidence is transformed or exposed.

Hazard classes include direct identifier, quasi-identifier, authenticator material, civil-proof material, institutional attribute, role or entitlement attribute, contextual event data, artifact/provenance data, behavioral or derived signal, sensitive preference, restricted professional/IP material, regulated data element, and synthetic demo value.

### Entity/Evidence graph

HELL-ER works over graph state, not flat records. Canonical node families include Subject, Alias, Identifier, Evidence, Attribute, Credential, Authenticator, Organization, Role, Event, Artifact, Source, Assertion, Policy, Contradiction, and ReleasePack.

Canonical edge families include claims, evidenced_by, issued_by, observed_in, affiliated_with, authenticates, federates_to, derived_from, contradicts, supersedes, revokes, supports, required_for, and released_under.

### Contradiction object

A contradiction object records incompatible assertions or graph states. Contradictions are preserved; they are not silently flattened.

### Query-negative

A query-negative means a query did not return a fact. It does not mean the fact is absent. HELL-ER must preserve this distinction in release packs, proof artifacts, and contradiction ledgers.

### Release pack

A release pack is the governed output object for a declared audience and release class. It contains release class, audience, context declaration, hazard profile, subject graph summary, prime atom ledger, contradiction ledger, assurance vector, lifecycle policy, redress queue, and machine-readable annex.

## Result vocabulary

HELL-ER inherits and extends the Identity Is Prime conformance vocabulary:

- `VERIFIED`: the subject state or release decision satisfies pinned policy and schema versions.
- `REFUTED`: the state structurally violates policy, admissibility, contradiction, non-escape, or release rules.
- `UNDECIDABLE`: the abstraction lacks enough evidence to prove or refute.
- `STALE`: the fixture, evidence, certificate, schema, policy, resolver, or release template is outdated.
- `REQUIRES_REVIEW`: steward review is required before mutation, release, merge, split, or promotion.
- `REDACTED`: the object is valid but withheld under the release class.
- `REVOKED`: the atom, credential, or release is no longer live.
- `EXPIRED`: the supporting evidence is no longer valid for current use.

## Determinism fields

Conformance outputs should pin:

- `schema_version`
- `policy_version`
- `resolver_version`
- `release_template_version`
- `hazard_classifier_version`
- `fixture_version`
- `input_hash`
- `result_hash`
- `certificate_hash`
- `release_pack_hash`
- `ledger_pointer`
- `graph_snapshot_ref`

A repeated clean checkout with the same pins should produce equivalent results.

## Core invariants

HELL-ER validators must enforce these invariants:

1. No atom without provenance.
2. No atom without sensitivity label.
3. No meaningful assertion without context.
4. No release without release class.
5. No release without policy tag.
6. No query-negative converted into fact-absent.
7. No unresolved contradiction silently flattened.
8. No merge without merge audit artifact.
9. No split without split audit artifact.
10. No expired or revoked evidence supporting a live assertion without review.
11. No contextual identity escalated into civil proof without proofing evidence.
12. No authenticator assurance collapsed into identity-proofing assurance.
13. No derived behavioral atom treated as direct evidence.
14. No external release of unredacted direct identifiers without explicit authorization.
15. No Sherlock search result treated as canonical truth without Regis/ledger backing.
16. No Holmes finding promoted to canonical graph mutation without policy and steward route.

## Required fixture families

Initial fixture families should include:

```text
prime_atom.valid.json
prime_atom.missing_provenance.invalid.json
query_negative_not_absent.valid.json
contradiction.open.valid.json
contradiction.flattened.invalid.json
release_pack.self_view.valid.json
release_pack.external_redacted.valid.json
release_pack.missing_policy.invalid.json
release_pack.unredacted_external.invalid.json
merge.audit.valid.json
merge.silent.invalid.json
split.audit.valid.json
split.silent.invalid.json
civil_proof_escalation.invalid.json
expired_evidence_support.invalid.json
```

## Schema set

The first schema tranche in this directory defines:

- `schemas/prime-atom.v1.schema.json`
- `schemas/contradiction-object.v1.schema.json`
- `schemas/release-pack.v1.schema.json`

Recommended future schemas:

- `context-declaration.v1.schema.json`
- `hazard-envelope.v1.schema.json`
- `entity-evidence-node.v1.schema.json`
- `entity-evidence-edge.v1.schema.json`
- `assurance-vector.v1.schema.json`
- `release-policy.v1.schema.json`
- `merge-split-artifact.v1.schema.json`
- `redress-item.v1.schema.json`

## Synthetic demo fixture policy

HELL-ER examples must use synthetic demo data unless explicitly approved.

Permitted demo subject name:

```text
Michael Heller
```

All other demo attributes should be synthetic placeholders unless separately approved.

Expected demo outcome:

```text
context_resolved access: VERIFIED
civil_identity_proof: UNDECIDABLE / not proofed
authenticator_binding: pending or separate
stale affiliation contradiction: retained
external release: redacted
```

## TriTRPC service candidates

Candidate service namespace:

```text
heller.identity.v1
```

Candidate methods:

```text
ClassifyHazard
ResolveSubject
RecordContradiction
EvaluateRelease
EmitReleasePack
RedactForAudience
RegisterRedress
RevokeAtom
ExpireEvidence
EvaluateMerge
EvaluateSplit
```

## Relationship to Regis / ACR

HELL-ER does not replace Regis or ACR.

- Regis stores graph state and proof certificates.
- ACR performs authority concordance, source-to-canonical crosswalks, and point-in-time golden projections.
- HELL-ER governs whether identity graph slices, assertions, contradictions, and release packs are safe to resolve, transform, or release.

Boundary:

```text
Regis = graph state
ACR = authority concordance
HELL-ER = hazard-governed resolution and release
```

## Relationship to Holmes and Sherlock

Holmes consumes HELL-ER contradiction objects, graph snapshots, ledger pointers, and release decisions to assemble investigative cases.

Sherlock indexes HELL-ER release packs, graph pointers, contradiction summaries, and evidence references for retrieval.

Neither Holmes nor Sherlock writes canonical identity truth directly.

## Acceptance criteria

HELL-ER v0.1 is acceptable when:

- schemas validate prime atoms, contradiction objects, and release packs;
- fixtures cover valid and invalid release paths;
- conformance validator rejects missing provenance;
- conformance validator rejects missing policy;
- query-negative cannot be interpreted as fact-absent;
- silent merge and silent split fixtures are refuted;
- external release of unredacted direct identifiers is refuted;
- synthetic demo fixture emits a release pack with contradiction retention;
- service method fixtures are deterministic under pinned schema/policy/resolver versions.

## Open questions

1. Should `heller.identity.v1` be a distinct TriTRPC namespace or part of `regis.proof.v1`?
2. Should HELL-ER release packs be signed independently or through Regis proof certificates?
3. Which HELL-ER objects belong in Ontogenesis first?
4. Should contradiction existence be visible in external redacted release packs?
5. What is the minimal assurance vector required for v0.1?
6. Which PIF atoms require independent signatures?
7. Should redress be a first-class service method in v0.1 or v0.2?
8. Should HELL-ER own selective disclosure or delegate to a credentials service?
9. What privacy metric gates release?
10. How should graph-neighborhood leakage be estimated?

## Initial implementation sequence

1. Add minimal JSON schemas for prime atom, contradiction object, and release pack.
2. Add synthetic valid and invalid fixtures.
3. Extend `tools/conformance/validate_identity_is_prime_fixtures.py` to discover `hell-er/fixtures`.
4. Add deterministic expected result files.
5. Add TriTRPC request/response fixture skeletons.
6. Update the Identity Is Prime architecture doc to describe HELL-ER as a symbiotic service function.
7. Only then wire Prophet Platform runtime service consumption.

## Final summary

HELL-ER is the governed service function that makes Identity Is Prime operationally safe.

It is HADES-descended, Heller-derived, and entity-resolution-centered.

It does not define identity by itself. It governs how prime identity evidence is resolved, contradicted, released, redacted, revoked, and reviewed.
