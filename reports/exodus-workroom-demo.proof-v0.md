# Exodus Migration Workroom demo proof package v0

Related issue: #478

Status: report-only proof artifact.

This report records what the synthetic Exodus Migration Workroom demo currently proves, what it explicitly does not prove, and what remains for the next sprint. It does not change workspace manifest membership, pins, refs, resolved-lock state, provider credentials, runtime behavior, or production claims.

## Proof matrix

| Proof area | Artifact | Repository | Current state | Claim supported |
|---|---|---|---|---|
| Exodus domain run | `examples/synthetic-tenant-a/exodus-run.json` | `SocioProphet/exodus` | merged | A deterministic synthetic Apple/Google/Microsoft exit-readiness run exists. |
| Exodus domain schema | `schemas/exodus-run.v0.schema.json` | `SocioProphet/exodus` | merged | The synthetic run has a persisted schema boundary. |
| Exodus domain validation | `scripts/validate_exodus_demo.py` | `SocioProphet/exodus` | merged | The synthetic fixture can be checked offline without provider credentials. |
| Workspace containment | `contracts/workspace/exodus-migration-workroom.v0.1.example.json` | `SocioProphet/prophet-workspace` | merged | A Professional Workroom can carry the Exodus run. |
| Workspace bridge | `contracts/workspace/exodus-workroom-bridge.schema.json` and example | `SocioProphet/prophet-workspace` | merged | Exodus refs are made explicit without forking the Professional Workroom model. |
| Workspace validation | `tools/validate_professional_workrooms.py` | `SocioProphet/prophet-workspace` | merged | The workroom and bridge examples validate under workspace contracts. |
| Sociosphere integration | `reports/exodus-workroom-demo.integration-v0.md` and `.json` | `SocioProphet/sociosphere` | merged | The three-repo chain is recorded as durable control-plane state. |
| Cross-repo readiness | `tools/check_exodus_workroom_demo.py` | `SocioProphet/sociosphere` | merged | Local check can verify expected artifacts across the three repos. |
| Demo runbook | `docs/exodus-workroom-demo-runbook.md` | `SocioProphet/sociosphere` | merged | A reviewer has a durable restartable validation path. |

## Supported claim matrix

The demo currently supports the following internal synthetic claims:

1. Exodus can represent a synthetic migration/evidence/scoring run for Apple, Google, and Microsoft.
2. The synthetic run can include provider topology, account/root inventory, asset census, export ledger, ERI/PCS scores, blockers, recommendations, and a Phase 2 budget proposal.
3. Prophet Workspace can represent that Exodus run as a Professional Workroom without creating a special-purpose alternate workroom surface.
4. The Workspace bridge can bind the Exodus run, provider topology, asset census, export ledger, scores, blockers, recommendations, budget proposal, office artifacts, evidence, policies, and Sociosphere control-plane refs.
5. Sociosphere can record the Exodus + Workspace chain as durable control-plane state with explicit declared, observed, disposition, summary, integration, and validation boundaries.
6. The demo can be restarted from Git artifacts and issue/PR state rather than conversation memory.

## Non-claim matrix

The demo does not currently prove:

1. Real Apple, Google, or Microsoft credential ingestion.
2. Live provider API operation.
3. Provider-side writes.
4. Destructive migration actions.
5. Real export automation.
6. Chain-of-custody sealing for real evidence.
7. Production migration readiness.
8. Polished Exodus Dashboard UI readiness.
9. Full 95-repo Sociosphere workspace estate resolution.
10. Security hardening for private-team or production execution.

## Current readiness assessment

The internal synthetic demo is now structurally ready if the local cross-repo readiness checker returns `ready` in the expected checkout layout or with path overrides.

Estimated readiness after validator pass:

- Architecture proof: high.
- Contract proof: high.
- Synthetic fixture proof: high.
- Cross-repo restartability: medium-high.
- Real-provider readiness: low.
- UI demo readiness: low-medium.

## Next sprint backlog

1. Run and capture local readiness output from `python3 tools/check_exodus_workroom_demo.py --run-validators --json`.
2. Add a committed readiness output fixture if the local check is clean.
3. Add a lightweight static dashboard fixture in Exodus or Workspace showing the run summary, ERI/PCS, blockers, recommendations, and budget proposal.
4. Add Sociosphere demo-state manifest profile that names the three repos and expected artifact paths.
5. Add first real-provider adapter readiness plan for Apple, Google, and Microsoft without credential collection.
6. Add security and privacy threat model for moving from synthetic demo to private-team demo.
7. Add UI follow-up issue for a browser-visible Exodus Migration Workroom surface.

## Stop conditions

Stop and review before any change that would:

- collect credentials;
- call provider APIs;
- write to provider accounts;
- perform destructive actions;
- edit workspace manifest membership;
- move pins or refs;
- regenerate full workspace resolved lock;
- claim production migration readiness.

## Bottom line

The synthetic demo chain is materially established. The remaining proof step is to run and capture the cross-repo readiness checker output. After that, the work should move from contract proof to user-visible demo surface and real-provider readiness planning.
