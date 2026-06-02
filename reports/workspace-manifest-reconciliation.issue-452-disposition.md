# Issue 452 connector and service disposition report

Source issue: #452

Status: evidence and disposition proposal only. This file does not change `manifest/workspace.toml`.

## Scope

- `connector-github`
- `connector-gitlab`
- `connector-jira`
- `connector-kafka`
- `connector-slack`
- `configs`
- `dev_api`
- `asr-service`
- `embeddings-service`
- `event-bus`
- `data-pipeline`

## Current lookup state

All scoped manifest entries returned `repository_404` through the connector lookup path in `reports/workspace-resolved-lock-standard-main-live-outcomes.batch-005.json`, except `event-bus` and `data-pipeline`, which were captured in batch 006 and also did not resolve as declared.

## Repository search evidence

Exact or near-exact searches did not identify active SocioProphet repositories for:

- `connector-github`
- `connector-gitlab`
- `connector-jira`
- `connector-kafka`
- `connector-slack`
- `dev-api`
- `asr-service`
- `embeddings-service`
- `event-bus`

Broad connector search returned unrelated or generic connector/vendor/MCP repositories and did not establish a one-to-one replacement for the declared connector entries.

Broad `data pipeline` search returned possible adjacent candidates:

- `SocioProphet/datakit`, default branch `master`
- `SocioProphet/argo-dataflow`, default branch `main`

These are not confirmed replacements for `data-pipeline`.

Broad `configs` search did not return an exact `configs` repository; visible results were not direct replacements.

## Proposed dispositions

### Connector stubs

Entries:

- `connector-github`
- `connector-gitlab`
- `connector-jira`
- `connector-kafka`
- `connector-slack`

Proposed disposition:

- classify as `planned_or_stale_connector_stub_pending_confirmation`.
- do not replace with unrelated generic connector repositories.
- decide whether these should remain as future logical components or be removed from the workspace manifest until created.

### Service stubs

Entries:

- `dev_api`
- `asr-service`
- `embeddings-service`
- `event-bus`

Proposed disposition:

- classify as `planned_or_stale_service_stub_pending_confirmation`.
- verify whether these services exist under different canonical platform repositories before removing.

### configs

Entry:

- `configs`

Proposed disposition:

- classify as `planned_or_stale_adapter_pending_confirmation`.
- verify whether configuration now lives inside `sociosphere`, `prophet-platform`, or another canonical config/policy repo.

### data-pipeline

Entry:

- `data-pipeline`

Candidate adjacent repositories:

- `SocioProphet/datakit`
- `SocioProphet/argo-dataflow`

Proposed disposition:

- classify as `candidate_successor_pending_confirmation`.
- do not rewrite to either candidate until ownership and semantic equivalence are confirmed.

## Required next checks before manifest mutation

Before any cleanup PR:

1. Search inbound references in Sociosphere for every scoped entry.
2. Check whether each name is intended as a future logical repo even if not created.
3. Confirm whether any candidate successor has equivalent role, local path expectations, and required capabilities.
4. Remove, replace, or retain entries only through a manifest PR with explicit rationale.
5. Regenerate coverage and resolved-lock reports after approved changes.

## Default decision

No automatic removal.

The safest current classification is planned/stale pending confirmation for every entry except `data-pipeline`, which has possible but unconfirmed adjacent successors.
