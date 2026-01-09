# 035 - Schema Distribution and Resolution (Embedded + Federated Registries)

## Status
- Version: v0
- Normative for schema resolution across TriRPC and capability bundles.

## Goals
- Deterministic offline execution using embedded schemas
- Scalable ecosystem distribution via federated registries
- Schema identity by content fingerprint (no name-only trust)

## Schema Identity
Every schema MUST be identified by:
- fp256 = sha256(canonical_schema_bytes) as lowercase hex
Optional:
- fp64 = first 16 hex chars of fp256 (hint only; never authoritative)

## Canonicalization (MUST)
The repo MUST define canonical bytes for each schema format:
- Avro: canonical schema bytes rule
- SchemaSalad: canonical YAML/JSON normalization rule

Fingerprints MUST be computed over canonical bytes.

## Distribution Modes
### Mode A - Embedded (MUST for core)
Agents MUST embed:
- TriRPC core schemas (envelope/value/error/bundle manifest)
Agents SHOULD embed:
- all schemas required by their public surface and expected workloads

### Mode B - Federated Registry Fetch (MAY)
When a schema fingerprint is not available locally, an implementation MAY fetch from registries if:
- policy allows remote fetch
- fetched bytes hash to the requested fp256
- signatures/trust checks pass (if required by policy)
- schema is cached/pinned locally thereafter

## Resolution Order (MUST)
1) Embedded bundle schemas
2) Local cache (content-addressed store)
3) Org registry list (ordered)
4) Community registry list (ordered)
5) Peer exchange (optional; policy gated)

## Failure Semantics (MUST)
- If required schema cannot be resolved: fail closed.
- If fetched schema hash mismatch: reject and mark registry suspect.

## Registry API (v0 minimum)
- GET /schemas/{fp256} -> bytes + metadata
- GET /schemas/{fp256}/meta -> fingerprint + size + mime + signatures

## Policy Hooks
Policies MUST be able to declare:
- allow_remote_fetch: true/false
- allowed_registries: list
- required_signers / trust roots
- max_schema_size_bytes
