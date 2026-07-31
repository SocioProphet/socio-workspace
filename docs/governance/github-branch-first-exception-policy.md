# GitHub branch-first exception policy

Status: operational policy. This document governs exceptions to branch-first GitOps for Sociosphere repository work. It does not authorize destructive mutation, issue closure, PR merge, branch deletion, production execution, or credential expansion.

## Rule

Branch-first GitOps is the default. Direct-to-main writes are exceptions and must be rare, low-risk, receipt-verified, and ledgered when caused by tool or connector limitations.

## Normal path

For normal repository work:

1. rehydrate durable state;
2. identify latest intended base;
3. create a branch from the current base SHA;
4. create or update files on that branch;
5. open a PR with explicit scope and non-goals;
6. inspect changed files and checks;
7. merge only after preflight authority is established;
8. verify post-merge receipts.

## Direct-to-main exception conditions

A direct-to-main write is allowed only when all conditions are true:

1. the change is documentation, registry seed data, or non-executing governance metadata;
2. the change is non-destructive;
3. the change does not alter runtime, production, deployment, credentials, or user-facing behavior;
4. no branch/PR path is available in the current tool surface or the user explicitly authorizes the exception;
5. the operator records the rationale;
6. the operator performs an immediate post-write read receipt;
7. the exception is recorded in `registry/github-tool-impedance-ledger.yaml` when caused by tool, connector, branch, or workflow impedance.

## Direct-to-main prohibition

Direct-to-main writes are prohibited for:

- runtime code;
- production configuration;
- secrets, credentials, or auth changes;
- destructive changes;
- branch deletion;
- issue or PR closure;
- merge operations;
- generated lockfile replacement;
- resolved-lock regeneration;
- workflow changes with production authority;
- any change whose risk cannot be classified before writing.

## Required exception record

The ledger event must include:

- operation intended;
- why branch-first was bypassed;
- tool/connector surface observed;
- mutation commit SHA;
- post-write fetch receipt;
- attribution split between connector, GitHub-native behavior, assistant/operator behavior, permission boundary, and real repo defect;
- remediation or controller requirement.

## Symbols

Direct-to-main exceptions typically involve:

- `delta_r`: durable-state rehydration boundary;
- `epsilon_r`: evidence receipt requirement;
- `A_i`: assistant-induced impedance when procedure is bypassed;
- `C_m`: connector capability matrix gap;
- `W_to_K`: workaround-to-controller law.

## Controller requirement

A future GitHub Controller must make direct-to-main writes structurally harder than branch-first changes. The controller should require explicit exception classification and should automatically create a ledger event when direct-to-main is used.
