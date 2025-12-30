package mcp.guard

test_allow_low_danger {
  allow with input as {
    "attestation": {"tpm_valid": true, "cosign_valid": true},
    "server": "fs.introspect",
    "tool": {"name": "list"},
    "params": {"total_bytes": 0},
    "policy": {"limits": {"bytes_max": 10}},
    "signatures": [{"kind": "human"}]
  }
}
