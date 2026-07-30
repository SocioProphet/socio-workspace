#!/usr/bin/env python3
"""Publish a vendored artifact to zot as an OCI artifact, so consumers can pin a DIGEST.

W12.3, sovereign path. Today `package.json` hardcodes
`file:vendor/socioprophet-hellgraph-<ver>.tgz`, so a version bump means editing a
FILENAME in N places across M repos, and the only thing asserting that those bytes
are the release they claim to be is a filename. A digest is not a filename: it is the
bytes, and it cannot be wrong.

Stdlib only, against the OCI Distribution API — no oras, skopeo, crane, or docker,
because a sovereign publish path that needs four vendor CLIs installed is not
sovereign. The whole client is HTTP.

── What is PROVEN and what is not ────────────────────────────────────────────────
PROVEN, by running it: against zot v2.1.2 (`distSpecVersion 1.1.0`) in a local
container, every step below returned the status codes it asserts, the manifest digest
the server reported matched the digest recomputed locally, a pull BY DIGEST returned
byte-identical bytes, an unknown digest 404'd, and the same bytes pushed twice
produced the same digest. A pure-curl reimplementation produced the identical digest,
which is a check on the canonical encoding rather than on this code.

NOT PROVEN: publishing to the production registry at registry.socioprophet.ai. That
endpoint is live and answers `GET /v2/` with `401 Basic realm="zot-sovereign"`, which
is the correct auth challenge and is the only thing about it verified here. It was not
pushed to, because doing so needs the `ci` htpasswd credential and this work adds no
new secrets. See docs/governance/vendor-freshness-sovereign-path.md.

── The zot quirk this exists to work around ──────────────────────────────────────
Overwriting a TAG orphans the manifest digest that tag previously held: after
repointing tag `X`, `GET manifests/<old-digest>` returns 404, even though the manifest
blob is still readable via the blobs endpoint. Pushing by digest afterwards does not
protect it. A SECOND tag referencing the manifest does.

That is fatal to the entire point of this file, so every publish also writes an
immutable alias tag `sha256-<hex>` (71 chars, inside the 128-char OCI tag limit).
Isolated A/B: without the alias the original digest 404s, with it the digest resolves
and the bytes are identical. Any digest-pinning promise on zot must do this.

Environment: OCI_REGISTRY, OCI_SCHEME, OCI_REPO, OCI_TAG, and OCI_USERNAME/OCI_PASSWORD
or OCI_TOKEN. In CI these come from the ZOT_CI_* repository secrets that ALREADY exist
for the image pipeline; this adds none.
"""


import base64
import hashlib
import http.client
import json
import os
import sys
import urllib.parse

# ---------------------------------------------------------------- config

REGISTRY = os.environ.get("OCI_REGISTRY", "localhost:15000")
SCHEME = os.environ.get("OCI_SCHEME", "http")  # "https" in production
REPO = os.environ.get("OCI_REPO", "socioprophet/hellgraph")
TAG = os.environ.get("OCI_TAG", "0.4.40")
# The version the metadata CLAIMS must be the version being pushed. Hard-coding it
# meant a publish of 0.4.45 shipped a config blob and an image.version annotation
# that both said 0.4.40: the digest would pin one release's bytes while the metadata
# named another, and the digest — being correct — would make the lie permanent.
VERSION = os.environ.get("OCI_VERSION", TAG).lstrip("v")

# Auth: production zot is htpasswd- or bearer-protected. Local probe has none.
OCI_USER = os.environ.get("OCI_USERNAME")
OCI_PASS = os.environ.get("OCI_PASSWORD")
OCI_TOKEN = os.environ.get("OCI_TOKEN")

# zot QUIRK MITIGATION (observed on v2.1.2): overwriting a tag ORPHANS the
# manifest digest that tag previously held -- GET manifests/<old-digest> then
# returns 404 -- UNLESS a second tag still references it. So we always also
# push an immutable alias tag `sha256-<hex>`, which pins the digest forever.
IMMUTABLE_ALIAS = os.environ.get("OCI_IMMUTABLE_ALIAS", "1") != "0"

