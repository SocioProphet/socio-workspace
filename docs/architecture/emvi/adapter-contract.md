# EMVI Adapter Contract

Status: Draft v0.1

## Purpose

Adapters expose implementation surfaces to the EMVI shell without leaking raw
implementation detail into the shell grammar.

## Minimum adapter capabilities

Each adapter must declare which of these it supports:
- `search`
- `list`
- `open`
- `preview`
- `capture`
- `inspect`
- `act`
- `cancel`
- `replay`

## Required adapter metadata

Each adapter must disclose:
- supported object kinds
- supported trust classes
- auth/session requirements
- degraded-mode behavior
- placement expectations
- anchor strategy or locator stability
- capability limits

## Service-family affinity

Every adapter should map cleanly to one or more service families.
Examples:
- browser-facing runtime -> `ui_runtime`, `network`, `policy`
- shell execution -> `shell`, `policy`, `ledger`
- graph query -> `graph`, `ledger`
- collection export -> `collection`, `ledger`

## Contract shape

An adapter-facing request should carry at least:
- normalized intent
- target object(s)
- context/deictic resolution
- trust class
- requested placement
- provenance correlation id

The adapter response should carry at least:
- result objects or status
- preview material when applicable
- provenance append or reference
- errors as typed failure states, not only raw strings

## Error contract

Adapters should distinguish:
- unsupported capability
- denied by policy
- missing auth/session
- missing anchor re-resolution
- unavailable placement
- transient transport/runtime failure
- invalid target object

## Invariants

1. Adapters expose capabilities; the shell does not guess them.
2. Adapters do not bypass policy for gated actions.
3. Adapters should be replay/provenance aware from day one.
4. Degraded mode must be explicit, not silent.
