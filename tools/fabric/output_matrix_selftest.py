from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from .planner_surface import planner_outcome_from_runtime_surface, planner_outcomes_from_runtime_surface_matrix
from .reconcile_flow_harness import run_authority_transition_flow, run_tombstone_propagation_flow
from .reconcile_matrix_harness import run_reconcile_matrix
from .result_card import card_from_view, cards_from_view_matrix
from .result_html import html_from_preview, html_from_preview_matrix
from .result_html_cli import cmd_show_result_html
from .result_interface import interface_from_serving_decision, interfaces_from_serving_matrix
from .result_page import page_from_preview, page_from_preview_matrix
from .result_page_cli import cmd_show_result_page
from .result_plan import serving_decision_from_planner_outcome, serving_decisions_from_planner_matrix
from .result_preview import preview_from_card, previews_from_card_matrix
from .result_preview_cli import cmd_show_result_preview
from .result_render import render_block_from_interface, render_blocks_from_interface_matrix
from .result_surface import outcome_from_flow_result, outcomes_from_reconcile_matrix
from .result_view import view_from_render_block, views_from_render_matrix
from .stale_mirror_flow_harness import run_stale_mirror_flow


class OutputMatrixSmokeTest(unittest.TestCase):
    def test_direct_preview_html_and_page_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            stale = run_stale_mirror_flow(
                Path(tmpdir) / "stale",
                stale_generation_gap=3,
                policy_allow_stale=True,
                authority_mode="local_first",
            )
            tombstone = run_tombstone_propagation_flow(
                Path(tmpdir) / "tombstone",
                signed_tombstone=True,
                local_dirty=False,
                authority_mode="provider_first",
            )
            authority = run_authority_transition_flow(
                Path(tmpdir) / "authority",
                current_authority="local",
                requested_authority="remote",
                quorum_granted=True,
            )

            def build_preview(flow_name: str, flow: dict):
                planner = planner_outcome_from_runtime_surface(outcome_from_flow_result(flow_name, flow))
                decision = serving_decision_from_planner_outcome(planner)
                interface = interface_from_serving_decision(decision)
                block = render_block_from_interface(interface)
                view = view_from_render_block(block)
                card = card_from_view(view)
                return preview_from_card(card)

            stale_preview = build_preview("stale_mirror", stale)
            tombstone_preview = build_preview("tombstone", tombstone)
            authority_preview = build_preview("authority_transition", authority)

            stale_html = html_from_preview(stale_preview)
            tombstone_html = html_from_preview(tombstone_preview)
            authority_html = html_from_preview(authority_preview)
            stale_page = page_from_preview("Fabric Result Preview", stale_preview)
            tombstone_page = page_from_preview("Fabric Result Preview", tombstone_preview)
            authority_page = page_from_preview("Fabric Result Preview", authority_preview)

            self.assertEqual(stale_preview.layout, "metadata_panel")
            self.assertEqual(tombstone_preview.layout, "inline_alert")
            self.assertEqual(authority_preview.visual_tone, "info")
            self.assertIn("metadata_panel", stale_html)
            self.assertIn("inline_alert", tombstone_html)
            self.assertIn("tone-info", authority_html)
            self.assertIn("<!doctype html>", stale_page)
            self.assertIn("metadata_panel", stale_page)
            self.assertIn("inline_alert", tombstone_page)
            self.assertIn("tone-info", authority_page)

    def test_matrix_preview_html_and_page_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            matrix = run_reconcile_matrix(Path(tmpdir))
            planners = planner_outcomes_from_runtime_surface_matrix(outcomes_from_reconcile_matrix(matrix))
            decisions = serving_decisions_from_planner_matrix(planners)
            interfaces = interfaces_from_serving_matrix(decisions)
            renders = render_blocks_from_interface_matrix(interfaces)
            views = views_from_render_matrix(renders)
            cards = cards_from_view_matrix(views)
            previews = previews_from_card_matrix(cards)
            html = html_from_preview_matrix(previews)
            page = page_from_preview_matrix("Fabric Result Preview", previews)
            self.assertEqual(previews["stale_mirror"]["layout"], "metadata_panel")
            self.assertEqual(previews["tombstone"]["layout"], "inline_alert")
            self.assertEqual(previews["authority_transition"]["visual_tone"], "info")
            self.assertIn("result-preview-grid", html)
            self.assertIn("metadata_panel", html)
            self.assertIn("inline_alert", html)
            self.assertIn("<!doctype html>", page)
            self.assertIn("result-preview-grid", page)

    def test_preview_html_and_page_cli_matrix(self) -> None:
        cases = [
            argparse.Namespace(
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
                self.assertEqual(cmd_show_result_preview(ns), 0)
                self.assertEqual(cmd_show_result_html(ns), 0)
                self.assertEqual(cmd_show_result_page(ns), 0)


if __name__ == "__main__":
    unittest.main()
