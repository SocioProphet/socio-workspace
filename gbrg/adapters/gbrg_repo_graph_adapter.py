#!/usr/bin/env python3
"""GBRG code-aware evidence producer implementing the RepoGraphAdapter protocol.

The estate ships a ``RepoGraphAdapter`` Protocol
(``tools/repo_graph_adapter.py``) with a ``BootstrapRepoGraphAdapter`` whose
docstring invites: *"A future Prophet Platform adapter should implement the same
protocol"*. This module is that adapter, implemented at CODE granularity: it
consumes GBRG ``gbrg-analyze`` ProofArtifacts and satisfies the SAME protocol —

    repositories()   -> roll ProofArtifacts up to repository nodes
    graph_fixture()  -> the corpus-loop-pinned governance fixture header
    source_inputs()  -> the parsed source files the artifacts came from

plus two GBRG-specific evidence surfaces that emit
``repo-governance-observation.v0`` records (see ``evidence.py``), making GBRG a
first-class evidence source for the governance corpus loop:

    evidence_records()       -> blast-radius observations (per code cell)
    risk_evidence_records()  -> supply-chain RISK observations (node/path/cluster,
                                via the live supply_chain_pipeline scorer)

CONSUME-ONLY: this adapter READS the estate protocol (``repo_graph_adapter.py``)
and the corpus-loop pin as its contract; it never modifies them. All new code
lives under ``gbrg/``.

EVIDENCE, NEVER AUTHORIZATION: :meth:`graph_fixture` returns the protocol's
``GraphFixture`` whose shape includes a ``policy_decision`` field. GBRG is an
evidence source and does NOT decide policy, so it leaves ``policy_decision``
EMPTY for policy-fabric to fill. It never fabricates an allow/deny.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from . import evidence as gbrg_evidence

# ── Consume-only imports of the estate protocol dataclasses ──────────────────
# Load tools/repo_graph_adapter.py by path (it is not an importable package) and
# reuse its RepositoryNode / GraphFixture / GraphInput / RepoGraphAdapter shapes
# verbatim, so this adapter conforms to the exact estate contract.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PROTOCOL_PATH = _REPO_ROOT / "tools" / "repo_graph_adapter.py"
_CORPUS_PIN = _REPO_ROOT / "registry" / "corpus-loop-v1" / "valid.watson-cyc-chronos.pinned.json"


def _load_protocol():
    spec = importlib.util.spec_from_file_location("estate_repo_graph_adapter", _PROTOCOL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load estate protocol at {_PROTOCOL_PATH}")
    module = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass annotation resolution can find the module.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_PROTO = _load_protocol()
RepositoryNode = _PROTO.RepositoryNode
GraphFixture = _PROTO.GraphFixture
GraphInput = _PROTO.GraphInput
RepoGraphAdapter = _PROTO.RepoGraphAdapter


def _corpus_loop_id() -> str:
    """The pinned corpus-loop id (read from the estate pin; no drift)."""
    pin = json.loads(_CORPUS_PIN.read_text(encoding="utf-8"))
    return pin["loop_id"]  # "watson-cyc-semantic-web-chronos-v1"


class GbrgRepoGraphAdapter:
    """RepoGraphAdapter over GBRG ProofArtifacts (code granularity).

    Parameters
    ----------
    artifacts:
        List of ``gbrg-analyze`` ProofArtifact dicts (as emitted / persisted).
    subject_repository:
        The ``owner/repo`` the parsed code belongs to (the monorepo housing the
        crates). Defaults to ``SocioProphet/sociosphere``.
    repo_root:
        Filesystem root used to resolve source blob SHAs. Defaults to the
        sociosphere worktree root.
    """

    def __init__(
        self,
        artifacts: list[dict[str, Any]],
        *,
        edges: list[dict[str, Any]] | None = None,
        subject_repository: str = "SocioProphet/sociosphere",
        repo_root: str | Path = _REPO_ROOT,
    ) -> None:
        self._artifacts = list(artifacts)
        self._edges = list(edges or [])
        self._subject_repository = subject_repository
        self._repo_root = Path(repo_root)

    # ── constructors ────────────────────────────────────────────────────────
    @classmethod
    def from_fixture_dir(cls, directory: str | Path, **kwargs: Any) -> "GbrgRepoGraphAdapter":
        """Load every ``proof-artifact*.json`` in a directory (e.g. real fixtures)."""
        directory = Path(directory)
        artifacts: list[dict[str, Any]] = []
        for path in sorted(directory.glob("proof-artifact*.json")):
            artifacts.append(json.loads(path.read_text(encoding="utf-8")))
        return cls(artifacts, **kwargs)

    @classmethod
    def from_bundle(cls, bundle: dict[str, Any] | str | Path, **kwargs: Any) -> "GbrgRepoGraphAdapter":
        """Load a ``gbrg-analyze --emit-edges`` bundle ``{artifacts, edges}``.

        Accepts the bundle dict directly or a path to it. Carrying the edges lets
        :meth:`risk_evidence_records` derive real CALLS paths (not just nodes).
        """
        if isinstance(bundle, (str, Path)):
            bundle = json.loads(Path(bundle).read_text(encoding="utf-8"))
        if isinstance(bundle, list):  # bare artifact array (no edges)
            bundle = {"artifacts": bundle, "edges": []}
        return cls(bundle.get("artifacts", []), edges=bundle.get("edges", []), **kwargs)

    # ── RepoGraphAdapter protocol ────────────────────────────────────────────
    def repositories(self) -> list[Any]:
        """Roll the code-cell artifacts UP to repository nodes.

        GBRG observes CODE, so a rolled-up repo node is present_in_canonical_sources
        (we parsed its source) and present_in_topology (we reason about its code
        dependency graph). It makes NO claim about spine/manifest/boundary
        presence — those are other producers' surfaces, left False.
        """
        if not self._artifacts:
            return []
        repo = self._subject_repository
        return [
            RepositoryNode(
                node=repo.split("/")[-1],
                repository=repo,
                spine_role="code-evidence-source",
                present_in_spine=False,
                present_in_manifest_overlay=False,
                present_in_canonical_sources=True,
                present_in_boundaries=False,
                present_in_topology=True,
            )
        ]

    def graph_fixture(self) -> Any:
        """The governance fixture header for this evidence batch.

        ``corpus_loop`` is pinned to the estate corpus-loop id. ``policy_decision``
        is EMPTY: GBRG is evidence-only and does not decide policy.
        """
        return GraphFixture(
            fixture_id="gbrg-code-evidence",
            corpus_loop=_corpus_loop_id(),
            policy_decision="",  # evidence-only: GBRG never emits a decision
            source_digest=self._source_digest(),
        )

    def source_inputs(self) -> list[Any]:
        """The distinct source files the ProofArtifacts were parsed from."""
        seen: dict[str, Any] = {}
        for artifact in self._artifacts:
            path = gbrg_evidence.cell_source_path(artifact["cell_id"])
            seen.setdefault(path, GraphInput(source_path=path))
        return list(seen.values())

    # ── GBRG evidence surface ────────────────────────────────────────────────
    def evidence_records(self) -> list[dict[str, Any]]:
        """All blast-radius evidence ENVELOPES (record + gbrg_extension) per artifact."""
        envelopes: list[dict[str, Any]] = []
        for artifact in self._artifacts:
            envelopes.extend(
                gbrg_evidence.proof_to_observations(
                    artifact,
                    subject_repository=self._subject_repository,
                    repo_root=self._repo_root,
                )
            )
        return envelopes

    def risk_evidence_records(
        self,
        *,
        evidence_index: dict[str, list[dict[str, Any]]] | None = None,
        tier0: bool = True,
    ) -> list[dict[str, Any]]:
        """Supply-chain RISK evidence ENVELOPES for node/path/cluster subjects.

        Runs the live scoring pipeline over this adapter's artifacts + edges (the
        UNMODIFIED ``supply_chain_risk`` scorer, fed graph-derived factors) and
        lifts each sealed ``SupplyChainRiskProofArtifact`` onto the evidence plane
        via the same evidence-only invariant as :meth:`evidence_records`. With no
        ``evidence_index`` and ``tier0``, every subject fails CLOSED (REJECTED).
        Imported lazily so the blast-radius surface has no scoring dependency.
        """
        from gbrg.governance import supply_chain_pipeline as pipeline

        result = pipeline.assess_estate(
            {"artifacts": self._artifacts, "edges": self._edges},
            evidence_index=evidence_index, tier0=tier0, persist=False,
        )
        return pipeline.estate_evidence_envelopes(
            result,
            subject_repository=self._subject_repository,
            repo_root=self._repo_root,
        )

    # ── helpers ──────────────────────────────────────────────────────────────
    def _source_digest(self) -> str:
        import hashlib

        paths = sorted(gi.source_path for gi in self.source_inputs())
        return hashlib.sha256("\n".join(paths).encode("utf-8")).hexdigest()
