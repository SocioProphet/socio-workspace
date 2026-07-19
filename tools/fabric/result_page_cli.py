from __future__ import annotations

import argparse
from pathlib import Path

from .planner_surface import planner_outcome_from_runtime_surface, planner_outcomes_from_runtime_surface_matrix
from .reconcile_flow_harness import run_authority_transition_flow, run_tombstone_propagation_flow
from .reconcile_matrix_harness import run_reconcile_matrix
from .result_card import card_from_view, cards_from_view_matrix
from .result_interface import interface_from_serving_decision, interfaces_from_serving_matrix
from .result_page import page_from_preview, page_from_preview_matrix
from .result_plan import serving_decision_from_planner_outcome, serving_decisions_from_planner_matrix
from .result_preview import preview_from_card, previews_from_card_matrix
from .result_render import render_block_from_interface, render_blocks_from_interface_matrix
from .result_surface import outcome_from_flow_result, outcomes_from_reconcile_matrix
from .result_view import view_from_render_block, views_from_render_matrix
from .stale_mirror_flow_harness import run_stale_mirror_flow


def cmd_show_result_page(args: argparse.Namespace) -> int:
    root = Path(args.root)
    title = args.title
    if args.kind == "stale_mirror":
        flow = run_stale_mirror_flow(
            root,
            stale_generation_gap=args.stale_generation_gap,
            policy_allow_stale=args.policy_allow_stale,
            authority_mode=args.authority_mode,
        )
        preview = preview_from_card(
            card_from_view(
                view_from_render_block(
                    render_block_from_interface(
                        interface_from_serving_decision(
                            serving_decision_from_planner_outcome(
                                planner_outcome_from_runtime_surface(outcome_from_flow_result("stale_mirror", flow))
                            )
                        )
                    )
                )
            )
        )
        print(page_from_preview(title, preview))
        return 0
    if args.kind == "tombstone":
        flow = run_tombstone_propagation_flow(
            root,
            signed_tombstone=args.signed_tombstone,
            local_dirty=args.local_dirty,
            authority_mode=args.authority_mode,
        )
        preview = preview_from_card(
            card_from_view(
                view_from_render_block(
                    render_block_from_interface(
                        interface_from_serving_decision(
                            serving_decision_from_planner_outcome(
                                planner_outcome_from_runtime_surface(outcome_from_flow_result("tombstone", flow))
                            )
                        )
                    )
                )
            )
        )
        print(page_from_preview(title, preview))
        return 0
    if args.kind == "authority_transition":
        flow = run_authority_transition_flow(
            root,
            current_authority=args.current_authority,
            requested_authority=args.requested_authority,
            quorum_granted=args.quorum_granted,
        )
        preview = preview_from_card(
            card_from_view(
                view_from_render_block(
                    render_block_from_interface(
                        interface_from_serving_decision(
                            serving_decision_from_planner_outcome(
                                planner_outcome_from_runtime_surface(outcome_from_flow_result("authority_transition", flow))
                            )
                        )
                    )
                )
            )
        )
        print(page_from_preview(title, preview))
        return 0
    if args.kind == "reconcile_matrix":
        matrix = run_reconcile_matrix(root)
        surfaces = outcomes_from_reconcile_matrix(matrix)
        planners = planner_outcomes_from_runtime_surface_matrix(surfaces)
        decisions = serving_decisions_from_planner_matrix(planners)
        interfaces = interfaces_from_serving_matrix(decisions)
        renders = render_blocks_from_interface_matrix(interfaces)
        views = views_from_render_matrix(renders)
        cards = cards_from_view_matrix(views)
        previews = previews_from_card_matrix(cards)
        print(page_from_preview_matrix(title, previews))
        return 0
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fabric-page")
    parser.add_argument("kind", choices=["stale_mirror", "tombstone", "authority_transition", "reconcile_matrix"])
    parser.add_argument("--root", required=True)
    parser.add_argument("--title", default="Fabric Result Preview")
    parser.add_argument("--stale-generation-gap", type=int, default=3)
    parser.add_argument("--policy-allow-stale", action="store_true")
    parser.add_argument("--signed-tombstone", action="store_true")
    parser.add_argument("--local-dirty", action="store_true")
    parser.add_argument("--authority-mode", default="local_first", choices=["local_first", "provider_first", "hybrid"])
    parser.add_argument("--current-authority", default="local")
    parser.add_argument("--requested-authority", default="remote")
    parser.add_argument("--quorum-granted", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return cmd_show_result_page(args)


if __name__ == "__main__":
    raise SystemExit(main())
