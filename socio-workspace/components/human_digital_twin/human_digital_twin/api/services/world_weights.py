
from typing import Dict, List, Tuple
def degree_weights(graph_edges: List[Tuple[str, str]]) -> Dict[str, float]:
    deg = {}
    for u, v in graph_edges: deg[u]=deg.get(u,0)+1; deg[v]=deg.get(v,0)+1
    total = sum(deg.values()) or 1.0
    return {k: v/total for k,v in deg.items()}
def world_weights(strategy: str, **kwargs) -> Dict[str, float]:
    if strategy == "degree": return degree_weights(kwargs.get("edges", []))
    if strategy == "empirical":
        edges = kwargs.get("edges", []); rel = kwargs.get("reliability", {}); base = degree_weights(edges)
        mixed = {k: base.get(k,0.0)*(0.5+0.5*rel.get(k,0.5)) for k in base}; s=sum(mixed.values()) or 1.0
        return {k: v/s for k,v in mixed.items()}
    return {}
