package mcp.guard

default allow = false
default danger_class = "LOW"

side_effect_tools := {"exec", "write", "delete"}

danger_class = "HIGH" {
  input.tool.name == "exec"
} else = "MEDIUM" {
  input.server == "egress.proxy"
}

# Human quorum check: count human signatures >= threshold for danger class
quorum_ok {
  need := { "MEDIUM": 2, "HIGH": 3 }[danger_class]
  count({ v | v := input.signatures[_]; v.kind == "human" }) >= need
}

# Main allow rule
allow {
  input.attestation.tpm_valid
  input.attestation.cosign_valid
  allowed := { 
    "fs.introspect/list", 
    "fs.introspect/hash",
    "net.observe/flows",
    "policy.eval/rego_eval"
  }
  concat("/", [input.server, input.tool.name]) == allowed[_]
  input.params.total_bytes <= input.policy.limits.bytes_max
  (danger_class == "LOW"; true) or quorum_ok
}
