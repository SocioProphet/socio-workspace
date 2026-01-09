# 034 - Morloc Interop Core (Polyglot Execution Under a Common Type System)

## Status
- Version: v0
- Normative for Sociosphere polyglot execution.

## Goal
Enable multi-language implementations of capabilities under a common type system so workflows can compose functions across languages without handwritten glue.

We adopt the Morloc design model (common type system + explicit normalization via pack/unpack + pool-based execution) as a core design choice, implemented via TriRPC wire format + Avro schemas + SchemaSalad packaging.

## Scope
- Common "General Types" used on the wire
- Native type mappings per language
- Pack/Unpack normalization ("Packable" contract)
- Execution model (controller + language pools)
- Requirements for language bindings and conformance

Non-scope:
- High-level workflow scheduling semantics (Apache Beam alignment)
- Cryptographic trust policies (attestations standard)

## Definitions
- General Type: language-independent type with canonical on-wire representation.
- Native Type: language-specific runtime representation.
- Pack/Unpack: deterministic conversion between native and canonical general representations.

## General Type Core (v0)
The wire-visible general type universe MUST include:

### Primitives
- Unit
- Bool
- Int{8,16,32,64}
- UInt{8,16,32,64}
- Float32, Float64
- Bytes
- String (UTF-8)

### Collections
- List<T>
- Tuple<T1..Tn>

### Derived Canonical Types (platform conventions)
- Optional<T> (sum type)
- Result<T,E> (sum type)
- Map<K,V> (canonicalized; see Pack/Unpack)
- Record (wire encoded as Tuple + field names defined by schema)
- Table (wire encoded as one canonical form; see Pack/Unpack)
- ArtifactRef (hash + optional locator)

## Sum Types (MUST)
Externally-facing schemas MUST represent sum types using a tagged pattern:
- tag: stable string (or fp64 hint)
- value: union containing allowed branches

Optional<T> MUST be represented as {tag: "none"|"some", value: null|T}
Result<T,E> MUST be represented as {tag: "ok"|"err", value: T|E}

## Pack/Unpack Normalization Contract (MUST)
Complex native types that vary across languages MUST provide explicit Pack/Unpack rules to a canonical general form.

### Pack rules (examples)
- Map<K,V> MUST pack to one of:
  A) List<Tuple<K,V>>  OR
  B) Tuple<List<K>,List<V>>
  The platform MUST choose one as canonical for v0 and declare it in Appendix A.

- Record MUST pack to Tuple ordered by schema field order.
- Table MUST pack to a canonical table encoding (row or column) declared in Appendix A.

### Determinism
Pack and Unpack MUST be deterministic and total for supported inputs. If a value cannot be normalized, the binding MUST emit a typed error with a stable error code.

## Execution Model (v0)
A controller process orchestrates language pools (one pool per runtime).
- Calls are routed to the correct pool based on capability implementation metadata.
- Inputs/outputs are transported as TriRPC envelopes.
- Pools MUST be able to decode/encode TriRPC core envelopes + values.

## Language Binding Requirements (MUST)
For each supported language runtime, the binding MUST provide:
1) Codec: TriRPC Envelope + Value encode/decode (Avro binary)
2) Schema resolution: embedded bundle + optional registry fetch (fingerprint verified)
3) Native type mapping table: General Type <-> Native Type
4) Pack/Unpack registry: pluggable per type family
5) Streaming: incremental decode/encode of framed envelopes
6) Error mapping: stable error codes + structured error payload

## Conformance
A runtime/binding MUST pass:
- TriRPC v0 Conformance Suite vectors relevant to its supported surface
- Pack/Unpack golden tests for declared complex types

## Appendix A - Type Mapping Tables (REQUIRED)
This appendix MUST be filled with:
- Canonical Map encoding choice (A or B)
- Canonical Table encoding choice (row or column)
- Timestamp/Duration encoding rules (safe integer constraints)

## Appendix B - Initial language set (RECOMMENDED)
- Rust, Go, Python, TypeScript/Node
Additional languages MAY be added with conformance vectors and mapping tables.
