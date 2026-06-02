# Issue 453 documentation and support disposition report

Source issue: #453

Status: evidence and disposition proposal only. This file does not change `manifest/workspace.toml`.

## Scope

- `socioprophet_integration`
- `runbooks`
- `onboarding-docs`
- `architecture-docs`
- `api-specs`

## Current lookup state

All five scoped manifest entries returned `repository_404` through the connector lookup path in `reports/workspace-resolved-lock-standard-main-live-outcomes.batch-004.json`.

Searches across the SocioProphet GitHub estate did not find exact active repositories for:

- `runbooks`
- `onboarding-docs`
- `api-specs`

Search for `socioprophet integration` did not return an exact replacement; the nearest relevant result was `socioprophet-standards-knowledge`, which is not a direct replacement.

Search for `architecture docs` did not return an exact replacement; the visible result was not a SocioProphet architecture documentation successor.

## Adjacent canonical evidence

The retired `socioprophet-docs` repository explicitly says it is not the current canonical documentation home and points active documentation to `SocioProphet/socioprophet`, with docs source under `docs/.vitepress/` and public docs mounted at `/documentation/`.

That means the likely documentation consolidation target is the active `socioprophet` documentation surface, not the stale standalone docs/support repositories.

## Proposed dispositions

### socioprophet_integration

Current manifest state:

- role: docs
- local path: `components/socioprophet_integration`
- URL: `https://github.com/SocioProphet/socioprophet_integration`
- ref: `main`

Proposed disposition:

- classify as `stale_or_merged_pending_confirmation`.
- candidate successor surface: `SocioProphet/socioprophet` documentation and integration docs, if confirmed.
- do not remove until inbound references are checked.

### runbooks

Current lookup state:

- repository_404
- no exact installed-repository search result found.

Proposed disposition:

- classify as `stale_or_uncreated_pending_confirmation`.
- if runbooks are now embedded in active docs, replace the manifest entry with the canonical docs surface only after confirmation.

### onboarding-docs

Current lookup state:

- repository_404
- no exact installed-repository search result found.

Proposed disposition:

- classify as `stale_or_uncreated_pending_confirmation`.
- likely merged into active documentation or not yet created.

### architecture-docs

Current lookup state:

- repository_404
- no exact installed-repository search result found.

Proposed disposition:

- classify as `stale_or_uncreated_pending_confirmation`.
- check whether architecture material lives under `SocioProphet/socioprophet`, `socioprophet-standards-knowledge`, or Sociosphere docs before removal.

### api-specs

Current lookup state:

- repository_404
- no exact installed-repository search result found.

Proposed disposition:

- classify as `stale_or_uncreated_pending_confirmation`.
- check whether API specs now live in service repositories or platform standards before removal.

## Required next checks before manifest mutation

Before any manifest cleanup PR:

1. Search inbound references for each scoped name in Sociosphere.
2. Search active documentation surfaces for equivalent content.
3. Decide whether the stale entries should be removed, replaced, or retained as planned/private repos.
4. Regenerate coverage and resolved-lock reports after approved manifest changes.

## Default decision

No automatic removal.

The currently safest state is to mark all five as stale or uncreated pending confirmation, then perform a dedicated inbound-reference scan before changing `manifest/workspace.toml`.
