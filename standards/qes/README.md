# QES (Quality Evaluation Service) Standard

This standard defines the *contracts* for end-to-end quality evaluation of an event-driven incident pipeline.
It is implementation-agnostic and Linux-first.

## Scope
- CloudEvents envelope + payload schemas
- Topic catalog (names, versions, compatibility expectations)
- RunSpec (how evaluations are declared)
- Evidence events (provenance + auditability)

## Non-negotiables
- Everything is events (CloudEvents 1.0)
- Deterministic replays (offset/time-window driven)
- Versioned schemas + compatibility policy
- Provenance captured per run (git SHAs, image digests, schema versions, offsets)

## Canonical topics (v1)
- normalized.alerts.v1
- normalized.logs.v1
- derived.stories.v1
- event.groups.v1
- event.localized.v1
- similar.incidents.v1
- log.anomalies.v1

## Files
- diagrams/qes-flow.mmd
- schemas/topics/topic-catalog.v1.yaml
- schemas/runspec/runspec.v1.json
