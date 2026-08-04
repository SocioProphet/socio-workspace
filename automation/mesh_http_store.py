"""Networked mesh transport — fragments and manifests move node-to-node over HTTP.

The last edge between "proven on real storage" and "running across physical nodes." MeshHttpStore
is a client that satisfies the SAME put/get/put_blob/get_blob seams as MeshFsStore, but reaches each
mesh node over HTTP instead of a local directory. A node runs a tiny server (make_node_server,
persistence injected) exposing PUT/GET for its fragments and manifest blobs. Nothing in
leaf_propagation / manifest_store changes — the interface is the contract, and the network is just a
different implementation of it.

Seizure / partition is modelled exactly as it happens: a node whose server is down or unroutable
raises on connect, which the client turns into ``None`` on read — an unreachable fragment, never a
healthy one. Writes fail loud (the writer must know a node rejected its fragment). Stdlib only
(urllib, http.server, threading) — no dependency, works on any silicon.
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


# ── the node server: a tiny key/value HTTP face over an injected backend ─────────────────────
class _NodeHandler(BaseHTTPRequestHandler):
    def _key(self) -> str:
        return self.path  # e.g. /frag/3 or /blob/<quoted>

    def do_PUT(self) -> None:
        length = int(self.headers.get("Content-Length", 0) or 0)
        data = self.rfile.read(length)
        self.server.kv[self._key()] = data  # type: ignore[attr-defined]
        self.send_response(204)
        self.end_headers()

    def do_GET(self) -> None:
        data = self.server.kv.get(self._key())  # type: ignore[attr-defined]
        if data is None:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args) -> None:  # keep tests/servers quiet
        pass


def make_node_server(kv: Optional[Dict[str, bytes]] = None) -> Tuple[ThreadingHTTPServer, str]:
    """Start a node's HTTP store on 127.0.0.1:<ephemeral> in a daemon thread. Returns (server, url).
    Call ``server.shutdown()`` to model that node being seized / partitioned away."""
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _NodeHandler)
    srv.kv = kv if kv is not None else {}      # type: ignore[attr-defined]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    host, port = srv.server_address
    return srv, f"http://{host}:{port}"


# ── the client: the put/get/put_blob/get_blob seams over HTTP ────────────────────────────────
class MeshHttpStore:
    """Reaches each node at ``node_urls[node]``. Unknown/unreachable node on read -> None."""

    def __init__(self, node_urls: Dict[str, str], *, timeout: float = 3.0):
        self.node_urls = dict(node_urls)
        self.timeout = timeout

    def _put(self, url: str, data: bytes) -> None:
        req = Request(url, data=data, method="PUT")
        with urlopen(req, timeout=self.timeout):  # noqa: S310 — trusted internal mesh URLs
            pass

    def _get(self, url: str) -> Optional[bytes]:
        try:
            with urlopen(url, timeout=self.timeout) as resp:  # noqa: S310
                return resp.read()
        except HTTPError as e:
            if e.code == 404:
                return None            # absent fragment on a reachable node
            raise
        except (URLError, OSError):
            return None                # node down / partitioned -> unreachable, not healthy

    def put(self, node: str, frag, data: bytes) -> None:
        self._put(f"{self.node_urls[node]}/frag/{quote(str(frag), safe='')}", data)

    def get(self, node: str, frag) -> Optional[bytes]:
        base = self.node_urls.get(node)
        return None if base is None else self._get(f"{base}/frag/{quote(str(frag), safe='')}")

    def put_blob(self, node: str, key: str, data: bytes) -> None:
        self._put(f"{self.node_urls[node]}/blob/{quote(key, safe='')}", data)

    def get_blob(self, node: str, key: str) -> Optional[bytes]:
        base = self.node_urls.get(node)
        return None if base is None else self._get(f"{base}/blob/{quote(key, safe='')}")
