# Issue 451 manifest reconciliation notes

Source issue: #451

Status: evidence note only. This file does not change `manifest/workspace.toml`.

## Scope

This note covers the high-risk reconciliation entries from `reports/workspace-manifest-reconciliation.disposition-v0.json`:

- `tritfabric`
- `tritrpc`
- `knowledge-graph`
- `hdt_app`
- `human_digital_twin`

## Manifest evidence

### hdt_app

Manifest entry:

- name: `hdt_app`
- role: `component`
- local path: `components/hdt_app`
- url: `https://github.com/SocioProphet/hdt_app`
- ref: `main`

Lookup outcome:

- `repository_404`

Proposed disposition:

- Do not remove automatically.
- Review as possible stale alias for `human_digital_twin`, retired app surface, uncreated repo, or private-beyond-connector repo.

### human_digital_twin

Manifest entry:

- name: `human_digital_twin`
- role: `component`
- local path: `components/human_digital_twin`
- url: `https://github.com/SocioProphet/human-digital-twin`
- ref: `main`

Lookup outcome:

- resolves to `a3a192cd0120d6004f57bc6f546af26abbd8fa81`

Proposed disposition:

- Retain as canonical HDT repo unless a better canonical repo is identified.
- If `hdt_app` is confirmed stale, remove or redirect it in a separate manifest PR.

### tritfabric

Manifest entry:

- name: `tritfabric`
- role: `component`
- local path: `components/tritfabric`
- url: `https://github.com/SocioProphet/tritfabric`
- ref: `main`
- rev: `3644b4a4b32fec209c2a57843ce9db2f1273bbec`

Lookup outcome:

- current `main` resolves to `9be4c3c74a8416d8c225124c0144647fa1b8b5e5`
- declared pin differs from current `main`

Proposed disposition:

- Preserve pin until an explicit pin-bump review approves a target revision.
- Do not silently move this dependency to current `main`.

### tritrpc

Manifest entry:

- name: `tritrpc`
- role: `protocol`
- local path: `third_party/tritrpc`
- url: `https://github.com/SocioProphet/TriTRPC`
- ref: `main`
- rev: `efc114b0132b61472d3abb29007441597bca0cfc`

Lookup outcome:

- current `main` resolves to `2caf46cae246d2ba432d580559f10f4da4cfc50c`
- declared pin differs from current `main`

Proposed disposition:

- Preserve pin until an explicit pin-bump review approves a target revision.
- Treat TriTRPC as protocol infrastructure; require stronger review than ordinary component pins.

### knowledge-graph

Disposition report state:

- lookup status: `ref_missing_or_no_main`

Proposed disposition:

- Verify repository default branch or intended canonical repo before editing the manifest.
- If the repo is valid but does not use `main`, update the manifest to the verified default branch in a separate PR.
- If the repo has been superseded, replace it only with a validated target repository and ref.

## Required next action before manifest mutation

Each scoped entry needs one final disposition:

- retain
- repin
- rename
- archive
- remove
- mark private/planned

No deletion, rename, or pin bump should be made from this note alone.