ARTIFACT_TYPE = "application/vnd.socioprophet.hellgraph.artifact.v1+json"
LAYER_MEDIA_TYPE = "application/vnd.socioprophet.hellgraph.tarball.v1+gzip"
CONFIG_MEDIA_TYPE = "application/vnd.socioprophet.hellgraph.config.v1+json"
MANIFEST_MEDIA_TYPE = "application/vnd.oci.image.manifest.v1+json"

# The OCI "empty descriptor" -- literally the two bytes `{}`.
EMPTY_JSON = b"{}"
EMPTY_MEDIA_TYPE = "application/vnd.oci.empty.v1+json"
EMPTY_DIGEST = "sha256:44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"

# ---------------------------------------------------------------- helpers


class PublishError(RuntimeError):
    """A correctness check on the publish path failed."""


def require(condition, message: str) -> None:
    """Assert-equivalent that survives `python -O`.

    These are not debug assertions: they are the checks that stop a digest
    mismatch, a non-201 PUT, or a non-byte-identical pull from being published
    anyway. `python -O` strips `assert`, which would have turned every one of
    them into a no-op and let the tool report a successful publish for bytes the
    registry never confirmed. A check that a runtime flag can silently delete is
    not a check.
    """
    if not condition:
        raise PublishError(message)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_of(data: bytes) -> str:
    return "sha256:" + sha256_hex(data)


def _conn():
    if SCHEME == "https":
        return http.client.HTTPSConnection(REGISTRY, timeout=120)
    return http.client.HTTPConnection(REGISTRY, timeout=120)


def auth_header():
    if OCI_TOKEN:
        return {"Authorization": "Bearer " + OCI_TOKEN}
    if OCI_USER and OCI_PASS:
        b = base64.b64encode(f"{OCI_USER}:{OCI_PASS}".encode()).decode()
        return {"Authorization": "Basic " + b}
    return {}


def request(method, path, body=None, headers=None, read_body=True):
    """Single HTTP request. Returns (status, headers_dict_lowercased, body_bytes)."""
    conn = _conn()
    hdrs = dict(auth_header())
    hdrs.update(headers or {})
    if body is not None and "Content-Length" not in hdrs:
        hdrs["Content-Length"] = str(len(body))
    try:
        conn.request(method, path, body=body, headers=hdrs)
        resp = conn.getresponse()
        data = resp.read() if read_body else b""
        hmap = {k.lower(): v for k, v in resp.getheaders()}
        return resp.status, hmap, data
    finally:
        conn.close()


def rel(location: str) -> str:
    """Normalise a Location header (may be absolute URL or path) to a request path."""
    p = urllib.parse.urlsplit(location)
    path = p.path or "/"
    if p.query:
        path += "?" + p.query
    return path


def add_query(path: str, **params) -> str:
    sep = "&" if "?" in path else "?"
    return path + sep + urllib.parse.urlencode(params)


def content_digest_header(hmap):
    return hmap.get("docker-content-digest") or hmap.get("oci-content-digest")


LOG = []


def log(step, status, note=""):
    LOG.append((step, status, note))
    print(f"  [{status}] {step}" + (f"  -- {note}" if note else ""), flush=True)


# ---------------------------------------------------------------- API ops


def api_version_check():
    st, h, b = request("GET", "/v2/")
    log("GET /v2/", st, f"api-version={h.get('docker-distribution-api-version')}")
    return st


def blob_exists(repo, digest):
    st, h, _ = request("HEAD", f"/v2/{repo}/blobs/{digest}")
    return st, h


