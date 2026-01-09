package qes.provenance

# Minimal policy: a completed run MUST include these provenance fields.
# We’ll tighten this once qes-open emits concrete run records.

default allow := false

required_keys := {
  "git",
  "images",
  "schemas",
  "offsets"
}

allow {
  input.status == "completed"
  prov := input.provenance
  prov.git
  prov.images
  prov.schemas
  prov.offsets
}
