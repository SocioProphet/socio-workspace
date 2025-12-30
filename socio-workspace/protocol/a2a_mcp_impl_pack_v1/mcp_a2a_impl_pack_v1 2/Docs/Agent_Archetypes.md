# Agent Archetypes (Base Classes, Features, and Permutations)

> This document uses the uploaded **MCP + A2A** diagram as the canonical reference for host roles and tool planes.
> See: `Docs/images/mcp_a2a_source.png`

## Base Class Templates

### 1. MCPHost
- **Role:** Hosts MCP clients; terminates A2A; requests/holds Grants.
- **Modules:** Identity (SPIFFE), Attestation (TPM/FIDO2 + cosign), GrantCache, LedgerEmitter.
- **Template (YAML extract):**
```yaml
kind: MCPHost
identity: spiffe://sourceos/<role>
a2a_endpoint: https://a2a/<role>
grant_ttl_sec: 900
ledger: { mode: append-only, sink: worm }
```

### 2. MCPServer
- **Role:** Expose narrow tools with declared **effect**: `read|write|compute`.
- **Modules:** SchemaValidator, RateLimiter, Redactor, SandboxAdaptor.
- **Template:**
```yaml
kind: MCPServer
name: fs.introspect
tools:
  - name: list
    effect: read
    input_schema: MCP/schemas/fs_list.schema.json
```

### 3. PolicyArbiter
- **Role:** Offloads all allow/deny to OPA.
- **Modules:** RegoBundleLoader, DecisionLogger.
```yaml
kind: PolicyArbiter
opa_url: http://opa:8181/v1/data/mcp/guard/allow
bundle: Policy/opa
```

### 4. EgressProxy
- **Role:** Single outbound chokepoint.
- **Modules:** Allowlist, DLP, RateLimiter, TLSPinning.
```yaml
kind: EgressProxy
allow_domains: ["slack.com","www.googleapis.com"]
dlp: Policy/dlp/patterns.yaml
```

### 5. ReplayRunner
- **Role:** Deterministic replay/simulation.
- **Modules:** Sandbox(gVisor|Kata), TraceExporter.
```yaml
kind: ReplayRunner
sandbox: gVisor
network: none
```

## Archetype Classes

1. **Inception Host (Edge MCPHost)**
   - **Servers:** fs.introspect, proc.inspect, net.observe, attest.local
   - **Traits:** Read-heavy; DLP+redaction; human-in-the-loop for side-effects.

2. **Twin Host (Cloud MCPHost)**
   - **Servers:** policy.eval, datalake.write, replay.sim, egress.proxy, c2.detector
   - **Traits:** Compute-heavy; immutability; strict egress pinning.

3. **Collector Agent (Edge Server specialisation)**
   - Minimal read-only toolset; zero egress; high-rate limits but small byte caps.

4. **Analyst Agent (Twin Server specialisation)**
   - compute-only; network disabled; produces traces exported to WORM.

5. **Coordinator (A2A + PolicyArbiter)**
   - Negotiates grants; enforces quorum; writes decision logs.

6. **Egress Gateway (EgressProxy)**
   - Mediates all Internet IO; terminates TLS; injects provenance headers.

7. **Validator Agent**
   - Human signature capturer; not an MCP server; binds signatures to grants.

## Modular, Composable Features

- **Identity/Attestation Module**
- **Redaction/DLP Module**
- **Sandbox Module (gVisor/Kata)**
- **Provenance Module (cosign+ledger)**
- **Quorum Module (UI+signature collector)**
- **Egress Control Module (allowlist, DLP)**

## Permutation Matrix (examples)

| Archetype | Identity | Attestation | Sandbox | Egress | DLP/Redact | Quorum | Ledger | Typical Tools |
|---|---|---|---|---|---|---|---|---|
| Inception Host | SPIFFE | TPM+cosign | Bwrap | none | edge | MEDIUM | on | fs.*, proc.*, net.* |
| Twin Host | SPIFFE | cosign | gVisor/Kata | proxy | twin | HIGH | on | policy.*, replay.*, datalake.*, egress.* |
| Collector | SPIFFE | TPM | Bwrap | none | edge | LOW | on | fs.list/hash |
| Analyst | SPIFFE | cosign | gVisor | none | twin | LOW | on | replay.run/export |
| Coordinator | SPIFFE | cosign | n/a | none | n/a | HIGH | on | a2a.* |
| Egress Gateway | SPIFFE | cosign | n/a | proxy | twin | MEDIUM | on | egress.http |
| Validator | human | FIDO2 | n/a | none | n/a | n/a | on | approvals |

## Code Skeletons (Python)

```python
# mcp_host.py (simplified)
class Grant: ...
class MCPHost:
    def __init__(self, spiffe_id, a2a_client, opa_client, ledger):
        self.spiffe_id = spiffe_id
        self.a2a = a2a_client
        self.opa = opa_client
        self.ledger = ledger
    def negotiate(self, capabilities):
        hello = self.a2a.hello(self.spiffe_id)
        att = self.a2a.attest(self._tpm_quote(), self._cosign_bundle())
        disc = self.a2a.discover(self._advertise(capabilities))
        grant = self.a2a.negotiate(self._request(capabilities), policy_hash=self.opa.policy_hash())
        self._store_grant(grant)
        return grant
```

## Image References
- **MCP + A2A** (uploaded): `Docs/images/mcp_a2a_source.png`
- **Archetype Stack** (generated): `Docs/images/archetype_stack.png`
- **Permutation Grid** (generated): `Docs/images/permutation_grid.png`
