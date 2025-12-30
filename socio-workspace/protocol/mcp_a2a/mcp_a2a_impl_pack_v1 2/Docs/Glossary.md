# Glossary (Inception + Digital‑Twin MCP/A2A)

**A2A (Agent-to-Agent)** — Control plane protocol for negotiation between agents (HELLO, ATTEST, DISCOVER, NEGOTIATE, GRANT, REVOKE).

**AUM (Agent Update/Manifest)** — Package format describing agent identity, capabilities, policies, and runtime constraints.

**DAG (Directed Acyclic Graph)** — Ordered steps/pipeline describing deterministic execution with edges and nodes.

**DLP (Data Loss Prevention)** — Pattern matching and heuristics to prevent sensitive data from leaving a trust boundary.

**Falco** — Open-source runtime security tool that detects suspicious syscalls or container events.

**gVisor/Kata** — Sandboxed runtimes: gVisor intercepts syscalls; Kata runs workloads in lightweight VMs.

**Grant** — Short-lived token describing permitted capabilities, scope, and TTL negotiated via A2A.

**MCP (Model Context Protocol)** — Protocol where clients call servers exposing tools/resources under a shared schema/transport (e.g., stdio/JSON-RPC).

**OPA/Rego** — Open Policy Agent with Rego policy language for declarative, testable authorization decisions.

**Quorum (Human)** — Required count of human signatures/approvals based on operation danger class (e.g., 2-of-3).

**RegO Decision Log** — Audit trail of inputs/outputs to policy decisions.

**Sigstore/cosign** — Open tooling to sign and verify artifacts, producing cryptographically verifiable provenance.

**SPIFFE/SVID** — Identity framework for workloads; Secure Production Identity Framework for Everyone; SVID is the issued identity document.

**TPM/FIDO2** — Hardware roots of trust for device and user-bound attestation.

**Twin (Digital‑Twin)** — Cloud-side counterpart that runs simulations/replays and hosts data/egress services.

**WORM (Write Once Read Many)** — Storage mode enforcing immutability for evidentiary objects.
