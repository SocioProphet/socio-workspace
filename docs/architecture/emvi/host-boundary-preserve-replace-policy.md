# EMVI Host-Boundary Preserve/Replace Policy

Status: Draft v0.1

## Purpose

The shell must coexist with the host OS, terminal stack, browser chrome, editors,
and accessibility tooling. This document defines which boundaries are preserved,
which may be mirrored, and which may be replaced only with explicit opt-in.

## Default policy

### Preserve by default
- OS launcher and app switching
- native window cycling and workspace controls
- accessibility and assistive controls
- terminal emulator management shortcuts
- tmux prefix and copy-mode ownership
- browser chrome shortcuts
- editor/composer insert-mode text input and formatting shortcuts
- sensitive text-entry surfaces

### Mirror allowed
EMVI may expose searchable or previewable equivalents of preserved actions,
but must not silently take ownership from their native surface.

### Opt-in replacement only
Launcher-like entry points may be replaced only when the user explicitly opts in
and the system provides rollback.

## Local ownership rule

If a surface is in a pass-through state, printable input belongs to that local surface.
Examples:
- terminal pass-through
- remote shell pass-through
- editor insert mode
- browser text fields
- composer/chat inputs

## Completion precedence

When a local completion surface is open, that completion surface owns Tab and
completion navigation first.

## Invariants

1. EMVI never silently takes raw text input from pass-through surfaces.
2. EMVI must remain compatible with accessibility ownership.
3. Host-native conventions win unless replacement is explicit and reversible.
4. Browser and terminal local key worlds remain first-class.
