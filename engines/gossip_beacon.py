#!/usr/bin/env python3
"""Gossip beacon: percolate a change over the hypergraph, not just down a rule.

Rule dispatch answers "who did someone name as a target?". That is authored, precise,
and blind in three directions at once:

  SELF       the source repo gets no record that it emitted anything. A beacon with no
             self-hop cannot be audited from the node that caused it.
  UPSTREAM   edges are directed, and dispatch only ever walks them forwards. But when
             noetica-impair changes, superconscious -- whose schemas have exactly one
             executor -- has a real interest in knowing, and no forward edge says so.
  HYPEREDGE  a lane is not a bag of pairs. interpretability-harness binds eleven repos
             in ONE relation; flattening it to pairwise edges loses the fact that they
             are co-parties to the same thing, so a change reaches whoever happened to
             be named and no one else.

So this walks a hypergraph. Lanes are hyperedges, pairwise edges are the directed
skeleton, and a beacon percolates over both: self at hop 0, then upstream, downstream
and lateral (lane co-members) at each hop, bounded by TTL and converged by a seen-set.

── why gossip is LESS noisy here, not more ─────────────────────────────────────
The earlier cascade problem was hub blast: depth 2 through `sociosphere` reached four
unrelated maths repos, because graph distance is a bad proxy for relevance when a node
has many unrelated neighbours. Lateral spread does not have that failure mode -- it is
confined to lane membership, and a lane is a semantic set someone declared on purpose.
Eleven repos that all bind the same release doctrine are related BY CONSTRUCTION, which
is exactly what graph adjacency through a hub is not.

Lanes overlap (superconscious, sociosphere, agentplane and sourceos-spec are in both
interpretability-harness and lawful-learning), so this is a hypergraph rather than a
partition, and a beacon crossing an overlapping node reaches both lanes. That is the
intended behaviour: those repos are genuinely the seam between the two.

This module DECIDES NOTHING and sends nothing. It computes reach; the dispatcher in
propagation_engine decides what to act on.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "registry"

#: Beacons stay small on purpose. With lateral spread a lane is covered in one hop, so
#: a large TTL buys nothing but repetition through the directed skeleton.
DEFAULT_TTL = 2

DIRECTIONS = ("self", "lateral", "downstream", "upstream")


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def norm(repo: str | None) -> str | None:
    """Registry files disagree about org prefix and case; the beacon cannot.

    `SourceOS-Linux/sourceos-spec`, `sourceos_spec` and `sourceos-spec` are one node.
    Treating them as three would silently split a lane in half.
    """
    if not repo:
        return None
    r = str(repo).strip()
    if "/" in r:
        r = r.rsplit("/", 1)[-1]
    return r.replace("_", "-").lower() or None


class Hypergraph:
    """Lanes as hyperedges over a directed skeleton of pairwise edges."""

    def __init__(self, registry_dir: Path | None = None) -> None:
        self._dir = Path(registry_dir) if registry_dir else REGISTRY_DIR
        #: lane id -> member repos
        self.lanes: dict[str, set[str]] = defaultdict(set)
        #: repo -> lane ids it belongs to
        self.lanes_of: dict[str, set[str]] = defaultdict(set)
        self.out: dict[str, set[str]] = defaultdict(set)
        self.into: dict[str, set[str]] = defaultdict(set)
        #: members a registration declares but no edge connects
        self.unconnected: dict[str, set[str]] = defaultdict(set)
        #: lane -> members whose ONLY provenance is a future_* relationship or a
        #: deferred/pre_promotion edge. Declared into the lane, not yet party to it.
        self.deferred: dict[str, set[str]] = defaultdict(set)
        self.active_lanes: dict[str, set[str]] = defaultdict(set)
        self._loaded = False

    # ── loading ──────────────────────────────────────────────────────────────

    def _add_edge(self, src: str | None, dst: str | None) -> None:
        s, d = norm(src), norm(dst)
        if not s or not d or s == d:
            return
        self.out[s].add(d)
        self.into[d].add(s)

    def load(self) -> "Hypergraph":
        # Directed skeleton: the aggregate graph plus every additive lane pack. Packs
        # are included here even though propagation treats them as reference-only --
        # reach is not the same question as dependency, and a governance relationship
        # is exactly the kind of thing a beacon should travel along.
        agg = _load_yaml(self._dir / "dependency-graph.yaml")
        for e in agg.get("edges", []) or []:
            if isinstance(e, dict):
                self._add_edge(e.get("from"), e.get("to"))
        for repo, entry in (agg.get("dependencies") or {}).items():
            if isinstance(entry, dict):
                for dep in entry.get("depends_on", []) or []:
                    self._add_edge(repo, dep.get("name") if isinstance(dep, dict) else dep)

        edge_members: dict[str, set[str]] = defaultdict(set)
        active_edge_members: dict[str, set[str]] = defaultdict(set)
        for pack in sorted(self._dir.glob("*-dependency-edges.yaml")):
            for e in (_load_yaml(pack).get("edges") or []):
                if not isinstance(e, dict):
                    continue
                if str(e.get("state", "active")).lower() not in ("active", "in_use"):
                    lane = e.get("lane")
                    if lane:
                        for r in (norm(e.get("from")), norm(e.get("to"))):
                            if r:
                                edge_members[lane].add(r)
                    continue
                self._add_edge(e.get("from"), e.get("to"))
                lane = e.get("lane")
                if lane:
                    for r in (norm(e.get("from")), norm(e.get("to"))):
                        if r:
                            edge_members[lane].add(r)
                            active_edge_members[lane].add(r)

        # Hyperedges: a lane's membership is everything its registration names as a
        # surface or canonical relationship, plus everything its edges touch.
        for reg_path in sorted(self._dir.glob("*-registration.yaml")):
            reg = _load_yaml(reg_path)
            lane = (reg.get("lane") or {}).get("id")
            if not lane:
                continue
            declared: set[str] = set()
            for surface in (reg.get("surfaces") or {}).values():
                if isinstance(surface, dict) and (r := norm(surface.get("repo"))):
                    declared.add(r)
            active_declared: set[str] = set(declared)
            for key, val in (reg.get("canonical_relationships") or {}).items():
                if not isinstance(val, str) or not (r := norm(val)):
                    continue
                declared.add(r)
                # `future_*` names a relationship the lane INTENDS. Counting a future
                # owner as a co-party inflates every coverage gap with work nobody has
                # started, and drowns the genuine misses next to it.
                if not str(key).startswith("future_"):
                    active_declared.add(r)
            if owner := norm((reg.get("lane") or {}).get("owner_repo")):
                declared.add(owner)
                active_declared.add(owner)
            self.lanes[lane] |= declared
            self.active_lanes[lane] |= active_declared

        for lane, members in edge_members.items():
            self.lanes[lane] |= members
        for lane, members in active_edge_members.items():
            self.active_lanes[lane] |= members
        for lane, members in self.lanes.items():
            self.deferred[lane] = members - self.active_lanes.get(lane, set())

        for lane, members in self.lanes.items():
            for m in members:
                self.lanes_of[m].add(lane)
                # A lane member with no edge at all is declared into a relation that the
                # skeleton cannot see -- reachable laterally, invisible directionally.
                if not self.out.get(m) and not self.into.get(m):
                    self.unconnected[lane].add(m)

        self._loaded = True
        return self

    # ── the beacon ───────────────────────────────────────────────────────────

    def converge(self, source: str, *, max_cycles: int = 16,
                 directions: tuple[str, ...] = DIRECTIONS) -> dict[str, Any]:
        """Percolate to CLOSURE and report the cycle count it converged at.

        ``emit`` with a TTL answers "who is within N hops". That is a truncation, and a
        truncated beacon reported as a result is a partial cycle presented as a whole
        one -- some nodes were reached and their neighbours were never asked. Whether
        the frontier CLOSED is a different fact from how far it got, and only the first
        licenses "this is the reach".

        So this expands until the frontier empties (converged) or the cycle ceiling is
        hit (did NOT converge, and says so). The cycle count at closure is the beacon's
        frequency for that source: a low number means the source sits close to everything
        it can affect, a high one means the estate is deep in that direction.

        NOT claimed: any correspondence to the tetra/octa/icosa fundamental cycles. Those
        describe convergent geometry; a lane is a set of repos someone declared, sized by
        what the work needed. Reporting a cycle count is a measurement. Asserting the
        lanes realise those structures would be a typological parallel dressed as one,
        and the estate has a tag for that distinction precisely so it does not happen.
        """
        hops: list[dict[str, Any]] = []
        seen_total = 0
        converged = False
        cycles = 0
        for n in range(1, max_cycles + 1):
            hops = self.emit(source, ttl=n, directions=directions)
            if len(hops) == seen_total:
                converged = True
                cycles = n - 1
                break
            seen_total = len(hops)
            cycles = n
        return {
            "source": norm(source),
            "converged": converged,
            "cycles": cycles,
            "reach": len(hops),
            "max_cycles": max_cycles,
            "hops": hops,
            "note": ("closed at cycle %d" % cycles) if converged else
                    ("DID NOT CONVERGE within %d cycles; this reach is truncated, not "
                     "complete" % max_cycles),
        }

    def emit(self, source: str, *, ttl: int = DEFAULT_TTL,
             directions: tuple[str, ...] = DIRECTIONS,
             include_deferred: bool = False) -> list[dict[str, Any]]:
        """Percolate from ``source``, returning every hop in deterministic order.

        Convergence is by seen-set: a repo is recorded once, at the shortest hop that
        reached it, with the direction that got there first (lateral before directional,
        since co-party to the same lane is a stronger relation than an incident edge).
        Without that a beacon over a cyclic governance graph never terminates.
        """
        if not self._loaded:
            self.load()
        src = norm(source)
        if not src:
            return []

        hops: list[dict[str, Any]] = []
        seen = {src}
        if "self" in directions:
            hops.append({"repo": src, "direction": "self", "hop": 0,
                         "via": None, "lane": None})

        frontier = [src]
        for hop in range(1, max(0, ttl) + 1):
            nxt: list[str] = []
            # Lateral first so lane co-membership wins the seen-set race against a
            # merely incident edge.
            for node in frontier:
                if "lateral" in directions:
                    for lane in sorted(self.lanes_of.get(node, ())):
                        # Deferred members are declared into the lane but not yet party
                        # to it; beaconing them announces a relationship that does not
                        # exist. include_deferred surfaces them when auditing the lane.
                        members = (self.lanes[lane] if include_deferred
                                   else self.active_lanes.get(lane, self.lanes[lane]))
                        for peer in sorted(members):
                            if peer in seen:
                                continue
                            seen.add(peer)
                            nxt.append(peer)
                            hops.append({"repo": peer, "direction": "lateral",
                                         "hop": hop, "via": node, "lane": lane})
            for node in frontier:
                for direction, table in (("downstream", self.into),
                                         ("upstream", self.out)):
                    if direction not in directions:
                        continue
                    for peer in sorted(table.get(node, ())):
                        if peer in seen:
                            continue
                        seen.add(peer)
                        nxt.append(peer)
                        hops.append({"repo": peer, "direction": direction,
                                     "hop": hop, "via": node, "lane": None})
            if not nxt:
                break
            frontier = nxt
        return hops


def _report(source: str, hops: list[dict[str, Any]]) -> None:
    if not hops:
        print(f"no beacon reach from {source!r}")
        return
    by_dir: dict[str, int] = defaultdict(int)
    for h in hops:
        by_dir[h["direction"]] += 1
    print(f"beacon from {source}: {len(hops)} node(s) "
          + ", ".join(f"{k}={by_dir[k]}" for k in DIRECTIONS if by_dir[k]))
    for h in hops:
        tag = f"{h['direction']}"
        if h["lane"]:
            tag += f"/{h['lane']}"
        via = f" via {h['via']}" if h["via"] else ""
        print(f"  hop{h['hop']}  [{tag}] {h['repo']}{via}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["emit", "converge", "lanes", "audit"])
    ap.add_argument("--repo")
    ap.add_argument("--ttl", type=int, default=DEFAULT_TTL)
    ap.add_argument("--directions", default=",".join(DIRECTIONS),
                    help="comma-separated subset of " + ",".join(DIRECTIONS))
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    g = Hypergraph().load()

    if args.cmd == "lanes":
        out = {lane: sorted(m) for lane, m in sorted(g.lanes.items())}
        if args.format == "json":
            print(json.dumps(out, indent=2))
        else:
            for lane, members in out.items():
                overlap = [m for m in members if len(g.lanes_of[m]) > 1]
                print(f"{lane}: {len(members)} member(s)"
                      + (f", {len(overlap)} shared with another lane" if overlap else ""))
                for m in members:
                    mark = " *" if m in overlap else ""
                    print(f"  {m}{mark}")
        return 0

    if args.cmd == "audit":
        problems = 0
        for lane, members in sorted(g.lanes.items()):
            if len(members) < 2:
                print(f"FAIL {lane}: {len(members)} member(s) — a hyperedge binding "
                      "fewer than two repos is not a relation", file=sys.stderr)
                problems += 1
            stranded = sorted(g.unconnected.get(lane, ()))
            if stranded:
                # Not fatal: a lane may legitimately name a future owner. But it must be
                # visible, because "declared into a lane, connected to nothing" is how a
                # repo ends up governed on paper and unreachable in practice.
                print(f"WARN {lane}: {', '.join(stranded)} declared as member(s) but "
                      "carry no edge in either direction")
        if problems:
            return 1
        print(f"OK: {len(g.lanes)} hyperedge(s), "
              f"{sum(len(m) for m in g.lanes.values())} membership(s)")
        return 0

    if not args.repo:
        print("ERROR: --repo is required", file=sys.stderr)
        return 2
    dirs = tuple(d.strip() for d in args.directions.split(",") if d.strip())

    if args.cmd == "converge":
        res = g.converge(args.repo, directions=dirs)
        if args.format == "json":
            print(json.dumps(res, indent=2))
        else:
            mark = "CONVERGED" if res["converged"] else "TRUNCATED"
            print(f"[{mark}] {res['source']}: reach={res['reach']} "
                  f"cycles={res['cycles']}  ({res['note']})")
            _report(args.repo, res["hops"])
        return 0 if res["converged"] else 1
    hops = g.emit(args.repo, ttl=args.ttl, directions=dirs)
    if args.format == "json":
        print(json.dumps({"source": norm(args.repo), "ttl": args.ttl,
                          "directions": list(dirs), "hops": hops}, indent=2))
    else:
        _report(args.repo, hops)
    return 0


if __name__ == "__main__":
    sys.exit(main())
