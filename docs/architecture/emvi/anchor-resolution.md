# EMVI Anchor Resolution

Status: Draft v0.1

## Purpose

Anchors are what make captured knowledge durable.
A locator reopens the object; an anchor resolves the relevant portion inside it.

## Multi-anchor principle

Whenever possible, captured items should retain multiple anchors so drift in one
resolution path does not destroy the captured reference.

## Common anchor patterns

### Page / browser content
- URL / final URL
- heading path
- quote selector
- DOM locator if available
- content-hash neighborhood

### File / snippet
- file path
- symbol path
- line range
- content hash of selected span
- nearby structural context

### Terminal output
- command id / execution correlation id
- output span
- command hash
- timestamp and execution context

### Graph row
- row id if present
- query hash
- selected field set
- result position if stable enough

## Resolution order

Suggested strategy:
1. stable structural anchor
2. exact content-based anchor
3. fuzzy content-neighborhood fallback
4. operator-visible conflict if no reliable resolution remains

## Failure handling

Anchor failure must be surfaced explicitly.
Do not silently rebind to a questionable target.

## Invariants

1. Every captured reference should preserve at least one locator and one anchor.
2. Snapshots should preserve anchor material even if the live source later drifts.
3. Export should carry enough anchor data for downstream inspection where possible.
