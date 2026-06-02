# Issue 451 reconciliation decision checklist

Source issue: #451

This checklist controls when high-risk workspace manifest reconciliation entries may move from evidence gathering to manifest mutation.

## Decision rules

### Pins

Pinned entries are not ordinary branch-tracking dependencies.

A pin may only move when all of the following are true:

- the current pin is confirmed obsolete or insufficient;
- the target revision is selected explicitly;
- the target revision has been reviewed for compatibility;
- the issue or PR explains why the pin moves;
- coverage and resolved-lock reports are regenerated after the pin movement.

### Aliases and duplicate surfaces

Alias-like entries may only be removed or renamed when all of the following are true:

- the canonical replacement repository is identified;
- local path effects are understood;
- downstream consumers are checked;
- the manifest PR records the reason for removal or rename;
- coverage and resolved-lock reports are regenerated after the change.

### Missing refs

A missing ref may only be changed when all of the following are true:

- the repository exists;
- the intended branch, tag, or pin is verified;
- the manifest PR records the branch/ref correction;
- coverage and resolved-lock reports are regenerated after the change.

## Entry decisions

### tritfabric

Current state:

- manifest pins `rev = 3644b4a4b32fec209c2a57843ce9db2f1273bbec`
- current `main` resolves to `9be4c3c74a8416d8c225124c0144647fa1b8b5e5`

Decision needed:

- preserve current pin;
- bump to current main;
- bump to another reviewed revision;
- mark as intentionally frozen.

Default until decided: preserve current pin.

### tritrpc

Current state:

- manifest pins `rev = efc114b0132b61472d3abb29007441597bca0cfc`
- current `main` resolves to `2caf46cae246d2ba432d580559f10f4da4cfc50c`

Decision needed:

- preserve current pin;
- bump to current main;
- bump to another reviewed revision;
- mark as intentionally frozen.

Default until decided: preserve current pin.

### knowledge-graph

Current state:

- manifest declares `ref = main`
- live lookup returned `ref_missing_or_no_main`

Decision needed:

- identify correct default branch;
- pin to a known commit;
- replace with canonical successor repo;
- mark as private/planned/stale.

Default until decided: no manifest mutation.

### hdt_app

Current state:

- manifest points to `https://github.com/SocioProphet/hdt_app`
- live lookup returned `repository_404`
- `human_digital_twin` resolves successfully and may be canonical.

Decision needed:

- confirm `hdt_app` is an alias of `human_digital_twin`;
- confirm `hdt_app` is a planned/private repo;
- confirm `hdt_app` is stale and can be removed;
- replace with a validated canonical repo if different.

Default until decided: no manifest mutation.

### human_digital_twin

Current state:

- manifest points to `https://github.com/SocioProphet/human-digital-twin`
- live lookup resolves successfully.

Decision needed:

- retain as canonical HDT repo;
- only change if another canonical HDT repo is explicitly selected.

Default until decided: retain.

## Exit criteria for #451

Issue #451 can close only when:

- every scoped entry has one recorded disposition;
- any approved manifest changes are merged;
- generated reports are refreshed after those changes;
- #439 is updated with the final #451 disposition summary.
