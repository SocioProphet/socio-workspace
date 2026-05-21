# Identity Is Prime protocol fixtures

These fixtures anchor the Sociosphere conformance lane for Identity Is Prime, Regis Entity Graph, Authority Concordance Rex (ACR), Agent Registry integration, and the HELL-ER hazard-governed entity-resolution service function.

The fixture set is intentionally small in this first pass. It establishes deterministic semantics for:

- policy polytope membership
- forbidden identity mixtures
- token congruence and non-escape violations
- ACR golden-record proof shape
- HELL-ER identity release packs, contradiction preservation, hazard classification, and no-silent-release invariants

Each fixture should eventually be backed by executable validators under `tools/conformance/` and by TRIT RPC request/response fixtures for the relevant service surfaces.

## HELL-ER service function

HELL-ER belongs inside Identity Is Prime but remains a distinct symbiotic service function.

Identity Is Prime defines what prime identity means. HELL-ER governs how identity evidence is classified, resolved, contradicted, transformed, redacted, released, revoked, and reviewed.

The HELL-ER protocol lives under:

- `hell-er/README.md`
- `hell-er/schemas/`
- `hell-er/fixtures/`
- `hell-er/expected/`

Initial HELL-ER schemas:

- `hell-er/schemas/prime-atom.v1.schema.json`
- `hell-er/schemas/contradiction-object.v1.schema.json`
- `hell-er/schemas/release-pack.v1.schema.json`

Initial HELL-ER fixture:

- `hell-er/fixtures/release_pack.internal_operational.synthetic.valid.json`

## Required result vocabulary

- `VERIFIED`: the claim or state satisfies the pinned policy and schema versions.
- `REFUTED`: the claim or state structurally violates policy, admissibility, or non-escape rules.
- `UNDECIDABLE`: the current abstraction lacks enough evidence to prove or refute.
- `STALE`: the fixture or certificate pins outdated schema, policy, resolver, or template versions.
- `REQUIRES_REVIEW`: the fixture requires steward review before graph mutation or publication.
- `REDACTED`: the object is valid but withheld under the release class.
- `REVOKED`: the atom, credential, or release is no longer live.
- `EXPIRED`: the supporting evidence is no longer valid for current use.

## Determinism fields

Conformance outputs should pin the following where available:

- `schema_version`
- `policy_version`
- `resolver_version`
- `template_version`
- `release_template_version`
- `hazard_classifier_version`
- `fixture_version`
- `input_hash`
- `result_hash`
- `certificate_hash`
- `release_pack_hash`
- `ledger_pointer`
- `graph_snapshot_ref`

## First fixture families

- `fixtures/polytope.valid.json`
- `fixtures/polytope.invalid.json`
- `fixtures/token.non_escape.violation.json`
- `fixtures/acr.golden_record.proof.json`
- `expected/polytope.valid.result.json`
- `hell-er/fixtures/release_pack.internal_operational.synthetic.valid.json`
- `hell-er/expected/release_pack.internal_operational.synthetic.valid.result.json`

Follow-on fixtures should add transition graph, no-admissible-path, zeta audit, agent manifest rejection, TRIT RPC wire examples, HELL-ER query-negative/not-absent examples, contradiction flattening rejection, silent merge/split rejection, and external unredacted-release rejection.
