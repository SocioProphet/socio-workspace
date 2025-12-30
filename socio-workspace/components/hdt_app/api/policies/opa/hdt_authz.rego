package hdt.authz

default allow = false

allow {
  input.action == "read"
  input.purpose_of_use == "treatment"
  input.requester.role == "treating_provider"
}
allow {
  input.action == "export"
  input.purpose_of_use == "research_deid"
}
allow {
  input.action == "read"
  input.purpose_of_use == "emergency"
  input.break_glass == true
}
