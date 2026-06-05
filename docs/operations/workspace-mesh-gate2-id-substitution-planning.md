# Workspace Mesh Gate 2 — ID Substitution Planning

Status: `planning_only`
Mesh state: `prepared-but-not-deployed`
Gate 1 disposition: `reviewed_no_promotion`
Gate 2 disposition: `not_started`

## Purpose

Gate 2 will eventually review how placeholder IDs should be replaced in local operator configuration. This document is a planning scaffold only. It does not contain real IDs and does not begin substitution.

## Inputs under future review

The future review surface is limited to these placeholder fields:

| Placeholder | Meaning | Future review owner |
|---|---|---|
| `TODO_GOOGLE_SHEET_ID` | Prototype ledger Sheet identifier | Workspace operator |
| `TODO_APPS_SCRIPT_PROJECT_ID` | Apps Script project identifier | Workspace operator |
| `TODO_SP_CLOUD_VENDOR_STRATEGY_CALENDAR_ID` | Cloud Vendor Strategy calendar identifier | Workspace operator |
| `TODO_SP_LAUNCH_COUNCIL_CALENDAR_ID` | Launch Council calendar identifier | Workspace operator |

## Planning requirements

Before Gate 2 can start, a separate dated Gate 2 record must define:

- the source of each proposed ID,
- who verified that source,
- where the ID will be written locally,
- how the ID will be checked before use,
- how dry-run posture remains enabled,
- how a rollback to placeholders will be performed,
- and how logs will prove that no execution occurred during review.

## Required preconditions

Gate 2 planning can proceed only after:

- Gate 0 local topology proof exists,
- Gate 1 generated-artifact review proof exists,
- Gate 1 is recorded as reviewed with no promotion,
- default mesh plan safety still passes,
- generated artifact inspection still passes from `source=plan_json`,
- and the mesh still reports `prepared-but-not-deployed`.

## Planned review steps

1. Enumerate the four placeholder fields.
2. Confirm each placeholder still appears in `default-plan.json`.
3. Create a local-only candidate mapping file outside version control.
4. Review the candidate mapping without writing it into the repository.
5. Confirm no execution command is run as part of the review.
6. Record either `gate_2_not_started` or `gate_2_ready_for_review` in a dated record.

## Non-goals

This planning scaffold does not:

- provide real IDs,
- write IDs into versioned files,
- create or modify Workspace assets,
- run Apps Script,
- create scheduled jobs,
- or promote the mesh beyond planning.

## Next permissible action

The next permissible action is a Gate 2 planning validator that checks this scaffold and confirms all ID values remain placeholders.
