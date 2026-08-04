"""Generalize the triad mechanism across a k-mesh of N backends — recursively, self-similarly.

A single triad rotates leadership 120° (cyclic C3) and survives on a 2-of-3 quorum. The k-mesh is
the SAME mechanism applied recursively: partition N backends into a balanced ternary tree of
triads, and apply the identical rotation + majority quorum at EVERY level. Nothing new is
invented for scale — a mesh is just a triad whose members are themselves triads, all the way down.

  * build_tree(nodes)   — a balanced ternary tree (leaves = backends; internal = ≤3 subtrees).
  * tree_leader(tree, e) — the single global leader at epoch e: a mixed-radix rotation that nests
                           the per-level cyclic pick (child = e mod c; recurse with e // c). For a
                           power of 3 this is exactly the 120°-per-level nesting; over one full
                           turn every backend leads exactly once (even coverage at any N).
  * tree_healthy(tree)   — recursive quorum-of-quorums: an internal group is healthy iff a strict
                           majority of its children are healthy; a leaf iff it is up. This is why
                           triads are the sweet spot — a size-3 group tolerates 1 failure at the
                           cost of 1 redundant member; a size-2 group tolerates none.

Deterministic and coordination-free at every level, so the same schedule/verifier logic that
governs one triad governs the whole mesh — that IS the answer to "the same mechanism for N backends."
"""
from __future__ import annotations

from typing import List, Union

# A tree is a leaf (backend id, str) or an internal node (list of up-to-3 subtrees).
Tree = Union[str, List["Tree"]]


def _split3(nodes: List[str]) -> List[List[str]]:
    """Split into up to 3 contiguous, as-equal-as-possible parts (the balanced ternary fan-out)."""
    n, k = len(nodes), 3
    sizes = [n // k + (1 if i < n % k else 0) for i in range(k)]
    parts, idx = [], 0
    for s in sizes:
        if s:
            parts.append(nodes[idx:idx + s])
            idx += s
    return parts


def build_tree(nodes: List[str]) -> Tree:
    """A balanced ternary tree over ``nodes`` (leaves = backends). Depth ~ log3(N)."""
    nodes = list(nodes)
    if not nodes:
        raise ValueError("mesh needs at least one backend")
    if len(nodes) <= 3:
        return list(nodes)  # a triad (or smaller) of leaves
    return [build_tree(p) for p in _split3(nodes)]


def leaves(tree: Tree) -> List[str]:
    if isinstance(tree, str):
        return [tree]
    out: List[str] = []
    for child in tree:
        out.extend(leaves(child))
    return out


def depth(tree: Tree) -> int:
    """Number of rotation levels from root to a leaf (a lone triad of leaves = depth 1)."""
    if isinstance(tree, str):
        return 0
    return 1 + max(depth(c) for c in tree)


def tree_leader(tree: Tree, epoch: int) -> str:
    """The single global leader at ``epoch`` — a mixed-radix rotation nested down the tree.

    At each internal node of arity c the leading child is ``epoch % c``; recurse into it with
    ``epoch // c`` so each level turns at its own rate (the fractal time nesting). For an all-3
    tree this is the 120°-per-level rotation; over one full turn every leaf leads exactly once.
    """
    if isinstance(tree, str):
        return tree
    c = len(tree)
    return tree_leader(tree[epoch % c], epoch // c)


def _quorum(c: int) -> int:
    """Strict majority of a group of arity c: 3->2 (tolerates 1), 2->2 (tolerates 0), 1->1."""
    return (c // 2) + 1


def tree_healthy(tree: Tree, up: set) -> bool:
    """Recursive quorum-of-quorums: a leaf is healthy iff up; an internal group iff a strict
    majority of its children are healthy. The whole mesh is operational iff its root is healthy."""
    if isinstance(tree, str):
        return tree in up
    healthy = sum(1 for child in tree if tree_healthy(child, up))
    return healthy >= _quorum(len(tree))


def turn_length(tree: Tree) -> int:
    """Epochs for one full rotation turn (the product of arities along the deepest path)."""
    if isinstance(tree, str):
        return 1
    return len(tree) * max(turn_length(c) for c in tree)
