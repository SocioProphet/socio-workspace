# Inspection Without Inspection Standard v0.1

This standard defines the SocioProphet governance pattern for debugging, monitoring, and auditing privacy-locked or decentralized data systems without exposing raw private examples.

The invariant is simple: raw private data is never the inspection object. Every inspection request becomes a typed task, executable selection predicate, privacy-bounded proxy artifact, comparison ledger entry, and governed diagnostic claim.

## Canonical doctrine

1. Declare the inspection task as one of T1 through T6.
2. Compile the task into device-selection and local-filter predicates.
3. Train an auxiliary model under a declared user-level differential-privacy envelope.
4. Export only proxy artifacts, scores, summaries, and comparison records permitted by the privacy boundary.
5. Reject publication unless the artifact declares data touchpoints, DP parameters, fidelity requirements, and memorization-gate results.
6. Route the result to publish, review, or quarantine.

## Task taxonomy

| Task | Name | Inspection intent |
|---|---|---|
| T1 | sanity_check | Random examples from a target training distribution. |
| T2 | mistake_debugging | Examples selected by misclassification or model error. |
| T3 | unknown_or_oov | Unknown labels, OOV tokens, or unsupported classes. |
| T4 | poor_slice_performance | Low-accuracy slices, devices, users, cohorts, or segments. |
| T5 | human_labeling | Unlabeled examples requiring annotation or training use. |
| T6 | distribution_mismatch | Private/decentralized density high relative to public/training density. |

## Generator capability split

`explicit_likelihood` generators expose `sample()` and `logp(x)`. They can support the T6 likelihood lens: `log p_private(x) - log p_public(x)`.

`implicit_sampler` generators expose `sample()` only. They may support visual or discriminator-based comparison, but they must not be used for likelihood-ratio T6 unless an explicit likelihood adapter is declared.

## Canonical files

- `SPEC.md` — normative standard.
- `schemas/*.schema.json` — machine-readable artifact contracts.
- `examples/*.json` — positive examples for T3, T4, and T6.
- `../../tools/validate_inspection_without_inspection.py` — validation lane.

## Validation

```bash
python3 tools/validate_inspection_without_inspection.py
make inspection-without-inspection-validate
```

## Estate placement

SocioSphere owns the canonical standard and validation lane. Policy Fabric owns publication gates. AgentPlane owns executor capability contracts. Ontogenesis owns ontology and SHACL shapes. Gaia owns world-model coverage-gap profiles. Alexandrian Academy owns teaching/canonization. ProCybernetica owns defensive/audit control mappings.
