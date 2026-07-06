# Masking, Tokenization & GrASP Extraction — Privacy-Enforcement & Interpretable-Extraction Layer

**Status:** v0.1 — aligns two IBM Research assets (High-Assurance Data Desensitisation / *Chameleon* tokens;
*GrASP* pattern mining) to the SocioProphet stack.
**Companions:** Catalog Gateway PDP (`prophet-platform/docs/strategy/PROPHET_DATA_CATALOG_DESIGN.md` §5.2/§6.2),
Identity-Prime spine (`er-ner-realignment-and-task-placement.md`), Metadata Standards (`1SP_Metadata_Standards_v0_1`),
contracts under `protocol/identity-is-prime/{masking,extract}/`.

## 1. Purpose

Two named gaps get their mechanism here:

1. **Masking parity with IBM Watson Knowledge Catalog** — WKC's strongest card is runtime dynamic masking /
   tokenization. Our `distribution_class` was metadata-only. This design adopts the *published* primitives —
   **Chameleon (domain-scoped, cross-domain-unlinkable) tokens** and **key-evolving (updatable) tokenization** —
   as the enforcement layer, and *exceeds* WKC on two structural axes WKC cannot: every masking decision is a
   **verified-compute receipt**, and tokens are **structurally un-linkable across domains**.
2. **Interpretable extraction** — **GrASP** is the explainable engine behind `extract.mentions.v1` for the
   linguistic phenomena (argumentation, claims, evidence-type, compliance) the local model handles poorly.

Provenance note: both are IBM Research. **GrASP is open-source** (adopt directly). Chameleon /
key-evolving tokenization are **published cryptography** — reimplemented in our own crate (sovereign posture),
not taken as IBM product.

## 2. Masking / Obfuscation / Tokenization

### 2.1 The scheme spectrum (what each is for)

| Scheme | Reversible? | Use | Contract field |
|---|---|---|---|
| reversible / length-preserving encryption | yes | recover original w/ key | `tokenization-profile.scheme` |
| **format-preserving (FPE)** | yes | keep field shape (numeric/alpha) so it still validates | `preserve.format` |
| **semantic-preserving (SPE)** | yes | keep checksums valid (LUHN/IBAN), separators | `preserve.checksum/semantic` |
| **Chameleon token** | yes (governed) | domain pseudonym; deterministic *in-domain*, **not cross-domain-linkable** | `scheme=chameleon_token`, `cross_domain_linkable=false` |
| legacy AN10 token | yes | 10-digit legacy format | `scheme=legacy_token_an10` |
| HMAC pseudonym / one-way hash / redact / suppress / generalize | **no** | strong irreversible desensitisation | `reversibility=one_way` (enforced) |

### 2.2 Key invariants (mapped to the spine)

- **Cross-domain non-linkability** (`cross_domain_linkable: false`) is the crypto realization of the
  Identity-Prime **scope-realm sovereignty** model and the `no_health_adtech` policy veto. It directly
  mitigates "side-channel leakage between datasets."
- **Homomorphic domain tweaks** move a pseudonym between realms with no cleartext exposure — backing the
  EdgeWitness **congruence lane** (NonceStream / modular reachability) and modeled as a governed
  `masking-decision` with `requested_op = re_tokenize` + `target_domain`.
- **Key-evolving tokenization**: rotation emits an **epoch tweak** that migrates tokens consistency-preservingly
  (no full re-tokenise), so key rotation/revocation does **not** break append-only DecisionLedger replay or
  sequence-neutrality. Modeled by `tokenization-profile.key.{key_epoch,update_tweak_ref}`.
- **HSM-backed, FIPS 140-2 L3, KMIP/PKCS#11** — uses the `HSM` scope realm; key handles only, never material.
- **Re-identification = governed, audited, reversible release**: gated on an OpenID-Connect **profile
  attribute**, requires a mandatory **reason-for-action**, supports separation-of-duty, and is sealed with a
  **BEACON_COMMIT** receipt. It is a HELL-ER `evaluate_release` / `redact_for_audience` and may emit a release
  pack. Modeled by `masking-decision.re_identification`.

### 2.3 The PDP (Policy Decision Point)

