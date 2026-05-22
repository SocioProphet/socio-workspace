# CHRONOS Evidence Loop

Status: nomenclature and boundary doctrine.

## Naming

Product / external term:

```text
CHRONOS Evidence Loop
```

Internal doctrine term:

```text
Corpus-to-Governed-Carrier Loop
```

Implementation artifact family:

```text
corpus-loop v0 / v1 / v1.1
```

The repository may continue to use `corpus-loop-*` for filenames, schemas, Make targets, fixtures, and reports. Product-facing language should prefer `CHRONOS Evidence Loop`.

## Definition

The CHRONOS Evidence Loop converts a governed research corpus into a sequence of plane-owned carriers: evidence carriers, semantic carriers, policy carriers, bounded action carriers, audit carriers, and coordination packets.

Each carrier is typed, validated, provenance-bearing, and explicitly non-authorizing outside its owning plane.

## Carrier definition

A carrier is a plane-owned, machine-validatable boundary object that transports a governed artifact from one stage of the system to another while preserving provenance, claim status, validation state, and explicit non-authority boundaries.

Equivalently:

```text
Carrier = payload + provenance + schema + validation + boundary semantics
```

A carrier should answer five questions:

```text
What is being carried?
Where did it come from?
What validates it?
What authority does it have?
What authority does it explicitly not have?
```

## Carrier levels

Carrier schema:

```text
The machine-readable contract shape.
```

Carrier instance:

```text
One concrete payload satisfying that contract.
```

Carrier surface:

```text
Schema + examples + validator + documentation + negative fixtures.
```

Example:

- Carrier surface: Sherlock source-quality answer trace.
- Carrier schema: `schemas/source-quality-answer-trace.v0.schema.json`.
- Carrier instance: `fixtures/source-quality-answer-trace/valid.confirmed-bibliographic.json`.

## Current carrier chain

| Plane | Owner repo | Carrier surface |
|---|---|---|
| Evidence | `SocioProphet/sherlock-search` | Source-quality answer trace |
| Ontology | `SocioProphet/ontogenesis` | Corpus event semantics |
| Policy | `SocioProphet/policy-fabric` | Governed action policy decision |
| Agent carrier | `SocioProphet/agentplane` | Bounded action loop carrier |
| Ledger | `SocioProphet/model-governance-ledger` | Governance record checks |
| Coordination | `SocioProphet/sociosphere` | Manifest, resolver report, demo packet, customer-safe readout |

## Boundary

A carrier is not a runtime executor, not a permission grant, not a truth guarantee, and not a product workflow by itself.

A carrier makes the next plane able to reason safely.

SocioSphere may coordinate carriers, resolve pinned carrier paths, assemble demo packets, and emit customer-safe readouts. SocioSphere does not become the authority for the downstream carrier internals.

## Implementation mapping

`corpus-loop v0`:

```text
Static coordination manifest and local carrier validation.
```

`corpus-loop v1`:

```text
Pinned downstream carrier commits and generated workbench data.
```

`corpus-loop v1.1`:

```text
Pinned-path resolver, live-found report, and committed resolution validation.
```

Customer-safe product language should describe this as the CHRONOS Evidence Loop, backed by the `corpus-loop-*` implementation family.

## Non-claims

This doctrine does not claim:

- live runtime execution;
- autonomous external effects;
- production storage integration;
- completed corpus normalization;
- patent or license clearance for artifact reuse;
- downstream implementation ownership transfer into SocioSphere.

## Next product tranche

The next tranche should be a bounded read-only demo packet assembler for the CHRONOS Evidence Loop. It may assemble and display governed artifacts. It must not execute downstream actions or move authority out of owner repos.
