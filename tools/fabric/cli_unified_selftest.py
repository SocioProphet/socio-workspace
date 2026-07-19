from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from .cli_unified import cmd_show_result_output, cmd_show_result_interface, cmd_show_result_plan, cmd_show_result_view


class UnifiedCliSmokeTest(unittest.TestCase):
    def test_unified_surface_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = str(Path(tmpdir) / "case")
            plan_ns = argparse.Namespace(
                kind="stale_mirror",
                root=root,
                stale_generation_gap=3,
                policy_allow_stale=True,
                signed_tombstone=False,
                local_dirty=False,
                authority_mode="local_first",
                current_authority="local",
                requested_authority="remote",
                quorum_granted=False,
            )
            interface_ns = argparse.Namespace(
                kind="tombstone",
                root=root,
                stale_generation_gap=3,
                policy_allow_stale=False,
                signed_tombstone=True,
                local_dirty=False,
                authority_mode="provider_first",
                current_authority="local",
                requested_authority="remote",
                quorum_granted=False,
            )
            view_ns = argparse.Namespace(
                kind="authority_transition",
                root=root,
                stale_generation_gap=3,
                policy_allow_stale=False,
                signed_tombstone=False,
                local_dirty=False,
                authority_mode="local_first",
                current_authority="local",
                requested_authority="remote",
                quorum_granted=True,
            )
            output_ns = argparse.Namespace(
                output_mode="page",
                kind="reconcile_matrix",
                root=root,
                title="Fabric Result Preview",
                stale_generation_gap=3,
                policy_allow_stale=True,
                signed_tombstone=True,
                local_dirty=False,
                authority_mode="provider_first",
                current_authority="local",
                requested_authority="remote",
                quorum_granted=True,
            )
            self.assertEqual(cmd_show_result_plan(plan_ns), 0)
            self.assertEqual(cmd_show_result_interface(interface_ns), 0)
            self.assertEqual(cmd_show_result_view(view_ns), 0)
            self.assertEqual(cmd_show_result_output(output_ns), 0)


if __name__ == "__main__":
    unittest.main()