The masking PDP sits in the **Catalog Gateway** (and the workspace read path). At read / export / activation /
re-identify / re-tokenize time it evaluates realm + audience + policy polytope and returns a
**`masking-decision.v1`**: a `verdict` (allow / allow_masked / deny / review_required), the per-field
`applied_transforms`, any `re_identification` block, the active `side_channel_mitigations`, and a `receipt`
(policy-decision ref + optional BEACON_COMMIT). **The decision is itself evidence** — that is the moat vs WKC,
whose masking produces no verifiable artifact.

### 2.4 Risk calculus

Adopt the El Emam "Seven States of Data" control-vs-release matrix (governance / operational / technical /
contractual controls ↔ tokenisation + anonymisation level) as the rubric behind `distribution_class` and the
exodus `policy-gate` checks: the less organizational/technical control downstream, the stronger the required
data-risk reduction. The four re-identification risks (external-data combination; access to a reversible
scheme; access to identifying data; cross-dataset side channel) map to the
`masking-decision.side_channel_mitigations` enum.

## 3. GrASP — interpretable extraction

GrASP learns ranked, gap-tolerant, **multilayer** patterns (POS / NER / sentiment / hypernym / syntactic /
lexicon / topic) from positive **and negative** examples, selected by information gain with redundancy control.
It is the explainable extractor behind `extract.mentions.v1`:

- GrASP layers **are** the `source-record.mentions` multilayer model (overlapping / multi-labeled spans).
- A match emits a `mention` and a **named feature** into `edge-witness` / `resolution-decision` explanations —
  the "explainable, not just probabilistic" invariant, with human-readable patterns.
- `target_phenomenon = compliance_sentence | policy_trigger | consent_cue` lets GrASP **auto-discover the
  CONSTRAINTS-family triggers** that gate activation — feeding the policy polytope and ContractForge.
- Claim / evidence / argumentation patterns feed **Holmes** cases and **Sherlock** proposed-claims.
- Pattern/term mining is a consumer of the glossary candidate-term loop; CPU-light and interpretable, it runs
  local-first on `CITIZEN_FOG` and supports the bias/ethics review the audience-tagging template requires.

Contract: `extract/schemas/grasp-pattern.v1.schema.json` (+ the `[noun.person][shall][VB][the][IN]` fixture).

## 4. How the layers compose

```
GrASP finds        →  policy polytope decides   →  tokenization enforces      →  receipt seals
(claims, compliance    (allow / allow_masked /       (Chameleon domain token,      (policy-decision +
 cues, CONSTRAINTS      deny / review; the            FPE/SPE, key-epoch,           BEACON_COMMIT; the
 triggers)              no_health_adtech veto)        HSM; re-id w/ reason)         decision is evidence)
        │                        │                            │                          │
   extract.mentions      masking-decision.verdict     tokenization-profile        masking-decision.receipt
   + grasp-pattern       + forbidden_mixture          + masking-decision           (verified-compute)
```

The whole chain rides the same verified provenance spine — masking + obfuscation + tokenization fused with
explainable extraction, which is precisely what lets us match WKC's masking *and* out-prove it.

## 5. New contracts added (all validate, draft 2020-12)

- `protocol/identity-is-prime/masking/schemas/tokenization-profile.v1.schema.json`
- `protocol/identity-is-prime/masking/schemas/masking-decision.v1.schema.json`
- `protocol/identity-is-prime/masking/fixtures/masking_decision.{health_adtech_deny,reidentify_with_reason}.valid.json`
- `protocol/identity-is-prime/extract/schemas/grasp-pattern.v1.schema.json` + compliance fixture

## 6. Next steps

1. Implement the **Chameleon / key-evolving tokenization crate** (own implementation of the published primitive)
   with KMIP/PKCS#11 + HSM backing; wire it behind the masking PDP.
2. Wire the **masking PDP into the Catalog Gateway** read path (the WKC-parity deliverable) emitting
   `masking-decision` + BEACON_COMMIT.
3. Adopt **GrASP** (open-source) as an `extract.mentions.v1` provider for the claim/evidence/compliance lanes;
   mine `policy_trigger` patterns for the CONSTRAINTS family.
4. Bind audience-tagging `tag_assignment` to `masking-decision` so subject ids are tokenized per realm.