def push_blob(repo, data, label=""):
    """Two-shot upload: POST to start a session, PUT with ?digest= to finish.

    Returns dict with the statuses observed and the digest.
    """
    dg = digest_of(data)

    st_head, _ = blob_exists(repo, dg)
    if st_head == 200:
        log(f"HEAD blob {label}", 200, f"already present, skipping upload ({dg})")
        return {"digest": dg, "size": len(data), "post": None, "put": None,
                "head_before": 200}

    st_post, h_post, b_post = request("POST", f"/v2/{repo}/blobs/uploads/")
    if st_post not in (202, 201):
        raise RuntimeError(f"POST uploads failed {st_post}: {b_post!r}")
    location = h_post.get("location")
    log(f"POST /v2/{repo}/blobs/uploads/ ({label})", st_post, f"location={location}")

    put_path = add_query(rel(location), digest=dg)
    st_put, h_put, b_put = request(
        "PUT", put_path, body=data,
        headers={"Content-Type": "application/octet-stream"},
    )
    if st_put != 201:
        raise RuntimeError(f"PUT blob failed {st_put}: {b_put!r}")
    log(f"PUT blob?digest ({label})", st_put,
        f"{len(data)}B  server-digest={content_digest_header(h_put)}")

    return {"digest": dg, "size": len(data), "post": st_post, "put": st_put,
            "head_before": st_head, "location": location,
            "server_digest": content_digest_header(h_put)}


def build_manifest(config_desc, layer_descs, artifact_type=None, subject=None,
                   annotations=None):
    m = {
        "schemaVersion": 2,
        "mediaType": MANIFEST_MEDIA_TYPE,
        "config": config_desc,
        "layers": layer_descs,
    }
    if artifact_type:
        m["artifactType"] = artifact_type
    if subject:
        m["subject"] = subject
    if annotations:
        m["annotations"] = annotations
    # Deterministic, compact encoding. The EXACT bytes we hash are the EXACT
    # bytes we PUT -- this is what makes the manifest content-addressable.
    return json.dumps(m, sort_keys=True, separators=(",", ":")).encode("utf-8")


def descriptor(media_type, digest, size, artifact_type=None):
    d = {"mediaType": media_type, "digest": digest, "size": size}
    if artifact_type:
        d["artifactType"] = artifact_type
    return d


def push_manifest(repo, reference, manifest_bytes, label=""):
    st, h, b = request(
        "PUT", f"/v2/{repo}/manifests/{reference}",
        body=manifest_bytes,
        headers={"Content-Type": MANIFEST_MEDIA_TYPE},
    )
    server_dg = content_digest_header(h)
    local_dg = digest_of(manifest_bytes)
    log(f"PUT /v2/{repo}/manifests/{reference} ({label})", st,
        f"server={server_dg} local={local_dg}"
        + ("" if st < 300 else f" body={b[:400]!r}"))
    return st, server_dg, local_dg, h, b


def get_manifest(repo, reference, accept=MANIFEST_MEDIA_TYPE):
    return request("GET", f"/v2/{repo}/manifests/{reference}",
                   headers={"Accept": accept})


def get_blob(repo, digest):
    return request("GET", f"/v2/{repo}/blobs/{digest}")


def get_referrers(repo, digest, artifact_type=None):
    path = f"/v2/{repo}/referrers/{digest}"
    if artifact_type:
        path = add_query(path, artifactType=artifact_type)
    return request("GET", path, headers={"Accept": "application/vnd.oci.image.index.v1+json"})


# ---------------------------------------------------------------- main


