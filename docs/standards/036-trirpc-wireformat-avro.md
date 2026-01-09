# 036 - TriRPC Wireformat v0 (Avro + Stream Framing)

## Status
- Version: v0
- Normative for TriRPC messages.

## Goals
- Portable typed messaging across languages
- Stream/micro-batch/batch compatibility
- Schema-identified payloads

## Layering
- Layer 0: stream framing (OPEN/DATA/CLOSE/ERROR/CONTROL)
- Layer 1: TriRPC Envelope (Avro record)
- Layer 2: payload (Avro Value, raw bytes, or artifact ref)

## Envelope Requirements (MUST)
Envelope MUST include:
- protocol_version
- message_kind enum: CALL|DATA|RESULT|ERROR|CONTROL
- schema_ref (optional): fp256 + hints
- correlation_id / trace ids
- flags (bitset)
- payload bytes or payload_ref

## Value Requirements (MUST)
Core Value universe MUST support:
- primitives, list, tuple, tagged sum types
Complex types MUST be normalized via Pack/Unpack rules in 034.

## Streaming Semantics (MUST)
- OPEN starts a stream_id
- DATA carries ordered seq_no frames
- CLOSE ends stream_id
- ERROR terminates stream_id with typed error payload
- CONTROL conveys micro-batch boundaries, watermarks, checkpoints

## Compatibility
- Backward-compatible evolution MUST follow Avro reader/writer schema rules
- Breaking changes require new schema fp256 (and version bump policy)
