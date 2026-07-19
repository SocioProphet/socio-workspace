from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from .result_output_cli import cmd_show_result_output


class ResultOutputCliSmokeTest(unittest.TestCase):
    def test_unified_output_cli(self) -> None:
        cases = [
            argparse.Namespace(
                output_mode="preview",
                kind="stale_mirror",
                root=None,
                title="Fabric Result Preview",
                stale_generation_gap=3,
                policy_allow_stale=True,
                signed_tombstone=False,
                local_dirty=False,
                authority_mode="local_first",
                current_authority="local",
                requested_authority="remote",
                quorum_granted=False,
            ),
            argparse.Namespace(
                output_mode="html",
                kind="tombstone",
                root=None,
                title="Fabric Result Preview",
                stale_generation_gap=3,
                policy_allow_stale=False,
                signed_tombstone=True,
                local_dirty=False,
                authority_mode="provider_first",
                current_authority="local",
                requested_authority="remote",
                quorum_granted=False,
            ),
            argparse.Namespace(
                output_mode="page",
                kind="authority_transition",
                root=None,
                title="Fabric Result Preview",
                stale_generation_gap=3,
                policy_allow_stale=False,
                signed_tombstone=False,
                local_dirty=False,
                authority_mode="local_first",
                current_authority="local",
                requested_authority="remote",
                quorum_granted=True,
            ),
            argparse.Namespace(
                output_mode="page",
                kind="reconcile_matrix",
                root=None,
                title="Fabric Result Preview",
                stale_generation_gap=3,
                policy_allow_stale=True,
                signed_tombstone=True,
                local_dirty=False,
                authority_mode="provider_first",
                current_authority="local",
                requested_authority="remote",
                quorum_granted=True,
            ),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            for idx, ns in enumerate(cases):
                ns.root = str(Path(tmpdir) / f"case-{idx}")
                rc = cmd_show_result_output(ns)
                self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
