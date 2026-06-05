# Gate 1 — Generated Artifact Review Template

Status: template-only
Current mesh state: `prepared-but-not-deployed`
Gate: `gate-1-generated-artifact-review`

## Purpose

Gate 1 reviews local generated artifacts produced by the default Workspace mesh plan before any ID substitution, Apps Script execution, or live Workspace action.

This template does not authorize deployment. It exists to make generated artifact review repeatable, auditable, and separate from later gates.

## Prerequisites

- [ ] Gate 0 local topology proof is complete.
- [ ] `make workspace-mesh-topology-validate` passes.
- [ ] `make terraform-workspace-mesh-plan-safe` passes.
- [ ] Default plan remains local-file-only.
- [ ] Generated artifacts are present under the fabric repo generated directory.

## Generated artifacts under review

Expected generated directory:

```text
~/dev/prophet-platform-fabric-mlops-ts-suite/infra/google-workspace-ops-mesh/generated/google-workspace-ops-mesh/
```

Expected artifacts:

```text
config.generated.json
clasp.generated.json
mesh-summary.generated.json
operator-next-steps.md
```

## Artifact 1 — config.generated.json

Review checklist:

- [ ] `spreadsheetId` is still `TODO_GOOGLE_SHEET_ID`, unless Gate 2 has explicitly started.
- [ ] `dryRun` is `true`.
- [ ] `syncWindowDaysBack` is reasonable for rehearsal.
- [ ] `syncWindowDaysForward` is reasonable for rehearsal.
- [ ] `calendars` contains only prototype calendar placeholders or approved prototype calendar IDs.
- [ ] `requiredMetadataFields` includes `workstream`, `meeting_type`, `canonical_issue`, `dashboard_key`, and `expected_outputs`.
- [ ] `tabs` maps only expected ledger tabs.
- [ ] No secrets, tokens, credentials, or private production identifiers are present.

Reviewer notes:

```text
TODO
```

## Artifact 2 — clasp.generated.json

Review checklist:

- [ ] `scriptId` is still `TODO_APPS_SCRIPT_PROJECT_ID`, unless Gate 2 has explicitly started.
- [ ] `rootDir` points to `apps-script/google-workspace-ops-prototype`.
- [ ] `filePushOrder` contains only expected prototype Apps Script files.
- [ ] No secrets, tokens, credentials, or private production identifiers are present.
- [ ] Review confirms this artifact is not equivalent to running `clasp push`.

Reviewer notes:

```text
TODO
```

## Artifact 3 — mesh-summary.generated.json

Review checklist:

- [ ] `dry_run` is `true`.
- [ ] `project_services_enabled` is `false`.
- [ ] `workspace_groups_enabled` is `false`.
- [ ] IDs are still placeholders unless Gate 2 has explicitly started.
- [ ] No live resource creation is implied by the summary.
- [ ] No secrets, tokens, credentials, or private production identifiers are present.

Reviewer notes:

```text
TODO
```

## Artifact 4 — operator-next-steps.md

Review checklist:

- [ ] It tells operators to validate repository scaffold.
- [ ] It lists generated files to review.
- [ ] It says generated clasp config must be reviewed before copying to `.clasp.json`.
- [ ] It keeps `dryRun` enabled.
- [ ] It states unsupported-by-default surfaces, including calendars, Sheets, Apps Script projects, dashboard objects, Workspace groups, and scheduled triggers.
- [ ] It does not instruct operators to apply, deploy, push, or enable triggers.

Reviewer notes:

```text
TODO
```

## Gate 1 disposition

Choose one when a real review is performed:

```text
not_started | needs_changes | reviewed_no_promotion | reviewed_ready_for_gate_2
```

Current template disposition:

```text
not_started
```

## Explicit non-authorization

Gate 1 review does not authorize:

- ID substitution,
- `tofu apply`,
- `clasp push`,
- Apps Script execution,
- scheduled triggers,
- live calendar access,
- Workspace group creation,
- dashboard creation,
- production data processing,
- or native SocioProphet migration.
