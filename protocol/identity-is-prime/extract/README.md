# Extraction Contracts (NER / EL / Events / GrASP)

Method and pattern schemas for the extraction phase of the Identity-Prime spine.

| File | Role |
|---|---|
| `schemas/extract-mentions.v1.schema.json` | NER + entity-linking method (emits `regis.source-record.v1` mentions; overlapping spans) |
| `schemas/extract-events.v1.schema.json` | Event / relation extraction (Event-IR-aligned) |
| `schemas/grasp-pattern.v1.schema.json` | GrASP multilayer interpretable pattern (claim/evidence/argumentation/compliance/policy-trigger) |
| `fixtures/grasp_pattern.compliance_sentence.valid.json` | The deck's `[noun.person][shall][VB][the][IN]` compliance pattern |

## GrASP → `extract.mentions.v1` binding

GrASP (Greedy Augmented Sequential Patterns, IBM Research; open-source) is an **interpretable** extractor for
the phenomena the local model handles poorly (argumentation, claims, evidence-type, compliance). It binds in:

- GrASP's per-token augmentation layers (POS / named-entity / sentiment / hypernym / syntactic / lexicon /
  topic) **are** the multilayer `source-record.mentions` model — including overlapping / multi-labeled spans.
- A `grasp-pattern` match emits a `mention` (via `emits.mention_entity_class`) and contributes a named,
  human-readable feature to `edge-witness` / `resolution-decision` (`emits.edge_witness_feature`) — satisfying
  the "explainable, not just probabilistic" invariant.
- `target_phenomenon = policy_trigger | consent_cue` lets GrASP **mine the CONSTRAINTS-family triggers** that
  gate activation, feeding the policy polytope.
- Pattern mining is a consumer of the glossary candidate-term loop and runs local-first on `CITIZEN_FOG`
  (CPU-light, interpretable, audit-friendly).
