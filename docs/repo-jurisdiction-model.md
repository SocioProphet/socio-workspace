# Repo Jurisdiction Model

Status: Boundary Atlas v0.1 companion.

## Principle

A repository is a jurisdiction when it is the authoritative producer of one or more typed artifacts and the declared owner of the evidence contract attached to those artifacts.

Jurisdiction is not the same as ownership in GitHub. A repo may contain code without being authoritative for a claim. A repo becomes authoritative only when its boundary declaration names the artifact, claim mode, sufficiency type, trust roots, and downstream consumers.

## Jurisdiction record

Each jurisdiction records:

- `boundary_class`: the role this repo plays in the estate.
- `jurisdiction`: the concise responsibility statement.
- `owned_artifacts`: authoritative outputs.
- `claim_modes`: strongest claim types the repo may publish.
- `sufficiency_types`: what its outputs are sufficient for.
- `trust_roots`: assumptions required for downstream reliance.
- `maturity`: current boundary hardening level.
- `next_step`: immediate work needed to advance maturity.

## Boundary classes

Initial classes:

- `standards`: normative schemas, templates, and doctrine.
- `estate_registry`: estate-wide catalog, topology, coverage, and transition reporting.
- `runtime_verifier`: Event-IR, proof artifacts, run bundles, checker contracts.
- `admissibility_policy`: policy gates for claim promotion and boundary crossings.
- `law_compiler`: ontology/schema-to-law compilation.
- `governance_evidence`: evidence packets, scoring, adjudication, and model/service governance.
- `evidentiary_retrieval`: search surfaces, source attribution, and evidence retrieval traces.
- `world_model_trace`: geospatial/world-model traces, provenance, and uncertainty.
- `agent_runtime`: agent execution boundary, sandboxing, lifecycle, and output attestation.
- `agent_identity_capability`: agent identity, capability manifests, and revocation.
- `boot_trust`: boot, TPM/PCR, release set, and rollback trust boundary.
- `local_state_integrity`: local-first sync, repair, replication, and provenance integrity.

## Crossing rule

A boundary crossing is admissible only when all of the following are true:

1. the producer declares the emitted artifact;
2. the consumer declares the required input;
3. the artifact has an allowed claim mode;
4. the artifact has the required sufficiency type;
5. evidence required by the producer and consumer is present;
6. Policy Fabric admits the transition;
7. Sociosphere records the crossing.

## Example

`SocioProphet/prophet-platform` may emit a `proof_artifact` for a KMS key usage claim. `SocioProphet/policy-fabric` may consume that artifact to decide whether a claim-mode promotion is admissible. `SocioProphet/sociosphere` records the resulting transition status in the Boundary Atlas.

If the proof artifact is `INCONCLUSIVE`, Policy Fabric blocks promotion and Sociosphere records the missing evidence family. If the artifact is `VIOLATION`, Policy Fabric blocks promotion and routes the counterexample. If the artifact is `PROVED` under approved assumptions, Policy Fabric may allow promotion to the matching evidence mode.

## Anti-patterns

- Treating a repo as authoritative because it contains related docs.
- Treating a README claim as fixture validation.
- Treating logs or dashboards as proof artifacts.
- Consuming an artifact without a declared upstream boundary.
- Emitting public claims without claim-mode labels.
- Treating semantic sufficiency as microstate sufficiency.

## v0.1 target

The first target is not full automation. It is explicitness:

- boundary catalog exists;
- evidence contracts exist;
- maturity gaps are visible;
- first downstream repos know what boundary files to add;
- claim promotion cannot be discussed without evidence mode vocabulary.