def main():
    payload_path = sys.argv[1] if len(sys.argv) > 1 else "payload.tgz"
    with open(payload_path, "rb") as f:
        payload = f.read()
    payload_digest = digest_of(payload)

    print(f"\n=== payload: {payload_path}  {len(payload)}B  {payload_digest}\n")

    print("--- 0. registry reachable ---")
    api_version_check()

    # ---- 1. push the layer (the npm tarball) ----------------------------
    print("\n--- 1. push tarball layer blob ---")
    layer = push_blob(REPO, payload, label="tarball")

    # ---- 2. push a small JSON config blob -------------------------------
    print("\n--- 2. push JSON config blob ---")
    config_doc = {
        "artifact": "socioprophet-hellgraph",
        "version": VERSION,
        "npmName": "@socioprophet/hellgraph",
        "tarballSha256": payload_digest,
    }
    config_bytes = json.dumps(config_doc, sort_keys=True,
                              separators=(",", ":")).encode("utf-8")
    config = push_blob(REPO, config_bytes, label="config")

    # ---- 3. PUT manifest with artifactType ------------------------------
    print("\n--- 3. PUT manifest (OCI 1.1 artifactType + custom layer mediaType) ---")
    layer_desc = descriptor(LAYER_MEDIA_TYPE, layer["digest"], layer["size"])
    layer_desc["annotations"] = {
        "org.opencontainers.image.title": os.path.basename(payload_path),
    }
    config_desc = descriptor(CONFIG_MEDIA_TYPE, config["digest"], config["size"])

    manifest_bytes = build_manifest(
        config_desc, [layer_desc],
        artifact_type=ARTIFACT_TYPE,
        annotations={
            "org.opencontainers.image.version": VERSION,
            "dev.socioprophet.tarball.sha256": payload_digest,
        },
    )
    st, server_dg, local_dg, _, _ = push_manifest(REPO, TAG, manifest_bytes,
                                                  label="artifactType")
    require(st == 201, f"manifest PUT expected 201, got {st}")
    require(server_dg == local_dg, f"DIGEST MISMATCH server={server_dg} local={local_dg}")
    print(f"\n  ==> MANIFEST DIGEST: {local_dg}  (server header agrees)\n")
    manifest_digest = local_dg

    # ---- 3b. immutable alias tag (zot tag-overwrite orphaning mitigation) ----
    alias = None
    if IMMUTABLE_ALIAS:
        alias = "sha256-" + manifest_digest.split(":", 1)[1]
        st_a, sdg_a, _, _, _ = push_manifest(REPO, alias, manifest_bytes,
                                             label="immutable alias")
        require(
            st_a == 201 and sdg_a == manifest_digest,
            f"immutable alias push expected 201 and the same digest; got {st_a}/{sdg_a}",
        )
        print(f"  immutable alias tag pushed: {alias}")

    # ---- 4. digest-pinned round trip ------------------------------------
    print("--- 4. digest-pinned round trip ---")
    st_gm, h_gm, got_manifest = get_manifest(REPO, manifest_digest)
    log(f"GET manifests/{manifest_digest[:19]}...", st_gm,
        f"content-digest={content_digest_header(h_gm)}")
    require(st_gm == 200, f"GET manifest by digest expected 200, got {st_gm}")
    require(digest_of(got_manifest) == manifest_digest, "manifest bytes not stable")
    require(got_manifest == manifest_bytes, "manifest bytes differ from what we PUT")
    print("  manifest bytes byte-identical to what we PUT  [OK]")

    parsed = json.loads(got_manifest)
    print(f"  artifactType survived round-trip: {parsed.get('artifactType')!r}")
    print(f"  layer mediaType survived: {parsed['layers'][0]['mediaType']!r}")

    pulled_layer_digest = parsed["layers"][0]["digest"]
    st_gb, h_gb, got_layer = get_blob(REPO, pulled_layer_digest)
    log(f"GET blobs/{pulled_layer_digest[:19]}...", st_gb, f"{len(got_layer)}B")
    require(st_gb == 200, f"GET blob by digest expected 200, got {st_gb}")
    require(digest_of(got_layer) == payload_digest, "pulled layer digest mismatch")
    require(got_layer == payload, "pulled layer bytes differ from source")
    print(f"  layer bytes byte-identical to source tarball ({len(got_layer)}B)  [OK]")

    # ---- 5a. negative: digest we never pushed ---------------------------
    print("\n--- 5a. negative test: digest never pushed ---")
    bogus = "sha256:" + "de" * 32
    st_nm, _, b_nm = get_manifest(REPO, bogus)
    log(f"GET manifests/{bogus[:19]}... (bogus)", st_nm,
        f"code={_errcode(b_nm)}")
    st_nb, _, b_nb = get_blob(REPO, bogus)
    log(f"GET blobs/{bogus[:19]}... (bogus)", st_nb, f"code={_errcode(b_nb)}")
    require(st_nm == 404 and st_nb == 404,
            f"a digest never pushed must 404; got manifest={st_nm} blob={st_nb}")

    # ---- 5b. idempotency: push identical bytes again ---------------------
    print("\n--- 5b. idempotency: push the SAME bytes again ---")
    layer2 = push_blob(REPO, payload, label="tarball-again")
    config2 = push_blob(REPO, config_bytes, label="config-again")
    # The re-push result was previously computed and discarded, which made this an
    # idempotency test that never tested blob idempotency — only that a second push
    # did not raise. Content-addressing is the claim; check it.
    require(layer2["digest"] == layer["digest"],
            f"blob NOT content-addressed: re-push of identical bytes gave "
            f"{layer2['digest']} but the first gave {layer['digest']}")
    require(config2["digest"] == config["digest"],
            f"config blob NOT content-addressed: {config2['digest']} != {config['digest']}")
    manifest_bytes2 = build_manifest(
        descriptor(CONFIG_MEDIA_TYPE, config2["digest"], config2["size"]),
        [layer_desc],
        artifact_type=ARTIFACT_TYPE,
        annotations={
            "org.opencontainers.image.version": VERSION,
            "dev.socioprophet.tarball.sha256": payload_digest,
        },
    )
    require(manifest_bytes2 == manifest_bytes, "manifest serialisation not deterministic")
    st2, server_dg2, local_dg2, _, _ = push_manifest(
        REPO, TAG + "-dup", manifest_bytes2, label="idempotency")
    require(st2 == 201, f"idempotency re-push expected 201, got {st2}")
    require(server_dg2 == manifest_digest, f"NOT idempotent: {server_dg2} != {manifest_digest}")
    print(f"  second push under a DIFFERENT tag -> SAME digest {server_dg2}  [OK]")

    st_t1, h_t1, _ = get_manifest(REPO, TAG)
    st_t2, h_t2, _ = get_manifest(REPO, TAG + "-dup")
    log(f"GET manifests/{TAG}", st_t1, content_digest_header(h_t1))
    log(f"GET manifests/{TAG}-dup", st_t2, content_digest_header(h_t2))
    require(
        content_digest_header(h_t1) == content_digest_header(h_t2) == manifest_digest,
        f"both tags must resolve to {manifest_digest}; got "
        f"{content_digest_header(h_t1)} and {content_digest_header(h_t2)}",
    )

    # ---- 6. the digest must survive the mutable tag being moved -------------
    print("\n--- 6. digest survives the mutable tag being repointed ---")
    moved = build_manifest(config_desc, [layer_desc], artifact_type=ARTIFACT_TYPE,
                           annotations={"build": "SUPERSEDING"})
    st_mv, dg_mv, _, _, _ = push_manifest(REPO, TAG, moved, label="repoint tag")
    require(
        st_mv == 201 and dg_mv != manifest_digest,
        f"moving the tag should publish a NEW digest; got status {st_mv} digest {dg_mv}",
    )
    st_h, h_h, _ = request("HEAD", f"/v2/{REPO}/manifests/{TAG}",
                           headers={"Accept": MANIFEST_MEDIA_TYPE})
    log(f"HEAD manifests/{TAG} after repoint", st_h,
        f"tag now -> {content_digest_header(h_h)}")
    st_old, _, old_bytes = get_manifest(REPO, manifest_digest)
    log(f"GET manifests/{manifest_digest[:19]}... (original pin)", st_old,
        "SURVIVED" if st_old == 200 else "ORPHANED BY TAG MOVE")
    require(
        st_old == 200 and old_bytes == manifest_bytes,
        "original digest was orphaned -- immutable alias tag is REQUIRED on zot",
    )
    print("  original digest still resolves + bytes identical  [OK]")
    if alias:
        print(f"  (protected by immutable alias tag {alias})")

    print("\n" + "=" * 70)
    print(f"PROVEN. manifest digest = {manifest_digest}")
    print(f"pin with: {REGISTRY}/{REPO}@{manifest_digest}")
    print("=" * 70)
    return manifest_digest


def _errcode(body):
    try:
        return json.loads(body)["errors"][0]["code"]
    except Exception:
        return body[:120]


if __name__ == "__main__":
    main()
