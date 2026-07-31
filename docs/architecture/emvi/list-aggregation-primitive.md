# List Aggregation Primitive

Status: Draft v0.1

## Purpose

List aggregation is a shared primitive across browser, editor, terminal, and
agent-facing surfaces. It is not only a browser convenience.

## Problem

Open tabs, snippets, terminal outputs, graph rows, and service references are
usually trapped in separate tools. EMVI treats them as typed references that can
be captured into one working set.

## Core objects

- Resource
- Collection
- Snapshot
- Annotation

## Core verbs

- capture current
- capture selection
- capture all visible
- append to collection
- create snapshot
- export snapshot
- summarize collection
- compare collections
- publish/brief from collection

## Why it matters

- research sessions become portable
- multi-surface work becomes one typed working set
- agent summarization and curation have a stable input object
- exports become a first-class outcome rather than an afterthought

## Example flow

1. capture browser tabs into `collection:research`
2. capture an editor snippet into the same collection
3. capture shell output into the same collection
4. freeze a snapshot
5. export a briefing artifact
