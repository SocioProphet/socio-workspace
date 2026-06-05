# Workspace Mesh Release Readiness Checklist

Status: prepared-but-not-deployed
Date: 2026-06-05
Topology repo: `SocioProphet/sociosphere`
Implementation repo: `SocioProphet/prophet-platform-fabric-mlops-ts-suite`

## Purpose

This checklist prevents the Google Workspace Operations Mesh from drifting from prepared infrastructure into live deployment without explicit review.

The current approved state is:

```text
prepared-but-not-deployed
```

## Gate 0 — Local topology proof

Required before any promotion:

- [x] `sociosphere` has a `GNUmakefile` proxy surface.
- [x] `workspace-mesh-proxy-validate` passes.
- [x] `terraform-workspace-mesh-plan-safe` delegates to the fabric repo.
- [x] Default mesh plan is local-file-only.
- [x] Default mesh plan has exactly four actionable local-file resources.

Evidence:

```text
PASS: Sociosphere Workspace mesh proxy is valid
targets=14
PASS: Workspace mesh default plan is local-file-only
actionable_changes=4
```

## Gate 1 — Generated artifact review

Required before any ID substitution:

- [ ] Review `config.generated.json`.
- [ ] Review `clasp.generated.json`.
- [ ] Review `mesh-summary.generated.json`.
- [ ] Review `operator-next-steps.md`.
- [ ] Confirm generated files contain no secrets.
- [ ] Confirm generated files remain ignored unless explicitly promoted.

## Gate 2 — ID substitution review

Required before dry-run Apps Script execution:

- [ ] Replace `TODO_GOOGLE_SHEET_ID`.
- [ ] Replace `TODO_APPS_SCRIPT_PROJECT_ID`.
- [ ] Replace `TODO_SP_CLOUD_VENDOR_STRATEGY_CALENDAR_ID`.
- [ ] Replace `TODO_SP_LAUNCH_COUNCIL_CALENDAR_ID`.
- [ ] Confirm `dryRun` remains `true`.
- [ ] Confirm no Workspace group creation is enabled.
- [ ] Confirm no Google project service enablement is enabled unless separately approved.

## Gate 3 — Apps Script dry-run rehearsal

Required before controlled test write:

- [ ] Apps Script files pushed or copied intentionally.
- [ ] `setupOperationsLedger('<spreadsheet-id>')` succeeds.
- [ ] `seedWorkspaceRows('<spreadsheet-id>')` succeeds.
- [ ] `seedDashboardRows('<spreadsheet-id>')` succeeds.
- [ ] `runMetadataParserFixtureTest()` passes.
- [ ] `runMetadataParserNegativeTest()` passes.
- [ ] `syncCalendarEventsToMeetings(config)` runs with `dryRun: true`.
- [ ] `Automations` records dry-run outcome.
- [ ] `Meetings` is not mutated during dry run.

## Gate 4 — Controlled test write

Required before scheduled triggers:

- [ ] Create one test event on the prototype calendar.
- [ ] Include valid `socioprophet:` metadata.
- [ ] Set `dryRun: false` only for the controlled test.
- [ ] Confirm exactly one `Meetings` row is created.
- [ ] Modify the same event and rerun sync.
- [ ] Confirm the same row is updated rather than duplicated.
- [ ] Return config to `dryRun: true` after test unless explicitly approved otherwise.

## Gate 5 — Scheduled trigger approval

Required before recurring automation:

- [ ] Gate 0 through Gate 4 evidence is attached.
- [ ] Failure/quarantine behavior has been observed.
- [ ] Recovery path has been rehearsed.
- [ ] Trigger cadence is approved.
- [ ] Trigger owner is assigned.
- [ ] Trigger disable procedure is documented.

## Gate 6 — Native SocioProphet migration review

Required before treating Workspace behavior as a native platform contract:

- [ ] Calendar metadata stable for two review cycles.
- [ ] Meeting rows stable for two review cycles.
- [ ] Dashboard panels regenerate from ledger data.
- [ ] Automation run rows capture success, failure, and quarantine cases.
- [ ] Role/group mapping has durable identifiers.
- [ ] Native object targets are explicit.

## Explicit non-authorization

This checklist does not authorize:

- `tofu apply` against live Google resources,
- Google Workspace group creation,
- Google Calendar creation,
- Google Sheet creation by IaC,
- Apps Script scheduled triggers,
- Looker Studio dashboard creation,
- production data processing,
- or native SocioProphet migration.

Each requires its own promotion record.
