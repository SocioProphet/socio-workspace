"""The propagation path over a REAL network — fragments/manifests move node-to-node via HTTP,
against loopback servers. Seizure = shutting a node's server down (connection refused -> unreachable)."""
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation.holographic_ida import merkle_root  # noqa: E402
from automation.leaf_propagation import LeafUnavailable, fetch, propagate  # noqa: E402
from automation.manifest_store import publish_manifest, resolve_manifest  # noqa: E402
from automation.mesh_http_store import MeshHttpStore, make_node_server  # noqa: E402
from automation.storage_resilience import Placement

P = Placement(rs_k=6, rs_m=3)  # 9 fragments -> 9 nodes


@contextmanager
def mesh(n):
    """Bring up n node servers on loopback; yield (store, node_urls, servers); tear all down."""
    servers = {}
    urls = {}
    try:
        for i in range(n):
            node = f"n{i:02d}"
            srv, url = make_node_server()
            servers[node], urls[node] = srv, url
    except (OSError, PermissionError) as e:
        for srv in servers.values():
            srv.shutdown()
            srv.server_close()
        pytest.skip(f"loopback sockets unavailable in this environment: {e}")
    try:
        yield MeshHttpStore(urls, timeout=2.0), urls, servers
    finally:
        for srv in servers.values():
            srv.shutdown()
            srv.server_close()


def test_write_read_over_http():
    with mesh(9) as (store, urls, _):
        leaf = b"leaf over the wire " + os.urandom(48)
        m = propagate(leaf, nodes=list(urls), put=store.put, placement=P)
        assert fetch(m, get=store.get) == leaf


def test_survives_seized_nodes_over_http():
    with mesh(9) as (store, urls, servers):
        leaf = os.urandom(60)
        m = propagate(leaf, nodes=list(urls), put=store.put, placement=P)
        # seize 3 nodes -> their servers go down; 6 survive == k -> still reconstruct.
        frag_nodes = [nd for lst in m.fragment_nodes.values() for nd in lst]
        seized = frag_nodes[:3]
        for nd in seized:
            servers[nd].shutdown()
        reachable = set(urls) - set(seized)
        assert fetch(m, get=store.get, reachable=reachable) == leaf


def test_below_quorum_over_http_is_unavailable():
    with mesh(9) as (store, urls, servers):
        leaf = os.urandom(40)
        m = propagate(leaf, nodes=list(urls), put=store.put, placement=P)
        frag_nodes = [nd for lst in m.fragment_nodes.values() for nd in lst]
        for nd in frag_nodes[:4]:            # seize 4 -> only 5 < k=6 reachable
            servers[nd].shutdown()
        reachable = set(urls) - set(frag_nodes[:4])
        try:
            fetch(m, get=store.get, reachable=reachable)
        except LeafUnavailable:
            pass
        else:
            raise AssertionError("below quorum over HTTP must be LeafUnavailable")


def test_manifest_resolve_and_reconstruct_over_http_knowing_only_root():
    with mesh(12) as (store, urls, servers):
        leaf = b"GOVERNED :: " + os.urandom(64)
        m = propagate(leaf, nodes=list(urls), put=store.put, placement=P)
        publish_manifest(m, nodes=list(urls), put_blob=store.put_blob, replicas=4)
        root = m.root

        # seize 3 nodes; a manifest replica + a fragment quorum still survive.
        frag_nodes = [nd for lst in m.fragment_nodes.values() for nd in lst]
        seized = frag_nodes[:3]
        for nd in seized:
            servers[nd].shutdown()
        reachable = set(urls) - set(seized)

        manifest = resolve_manifest(root, nodes=list(urls), get_blob=store.get_blob,
                                    replicas=4, reachable=reachable)
        back = fetch(manifest, get=store.get, reachable=reachable)
        assert back == leaf and merkle_root(back) == root


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
    print(f"mesh_http_store: {len(fns)}/{len(fns)} tests pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
