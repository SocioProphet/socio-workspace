# EMVI Grammar and Token Ownership

Status: Draft v0.1

## Purpose

This document defines how shell input is parsed and, equally importantly, where
it is **not** parsed.

## Default interpretation

Search is the default interpretation for free text.

This avoids command overreach and protects phrases such as `open source licensing`
from being misparsed as a command when they are more naturally search.

## Command entry

Commands enter command mode in two ways:

1. Explicit command mode with a leading `>`
2. Implicit command mode only when a reserved verb is followed by strong command evidence

Examples:
- `>open current`
- `>capture selection into collection:research`
- `>query graph:commonsense "MATCH (...) RETURN ..."`

## Scope rule

In shell-owned states, leading slash tokens denote scope or filter.
Examples:
- `/files telemetry policy`
- `/browser current`
- `/graph commonsense deer corridor`

Slash is **not** a universal command prefix.

## Path rule

Absolute POSIX-style paths must not collide with scope syntax.
Absolute paths therefore require one of:
- `path:/etc/hosts`
- `file:///etc/hosts`
- quoted absolute path strings
- relative forms like `./`, `../`, `~/`

## Deictic references

The shell supports deictics such as:
- `current`
- `selection`
- `recent`
- `here`

These are resolved late against the active Context and focus owner.

## Typed selectors

Typed selectors reduce ambiguity and make lowering explicit.
Examples:
- `collection:research`
- `snapshot:current`
- `graph:commonsense`
- `service:policy`
- `host:laptop`

## Ownership boundary

Grammar only runs in grammar-owning states.
It must not parse or steal meaning from:
- editor insert mode
- browser text input
- terminal pass-through
- password/sensitive input
- accessibility-owned input

## Token precedence

1. local completion surface ownership
2. explicit command prefix (`>`)
3. local pass-through ownership
4. shell scope tokens (`/scope`)
5. implicit-command reserved verb with strong evidence
6. free-text search fallback

## Normalization rules

The parser should normalize equivalent intent forms where safe.
Examples:
- `find telemetry policy` -> search intent
- `/files telemetry policy` -> scoped search intent
- `>capture current into collection:research` -> explicit ActionSpec candidate

## Required parse result

A parse must produce either:
- SearchSpec
- ActionSpec candidate
- ParseError with explicit reason

## Invariants

1. Free text remains search by default.
2. Slash is scope/filter in shell-owned states, not global command syntax.
3. Grammar must defer to local input ownership in pass-through states.
4. Parse ambiguity should surface clearly instead of being silently guessed.
