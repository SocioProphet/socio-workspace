"""Coverage for tools/svf_runner.py utc_now() reproducible-fixture support.

utc_now() honours SVF_SOURCE_DATE_EPOCH so `make validate` regenerates the
committed artifacts/svf fixtures byte-for-byte and CI can gate on a clean tree.
That determinism -- and its fail-loud behaviour on a bad epoch -- is exactly
what the gate relies on, so the three paths are pinned here rather than left to
the smoke run to exercise implicitly.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

RUNNER = Path(__file__).resolve().parents[1] / "tools" / "svf_runner.py"
# ISO-8601 UTC, second precision, Z suffix -- the exact shape the fixtures and
# the receipt schema expect (no microseconds, no +00:00 offset).
ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _load_svf_runner():
    spec = importlib.util.spec_from_file_location("svf_runner_under_test", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


svf_runner = _load_svf_runner()


def test_frozen_epoch_pins_timestamp(monkeypatch):
    # 1781006026 == 2026-06-09T11:53:46Z, the pinned instant the Makefile uses.
    monkeypatch.setenv("SVF_SOURCE_DATE_EPOCH", "1781006026")
    assert svf_runner.utc_now() == "2026-06-09T11:53:46Z"


def test_unset_uses_wall_clock_with_correct_shape(monkeypatch):
    monkeypatch.delenv("SVF_SOURCE_DATE_EPOCH", raising=False)
    now = svf_runner.utc_now()
    # Real runs keep wall-clock time; assert the format (not a value) so the
    # test does not drift, and confirm microseconds are dropped and Z is used.
    assert ISO_Z.match(now), now


def test_invalid_epoch_raises_naming_the_variable(monkeypatch):
    monkeypatch.setenv("SVF_SOURCE_DATE_EPOCH", "not-an-int")
    # Must fail loudly and name the variable rather than emit an opaque int()
    # error -- a poisoned epoch must never silently reach the artifacts.
    with pytest.raises(ValueError, match="SVF_SOURCE_DATE_EPOCH"):
        svf_runner.utc_now()
