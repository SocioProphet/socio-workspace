# Protocol (placeholder)

This workspace is the canonical home for the protocol schema, fixtures, and adapter contract tests.

Current assumptions (carried from prior spec):
- `op: "hello"` handshake
- protocol_version negotiation
- capability negotiation
- canonical error codes

Next: move the canonical JSON schemas + fixture vectors into `protocol/fixtures/` and wire them into `runner run protocol:test`.
