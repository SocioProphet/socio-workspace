#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import re
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "tools" / "generate_active_spine_repo_graph.py"


@dataclass(frozen=True)
class RepositoryNode:
    node: str
    repository: str
    spine_role: str
    present_in_spine: bool
    present_in_manifest_overlay: bool
    present_in_canonical_sources: bool
    present_in_boundaries: bool
    present_in_topology: bool


@dataclass(frozen=True)
class GraphFixture:
    fixture_id: str
    corpus_loop: str
    policy_decision: str
    source_digest: str


@dataclass(frozen=True)
class GraphInput:
    source_path: str


class RepoGraphAdapter(Protocol):
    def repositories(self) -> list[RepositoryNode]: ...
    def graph_fixture(self) -> GraphFixture: ...
    def source_inputs(self) -> list[GraphInput]: ...


def _load_generator():
    spec = importlib.util.spec_from_file_location("generate_active_spine_repo_graph", GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load repo graph generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _literal(body: str, key: str) -> str:
    # A quoted literal is read whole: "." is legal inside one, and both source paths
    # ("catalog/boundaries.yaml") and fixture ids are dotted. Only an unquoted token
    # may be terminated by the statement "." or ";".
    # Only the quoted branch may be empty (so `""` still reads as ""); an unquoted
    # token must have at least one character, so a valueless `nrg:key ;` yields no
    # match rather than a silently empty value.
    pattern = rf'nrg:{key}\s+(?:"(?P<quoted>(?:[^"\\]|\\.)*)"|(?P<bare>[^\s;.]+))\s*[;.](?:\s|$)'
    match = re.search(pattern, body)
    if not match:
        return ""
    quoted = match.group("quoted")
    return quoted if quoted is not None else match.group("bare")


def _bool_literal(body: str, key: str) -> bool:
    return _literal(body, key) == "true"


class BootstrapRepoGraphAdapter:
    """No-dependency adapter for bootstrap CI.

    This adapter intentionally preserves the current generated-Turtle contract while
    isolating regex parsing behind a replaceable boundary. A future Prophet Platform
    adapter should implement the same protocol with RDF-native named graph traversal.
    """

    def __init__(self, graph: str | None = None) -> None:
        self._graph = graph

    def graph_text(self) -> str:
        if self._graph is None:
            generator = _load_generator()
            self._graph = generator.generate()
        return self._graph

    def repositories(self) -> list[RepositoryNode]:
        graph = self.graph_text()
        nodes: list[RepositoryNode] = []
        pattern = r"repo:([^\n]+)\n  a nrg:ActiveSpineRepository ;\n(?P<body>.*?)(?:\n\n|\Z)"
        for match in re.finditer(pattern, graph, re.DOTALL):
            body = match.group("body")
            nodes.append(RepositoryNode(
                node=match.group(1),
                repository=_literal(body, "repository"),
                spine_role=_literal(body, "spineRole"),
                present_in_spine=_bool_literal(body, "presentInSpine"),
                present_in_manifest_overlay=_bool_literal(body, "presentInManifestOverlay"),
                present_in_canonical_sources=_bool_literal(body, "presentInCanonicalSources"),
                present_in_boundaries=_bool_literal(body, "presentInBoundaries"),
                present_in_topology=_bool_literal(body, "presentInTopology"),
            ))
        return nodes

    def graph_fixture(self) -> GraphFixture:
        graph = self.graph_text()
        match = re.search(r"repo:active-spine-generated-graph\n(?P<body>.*?)(?:\n\n|\Z)", graph, re.DOTALL)
        if not match:
            raise ValueError("missing active-spine-generated-graph fixture")
        body = match.group("body")
        return GraphFixture(
            fixture_id=_literal(body, "fixtureId"),
            corpus_loop=_literal(body, "corpusLoop"),
            policy_decision=_literal(body, "policyDecision"),
            source_digest=_literal(body, "sourceDigest"),
        )

    def source_inputs(self) -> list[GraphInput]:
        graph = self.graph_text()
        inputs: list[GraphInput] = []
        pattern = r"repo:input-[^\n]+\n  a nrg:RepositoryGraphInput ;\n(?P<body>.*?)(?:\n\n|\Z)"
        for match in re.finditer(pattern, graph, re.DOTALL):
            source_path = _literal(match.group("body"), "sourcePath")
            if source_path:
                inputs.append(GraphInput(source_path=source_path))
        return inputs


def default_adapter() -> RepoGraphAdapter:
    return BootstrapRepoGraphAdapter()
