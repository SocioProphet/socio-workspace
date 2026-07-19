from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from .cli import (
    cmd_run_authority_flow,
    cmd_run_harness,
    cmd_run_stale_mirror_flow,
    cmd_run_tombstone_flow,
)


class CliSurfaceSmokeTest(unittest.TestCase):
    def test_cli_surface_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cases = [
                ("drive", cmd_run_harness, argparse.Namespace(connector="drive", root=str(Path(tmpdir) / "drive"))),
                ("s3", cmd_run_harness, argparse.Namespace(connector="s3", root=str(Path(tmpdir) / "s3"))),
                ("hyper", cmd_run_harness, argparse.Namespace(connector="hyper", root=str(Path(tmpdir) / "hyper"))),
                (
                    "tombstone",
                    cmd_run_tombstone_flow,
                    argparse.Namespace(
                        root=str(Path(tmpdir) / "tombstone"),
                        signed_tombstone=True,
                        local_dirty=False,
                        authority_mode="provider_first",
                    ),
                ),
                (
                    "authority",
                    cmd_run_authority_flow,
                    argparse.Namespace(
                        root=str(Path(tmpdir) / "authority"),
                        current_authority="local",
                        requested_authority="remote",
                        quorum_granted=True,
                    ),
                ),
                (
                    "stale_mirror",
                    cmd_run_stale_mirror_flow,
                    argparse.Namespace(
                        root=str(Path(tmpdir) / "stale"),
                        stale_generation_gap=3,
                        policy_allow_stale=False,
                        authority_mode="local_first",
                    ),
                ),
            ]
            for _, fn, ns in cases:
                rc = fn(ns)
                self.assertEqual(rc, 0)
                self.assertTrue((Path(ns.root) / "events.ndjson").exists())


if __name__ == "__main__":
    unittest.main()
