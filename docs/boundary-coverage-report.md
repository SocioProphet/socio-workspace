# Boundary Coverage Report v0.1

Status: bootstrap report.  
Owner: `SocioProphet/sociosphere`.

## Summary

The Boundary Atlas v0.1 makes repo boundary maturity visible across the initial estate spine.

Current high-level status:

| Maturity | Count | Meaning |
| --- | ---: | --- |
| L2 | 2 | Machine-readable example or catalog record exists |
| L1 | 3 | Implementation issue or human boundary path exists |
| L0 | 7 | Boundary still informal / native file missing |

Total initial entries: 12.

## Coverage by repo

| Repo | Boundary class | Maturity | Immediate gap |
| --- | --- | --- | --- |
| `SocioProphet/prophet-platform-standards` | standards | L2 | Merge typed-boundary standard and publish schemas |
| `SocioProphet/sociosphere` | estate_registry | L2 | Add validator / ingestion tool |
| `SocioProphet/prophet-platform` | runtime_verifier | L1 | Add native proof-artifact and Event-IR schemas |
| `SocioProphet/policy-fabric` | admissibility_policy | L1 | Add claim-mode and proof-verdict gates |
| `SocioProphet/model-governance-ledger` | governance_evidence | L1 | Add evidence-packet schema and scorer |
| `SocioProphet/ontogenesis` | law_compiler | L0 | Add boundary declaration for schema-to-law compiler role |
| `SocioProphet/sherlock-search` | evidentiary_retrieval | L0 | Add evidence retrieval/source trace boundary |
| `SocioProphet/gaia-world-model` | world_model_trace | L0 | Add world-model provenance/trace boundary |
| `SocioProphet/agentplane` | agent_runtime | L0 | Add runtime sandbox/output-attestation boundary |
| `SocioProphet/agent-registry` | agent_identity_capability | L0 | Add identity/capability/revocation boundary |
| `SourceOS-Linux/sourceos-boot` | boot_trust | L0 | Add BootReleaseSet/TPM/PCR trust boundary |
| `SourceOS-Linux/sourceos-syncd` | local_state_integrity | L0 | Add local-first state integrity boundary |

## First hardening queue

1. Merge `prophet-platform-standards` typed-boundary standard.
2. Add native boundary files to `prophet-platform`, `policy-fabric`, and `model-governance-ledger`.
3. Add Sociosphere validator for `catalog/boundaries.yaml` and repo-local `.socioprophet/boundary.yaml` files.
4. Add Policy Fabric admissibility gates for claim-mode promotion.
5. Add Prophet Platform proof-artifact schema and KMS fixtures.

## Risk notes

- Current catalog entries are bootstrap declarations, not proof of implementation.
- L0 repos should not be presented as boundary-governed until native declarations land.
- `PROVED`, `VIOLATION`, and `INCONCLUSIVE` semantics require downstream checker and policy integration before they can govern releases.
- The atlas records evidence contracts; it does not replace the evidence itself.

## v0.2 target

Boundary Atlas v0.2 should add:

- schema validation command;
- generated coverage report from catalog files;
- PR check for missing/invalid boundary metadata;
- links to native repo `BOUNDARY.md` files;
- transition status imported from Policy Fabric once available.
