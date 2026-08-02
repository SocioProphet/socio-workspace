"""The vendored kernel is pinned and tamper-evident — with teeth.

Vendoring without a pin check is just a stale copy waiting to lie. This asserts:

  1. Every file recorded in VENDOR.json exists and hashes to the recorded sha256
     (no silent local edit, no drift from the pinned source_commit).
  2. Every .py under the vendored tree is accounted for in VENDOR.json
     (no un-manifested file smuggled in).
  3. The manifest's spec_version equals the kernel's own SPEC_VERSION at runtime
     (the consumer and the pin agree on which contract is in force).

If the upstream kernel advances, this fails until someone re-vendors and re-pins
deliberately — which is the point: the bump is a reviewed act, not a silent slide.
"""

import hashlib
import json
import os

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_VENDOR_DIR = os.path.join(os.path.dirname(_HERE), "third_party", "procyber")
_SEMANTIC_DIR = os.path.join(_VENDOR_DIR, "semantic")
_MANIFEST = os.path.join(_VENDOR_DIR, "VENDOR.json")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def _load_manifest():
    with open(_MANIFEST, "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_manifest_exists_and_is_well_formed():
    m = _load_manifest()
    assert m["source_repo"] and m["source_commit"] and m["spec_version"]
    assert isinstance(m["files"], dict) and m["files"]


def test_every_pinned_file_matches_its_hash():
    m = _load_manifest()
    for name, expected in m["files"].items():
        path = os.path.join(_SEMANTIC_DIR, name)
        assert os.path.exists(path), f"pinned file missing from vendor tree: {name}"
        actual = _sha256(path)
        assert actual == expected, (
            f"vendored {name} drifted from pin:\n  expected {expected}\n  actual   {actual}\n"
            f"re-vendor from {m['source_repo']}@{m['source_commit']} and update VENDOR.json"
        )


def test_no_unmanifested_python_files():
    m = _load_manifest()
    on_disk = {f for f in os.listdir(_SEMANTIC_DIR) if f.endswith(".py")}
    manifested = set(m["files"])
    unaccounted = on_disk - manifested
    assert not unaccounted, f"vendored .py files not in VENDOR.json: {sorted(unaccounted)}"


def test_manifest_spec_matches_runtime_kernel():
    from procyber.semantic import SPEC_VERSION
    m = _load_manifest()
    assert m["spec_version"] == SPEC_VERSION, (
        f"pin says {m['spec_version']} but imported kernel is {SPEC_VERSION}"
    )
