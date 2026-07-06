# Glossary & Ontology Versioning Process (three-layer)

**Status:** v0.1 — binds the ER/NER plan §9 three-layer terminology model to the existing **ontogenesis**
machinery. **Companion:** `er-ner-realignment-and-task-placement.md`; ontogenesis
`catalog/registry.ttl`, `shapes/*.shacl.ttl`, `svf/ontogenesis-semantic-validation-basic.json`,
`docs/how-to-add-a-module.md`.

## 1. Principle

Controlled terminology moves at three speeds. Glossary terms change fast; ontology classes change slowly
under compatibility review. Models retrain *after* terminology stabilizes, not before. This process layers
the plan's vocabulary→glossary→ontology model onto ontogenesis's layered Turtle + registry + SHACL + ledger
pipeline — it adds **no new ontology engine**; it defines how identity-prime terms (prime-topics, NER entity
classes, audience tags) flow through the one that exists.

## 2. The three layers ↔ ontogenesis

| Layer | Content | ontogenesis home | Change cadence |
|---|---|---|---|
| **Vocabulary** | aliases, abbreviations, token normalization, surface forms, spelling variants | `Lower/` bindings + JSON-LD `contexts/`; alias tables consumed by extractors/search analyzers | near-immediate (glossary delta) |
| **Glossary** | preferred label, alt labels, definition, scope/jurisdiction notes, usage examples | `Middle/` modules (SKOS `skos:prefLabel`/`altLabel`/`definition`) | fast; daily / on review |
| **Ontology** | classes, properties, constraints, mappings, provenance, policy semantics | `Upper/` + `Domains/` (OWL classes/properties) + `Alignments/` (GIST/FIBO/UCO/…) | slow; versioned, compatibility-gated |

Identity-prime terms map in: **prime-topics** and **NER entity classes** (PERSON, ORG, IDENTIFIER, …,
PRIME_TOPIC_MENTION) are ontology classes; their **surface forms / audience tags** are vocabulary; their
**definitions + scope notes** are glossary entries.

## 3. Update pipeline

```
new corpus / review signal
  → candidate term mining
  → alias clustering            (vocabulary delta)
  → glossary proposal           (skos: prefLabel/altLabel/definition, with provenance)
  → ontology mapping            (owl: class/property, alignment to GIST/FIBO/UCO/...)
  → SHACL shape validation      (shapes/*.shacl.ttl promotion gate)
  → version publish             (bump VERSION + module owl:versionInfo; registry.ttl og:semver)
  → reindex                     (Sherlock analyzers consume glossary delta)
  → retrain                     (only after enough examples; ER promotion gated on benchmark)
```

This is the ontogenesis `make validate → shacl → jsonld → build → ledger → verify → sbom → svf` chain, with
the term lifecycle layered on top.

## 4. Registration & versioning (follow ontogenesis conventions)

- New term module = a Turtle file in the right layer folder + an `og:Module` entry in `catalog/registry.ttl`
  carrying `og:layer`, `og:path`, `og:baseIRI`, `og:semver`, `og:status` (draft|stable|deprecated), and a
  Turtle header with `owl:versionInfo` + `dct:title`/`dct:description`.
- Namespaces under `https://socioprophet.github.io/ontogenesis/<layer-or-domain>#`.
- SHACL shapes under `shapes/` target the new classes (`sh:targetClass`, `sh:property`, `sh:message`).
- Releases use the named-tag pattern (`semantic-enterprise-vX.Y.Z`); `dist/` and `audit/` are CI-generated
  only. SVF declares claim scopes (schema_conformant, semantic_roundtrip_preserved, artifact_integrity).

## 5. Governance rules (plan §9.3, enforced via SHACL + SVF)

- Every new term carries **provenance** (who/when/source) — required by the glossary shape.
- Every deprecation carries a **replacement mapping** (`skos:exactMatch`/`owl:deprecated` + successor IRI).
- **Glossary** changes (labels/aliases/definitions) may publish on the fast lane.
- **Ontology** changes (classes/properties/constraints) require a **compatibility review** gate before the
  SemVer MAJOR/MINOR bump; breaking changes fail the SHACL/SVF promotion until migration shapes exist.
- Search analyzers + candidate generators consume **glossary deltas** quickly; **model retraining lags**
  controlled-terminology changes until sufficient labeled examples exist (avoids training on churn).

## 6. Consumers

- **NER/EL** (`extract.mentions.v1`) reads vocabulary (aliases) + glossary (entity-class definitions) and
  stamps `ontology_version` on every response.
- **Sherlock** (`search-index-record.v1`) reindexes on glossary publish; cites `index_version`.
- **Regis** decisions pin `policy_version`; ontology releases that change prime-topic classes ripple into the
  identity polytope and therefore require the compatibility gate before they can affect merges.
