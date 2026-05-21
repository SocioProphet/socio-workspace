# Source Quality Validation Plan

Status: tooling specification scaffold.

## Purpose

Validate that corpus records satisfy governance requirements before they:

- generate implementation issues
- enter public summaries
- emit graph edges
- become reusable benchmark references

## Required checks

### Author records

Required:
- stable author ID
- name
- layer
- status
- at least one cluster
- at least one target component

Warnings:
- missing bibliography identifiers
- unresolved author disambiguation
- only title-level works present

### Paper records

Required for implementation-ready state:
- canonical title
- year
- ordered authors
- source_quality >= confirmed_bibliographic
- at least one source URL or DOI/arXiv key

Warnings:
- preprint only
- no PDF review
- unresolved venue
- unresolved duplicate/version lineage

### Artifact records

Required for reusable state:
- artifact ID
- source URL
- access status
- reuse mode
- license review status

Warnings:
- unknown license
- unknown artifact availability
- patent overlap unresolved

### Patent records

Required before implementation reuse:
- patent family identification
- assignee
- active/expired status
- design-around note

Warnings:
- claims not reviewed
- licensing unclear
- enterprise workflow overlap

## Blocking rules

- `plausible_needs_source` and `speculative_do_not_use` records cannot generate implementation issues.
- Patent-sensitive records require design-around review.
- Unknown-license artifacts cannot become reusable dependencies.
- Provisional paper-version edges cannot be treated as canonical lineage.

## Planned outputs

- validation report
- blocked queue update
- implementation-safe subset export
- public-safe subset export
- graph-quality warnings
