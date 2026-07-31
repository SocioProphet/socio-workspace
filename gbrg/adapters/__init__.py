"""GBRG code-aware evidence producer for the neurosymbolic-repo-graph-reasoner.

Implements the estate ``RepoGraphAdapter`` protocol at CODE granularity and maps
GBRG ProofArtifacts to ``repo-governance-observation.v0`` EVIDENCE records.

EVIDENCE, NEVER AUTHORIZATION: this package emits evidence for policy-fabric to
act on; it never emits a policyDecision or any authorization/verdict field.
"""
