from __future__ import annotations

import argparse
import json
from pathlib import Path

from .connectors.drive import DriveExecutor
from .connectors.hyper import HyperExecutor
from .connectors.s3 import S3Executor
from .events import EventSink
from .integration_common import run_mount_and_connector_flow
from .mount_agent import MountAgent, MountRequest
from .planner_surface import planner_outcome_from_runtime_surface, planner_outcomes_from_runtime_surface_matrix
from .reconcile_flow_harness import run_authority_transition_flow, run_tombstone_propagation_flow
from .reconcile_matrix_harness import run_reconcile_matrix
from .result_interface import interface_from_serving_decision, interfaces_from_serving_matrix
from .result_plan import serving_decision_from_planner_outcome, serving_decisions_from_planner_matrix
from .result_render import render_block_from_interface, render_blocks_from_interface_matrix
from .result_surface import outcome_from_flow_result, outcomes_from_reconcile_matrix
from .result_view import view_from_render_block, views_from_render_matrix
from .retrieval_registry import RetrievalRegistry
from .schema_refs import schema_paths
from .stale_mirror_flow_harness import run_stale_mirror_flow
from .validator import validate_file


def cmd_validate(args: argparse.Namespace) -> int:
    schemas = schema_paths()
    if args.schema not in schemas:
        print(json.dumps({"error": f"unknown schema {args.schema!r}", "known": sorted(schemas)}))
        return 2
    errors = validate_file(args.instance, schemas[args.schema])
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return 0 if not errors else 1


def cmd_register_demo(args: argparse.Namespace) -> int:
    registry = RetrievalRegistry()
    sink = EventSink(Path(args.events_file))
    agent = MountAgent(registry, sink)
    response = agent.register_mount(
        MountRequest(
            mount_name=args.mount_name,
            backend_type=args.backend_type,
            resolved_path_or_handle=args.path,
            node_ref=args.node_ref,
            rw_mode=args.rw_mode,
            capacity_bytes=args.capacity_bytes,
            workspace_ref=args.workspace_ref,
            dataset_ref=args.dataset_ref,
            pipeline_version=args.pipeline_version,
            policy_bundle_ref=args.policy_bundle_ref,
            principal=args.principal,
        )
    )
    print(json.dumps(response, default=lambda o: getattr(o, "__dict__", str(o)), indent=2))
    return 0


def cmd_run_harness(args: argparse.Namespace) -> int:
    mapping = {
        "drive": (DriveExecutor, "drive", "ds/demo", "demo", 1024),
        "s3": (S3Executor, "s3", "ds/demo-s3", "demo-s3", 2048),
        "hyper": (HyperExecutor, "hyper", "ds/demo-hyper", "demo-hyper", 4096),
    }
    executor_cls, connector_id, dataset_ref, mount_name, capacity_bytes = mapping[args.connector]
    result = run_mount_and_connector_flow(
        Path(args.root),
        executor_cls=executor_cls,
        connector_id=connector_id,
        dataset_ref=dataset_ref,
        mount_name=mount_name,
        capacity_bytes=capacity_bytes,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_run_tombstone_flow(args: argparse.Namespace) -> int:
    result = run_tombstone_propagation_flow(
        Path(args.root),
        signed_tombstone=args.signed_tombstone,
        local_dirty=args.local_dirty,
        authority_mode=args.authority_mode,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_run_authority_flow(args: argparse.Namespace) -> int:
    result = run_authority_transition_flow(
        Path(args.root),
        current_authority=args.current_authority,
        requested_authority=args.requested_authority,
        quorum_granted=args.quorum_granted,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_run_stale_mirror_flow(args: argparse.Namespace) -> int:
    result = run_stale_mirror_flow(
        Path(args.root),
        stale_generation_gap=args.stale_generation_gap,
        policy_allow_stale=args.policy_allow_stale,
        authority_mode=args.authority_mode,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_show_surface(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.kind == "stale_mirror":
        flow = run_stale_mirror_flow(
            root,
            stale_generation_gap=args.stale_generation_gap,
            policy_allow_stale=args.policy_allow_stale,
            authority_mode=args.authority_mode,
        )
        print(json.dumps(outcome_from_flow_result("stale_mirror", flow).to_dict(), indent=2))
        return 0
    if args.kind == "tombstone":
        flow = run_tombstone_propagation_flow(
            root,
            signed_tombstone=args.signed_tombstone,
            local_dirty=args.local_dirty,
            authority_mode=args.authority_mode,
        )
        print(json.dumps(outcome_from_flow_result("tombstone", flow).to_dict(), indent=2))
        return 0
    if args.kind == "authority_transition":
        flow = run_authority_transition_flow(
            root,
            current_authority=args.current_authority,
            requested_authority=args.requested_authority,
            quorum_granted=args.quorum_granted,
        )
        print(json.dumps(outcome_from_flow_result("authority_transition", flow).to_dict(), indent=2))
        return 0
    if args.kind == "reconcile_matrix":
        matrix = run_reconcile_matrix(root)
        print(json.dumps(outcomes_from_reconcile_matrix(matrix), indent=2))
        return 0
    print(json.dumps({"error": f"unknown surface kind {args.kind!r}"}))
    return 2


def cmd_show_planner_surface(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.kind == "stale_mirror":
        flow = run_stale_mirror_flow(
            root,
            stale_generation_gap=args.stale_generation_gap,
            policy_allow_stale=args.policy_allow_stale,
            authority_mode=args.authority_mode,
        )
        surface = outcome_from_flow_result("stale_mirror", flow)
        print(json.dumps(planner_outcome_from_runtime_surface(surface).to_dict(), indent=2))
        return 0
    if args.kind == "tombstone":
        flow = run_tombstone_propagation_flow(
            root,
            signed_tombstone=args.signed_tombstone,
            local_dirty=args.local_dirty,
            authority_mode=args.authority_mode,
        )
        surface = outcome_from_flow_result("tombstone", flow)
        print(json.dumps(planner_outcome_from_runtime_surface(surface).to_dict(), indent=2))
        return 0
    if args.kind == "authority_transition":
        flow = run_authority_transition_flow(
            root,
            current_authority=args.current_authority,
            requested_authority=args.requested_authority,
            quorum_granted=args.quorum_granted,
        )
        surface = outcome_from_flow_result("authority_transition", flow)
        print(json.dumps(planner_outcome_from_runtime_surface(surface).to_dict(), indent=2))
        return 0
    if args.kind == "reconcile_matrix":
        matrix = run_reconcile_matrix(root)
        surfaces = outcomes_from_reconcile_matrix(matrix)
        print(json.dumps(planner_outcomes_from_runtime_surface_matrix(surfaces), indent=2))
        return 0
    print(json.dumps({"error": f"unknown planner surface kind {args.kind!r}"}))
    return 2


def cmd_show_result_plan(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.kind == "stale_mirror":
        flow = run_stale_mirror_flow(
            root,
            stale_generation_gap=args.stale_generation_gap,
            policy_allow_stale=args.policy_allow_stale,
            authority_mode=args.authority_mode,
        )
        surface = outcome_from_flow_result("stale_mirror", flow)
        planner = planner_outcome_from_runtime_surface(surface)
        print(json.dumps(serving_decision_from_planner_outcome(planner).to_dict(), indent=2))
        return 0
    if args.kind == "tombstone":
        flow = run_tombstone_propagation_flow(
            root,
            signed_tombstone=args.signed_tombstone,
            local_dirty=args.local_dirty,
            authority_mode=args.authority_mode,
        )
        surface = outcome_from_flow_result("tombstone", flow)
        planner = planner_outcome_from_runtime_surface(surface)
        print(json.dumps(serving_decision_from_planner_outcome(planner).to_dict(), indent=2))
        return 0
    if args.kind == "authority_transition":
        flow = run_authority_transition_flow(
            root,
            current_authority=args.current_authority,
            requested_authority=args.requested_authority,
            quorum_granted=args.quorum_granted,
        )
        surface = outcome_from_flow_result("authority_transition", flow)
        planner = planner_outcome_from_runtime_surface(surface)
        print(json.dumps(serving_decision_from_planner_outcome(planner).to_dict(), indent=2))
        return 0
    if args.kind == "reconcile_matrix":
        matrix = run_reconcile_matrix(root)
        surfaces = outcomes_from_reconcile_matrix(matrix)
        planners = planner_outcomes_from_runtime_surface_matrix(surfaces)
        print(json.dumps(serving_decisions_from_planner_matrix(planners), indent=2))
        return 0
    print(json.dumps({"error": f"unknown result plan kind {args.kind!r}"}))
    return 2


def cmd_show_result_interface(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.kind == "stale_mirror":
        flow = run_stale_mirror_flow(
            root,
            stale_generation_gap=args.stale_generation_gap,
            policy_allow_stale=args.policy_allow_stale,
            authority_mode=args.authority_mode,
        )
        surface = outcome_from_flow_result("stale_mirror", flow)
        planner = planner_outcome_from_runtime_surface(surface)
        decision = serving_decision_from_planner_outcome(planner)
        print(json.dumps(interface_from_serving_decision(decision).to_dict(), indent=2))
        return 0
    if args.kind == "tombstone":
        flow = run_tombstone_propagation_flow(
            root,
            signed_tombstone=args.signed_tombstone,
            local_dirty=args.local_dirty,
            authority_mode=args.authority_mode,
        )
        surface = outcome_from_flow_result("tombstone", flow)
        planner = planner_outcome_from_runtime_surface(surface)
        decision = serving_decision_from_planner_outcome(planner)
        print(json.dumps(interface_from_serving_decision(decision).to_dict(), indent=2))
        return 0
    if args.kind == "authority_transition":
        flow = run_authority_transition_flow(
            root,
            current_authority=args.current_authority,
            requested_authority=args.requested_authority,
            quorum_granted=args.quorum_granted,
        )
        surface = outcome_from_flow_result("authority_transition", flow)
        planner = planner_outcome_from_runtime_surface(surface)
        decision = serving_decision_from_planner_outcome(planner)
        print(json.dumps(interface_from_serving_decision(decision).to_dict(), indent=2))
        return 0
    if args.kind == "reconcile_matrix":
        matrix = run_reconcile_matrix(root)
        surfaces = outcomes_from_reconcile_matrix(matrix)
        planners = planner_outcomes_from_runtime_surface_matrix(surfaces)
        decisions = serving_decisions_from_planner_matrix(planners)
        print(json.dumps(interfaces_from_serving_matrix(decisions), indent=2))
        return 0
    print(json.dumps({"error": f"unknown result interface kind {args.kind!r}"}))
    return 2


def cmd_show_result_view(args: argparse.Namespace) -> int:
    root = Path(args.root)
    if args.kind == "stale_mirror":
        flow = run_stale_mirror_flow(
            root,
            stale_generation_gap=args.stale_generation_gap,
            policy_allow_stale=args.policy_allow_stale,
            authority_mode=args.authority_mode,
        )
        surface = outcome_from_flow_result("stale_mirror", flow)
        planner = planner_outcome_from_runtime_surface(surface)
        decision = serving_decision_from_planner_outcome(planner)
        interface = interface_from_serving_decision(decision)
        block = render_block_from_interface(interface)
        print(json.dumps(view_from_render_block(block).to_dict(), indent=2))
        return 0
    if args.kind == "tombstone":
        flow = run_tombstone_propagation_flow(
            root,
            signed_tombstone=args.signed_tombstone,
            local_dirty=args.local_dirty,
            authority_mode=args.authority_mode,
        )
        surface = outcome_from_flow_result("tombstone", flow)
        planner = planner_outcome_from_runtime_surface(surface)
        decision = serving_decision_from_planner_outcome(planner)
        interface = interface_from_serving_decision(decision)
        block = render_block_from_interface(interface)
        print(json.dumps(view_from_render_block(block).to_dict(), indent=2))
        return 0
    if args.kind == "authority_transition":
        flow = run_authority_transition_flow(
            root,
            current_authority=args.current_authority,
            requested_authority=args.requested_authority,
            quorum_granted=args.quorum_granted,
        )
        surface = outcome_from_flow_result("authority_transition", flow)
        planner = planner_outcome_from_runtime_surface(surface)
        decision = serving_decision_from_planner_outcome(planner)
        interface = interface_from_serving_decision(decision)
        block = render_block_from_interface(interface)
        print(json.dumps(view_from_render_block(block).to_dict(), indent=2))
        return 0
    if args.kind == "reconcile_matrix":
        matrix = run_reconcile_matrix(root)
        surfaces = outcomes_from_reconcile_matrix(matrix)
        planners = planner_outcomes_from_runtime_surface_matrix(surfaces)
        decisions = serving_decisions_from_planner_matrix(planners)
        interfaces = interfaces_from_serving_matrix(decisions)
        blocks = render_blocks_from_interface_matrix(interfaces)
        print(json.dumps(views_from_render_matrix(blocks), indent=2))
        return 0
    print(json.dumps({"error": f"unknown result view kind {args.kind!r}"}))
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fabric")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-json")
    validate.add_argument("schema", help="schema key, e.g. manifest.v1")
    validate.add_argument("instance", help="path to JSON instance file")
    validate.set_defaults(func=cmd_validate)

    demo = sub.add_parser("register-demo")
    demo.add_argument("--mount-name", required=True)
    demo.add_argument("--backend-type", required=True)
    demo.add_argument("--path", required=True)
    demo.add_argument("--node-ref", default="node.local")
    demo.add_argument("--rw-mode", default="rw")
    demo.add_argument("--capacity-bytes", type=int, default=0)
    demo.add_argument("--workspace-ref", required=True)
    demo.add_argument("--dataset-ref", required=True)
    demo.add_argument("--pipeline-version", default="v1")
    demo.add_argument("--policy-bundle-ref", default="policy/default")
    demo.add_argument("--principal", default="operator")
    demo.add_argument("--events-file", default="/tmp/fabric-events.ndjson")
    demo.set_defaults(func=cmd_register_demo)

    harness = sub.add_parser("run-harness")
    harness.add_argument("connector", choices=["drive", "s3", "hyper"])
    harness.add_argument("--root", required=True)
    harness.set_defaults(func=cmd_run_harness)

    tombstone = sub.add_parser("run-tombstone-flow")
    tombstone.add_argument("--root", required=True)
    tombstone.add_argument("--signed-tombstone", action="store_true")
    tombstone.add_argument("--local-dirty", action="store_true")
    tombstone.add_argument("--authority-mode", default="local_first", choices=["local_first", "provider_first", "hybrid"])
    tombstone.set_defaults(func=cmd_run_tombstone_flow)

    authority = sub.add_parser("run-authority-flow")
    authority.add_argument("--root", required=True)
    authority.add_argument("--current-authority", required=True)
    authority.add_argument("--requested-authority", required=True)
    authority.add_argument("--quorum-granted", action="store_true")
    authority.set_defaults(func=cmd_run_authority_flow)

    stale = sub.add_parser("run-stale-mirror-flow")
    stale.add_argument("--root", required=True)
    stale.add_argument("--stale-generation-gap", type=int, required=True)
    stale.add_argument("--policy-allow-stale", action="store_true")
    stale.add_argument("--authority-mode", default="local_first", choices=["local_first", "provider_first", "hybrid"])
    stale.set_defaults(func=cmd_run_stale_mirror_flow)

    surface = sub.add_parser("show-surface")
    surface.add_argument("kind", choices=["stale_mirror", "tombstone", "authority_transition", "reconcile_matrix"])
    surface.add_argument("--root", required=True)
    surface.add_argument("--stale-generation-gap", type=int, default=3)
    surface.add_argument("--policy-allow-stale", action="store_true")
    surface.add_argument("--signed-tombstone", action="store_true")
    surface.add_argument("--local-dirty", action="store_true")
    surface.add_argument("--authority-mode", default="local_first", choices=["local_first", "provider_first", "hybrid"])
    surface.add_argument("--current-authority", default="local")
    surface.add_argument("--requested-authority", default="remote")
    surface.add_argument("--quorum-granted", action="store_true")
    surface.set_defaults(func=cmd_show_surface)

    planner = sub.add_parser("show-planner-surface")
    planner.add_argument("kind", choices=["stale_mirror", "tombstone", "authority_transition", "reconcile_matrix"])
    planner.add_argument("--root", required=True)
    planner.add_argument("--stale-generation-gap", type=int, default=3)
    planner.add_argument("--policy-allow-stale", action="store_true")
    planner.add_argument("--signed-tombstone", action="store_true")
    planner.add_argument("--local-dirty", action="store_true")
    planner.add_argument("--authority-mode", default="local_first", choices=["local_first", "provider_first", "hybrid"])
    planner.add_argument("--current-authority", default="local")
    planner.add_argument("--requested-authority", default="remote")
    planner.add_argument("--quorum-granted", action="store_true")
    planner.set_defaults(func=cmd_show_planner_surface)

    result_plan = sub.add_parser("show-result-plan")
    result_plan.add_argument("kind", choices=["stale_mirror", "tombstone", "authority_transition", "reconcile_matrix"])
    result_plan.add_argument("--root", required=True)
    result_plan.add_argument("--stale-generation-gap", type=int, default=3)
    result_plan.add_argument("--policy-allow-stale", action="store_true")
    result_plan.add_argument("--signed-tombstone", action="store_true")
    result_plan.add_argument("--local-dirty", action="store_true")
    result_plan.add_argument("--authority-mode", default="local_first", choices=["local_first", "provider_first", "hybrid"])
    result_plan.add_argument("--current-authority", default="local")
    result_plan.add_argument("--requested-authority", default="remote")
    result_plan.add_argument("--quorum-granted", action="store_true")
    result_plan.set_defaults(func=cmd_show_result_plan)

    result_interface = sub.add_parser("show-result-interface")
    result_interface.add_argument("kind", choices=["stale_mirror", "tombstone", "authority_transition", "reconcile_matrix"])
    result_interface.add_argument("--root", required=True)
    result_interface.add_argument("--stale-generation-gap", type=int, default=3)
    result_interface.add_argument("--policy-allow-stale", action="store_true")
    result_interface.add_argument("--signed-tombstone", action="store_true")
    result_interface.add_argument("--local-dirty", action="store_true")
    result_interface.add_argument("--authority-mode", default="local_first", choices=["local_first", "provider_first", "hybrid"])
    result_interface.add_argument("--current-authority", default="local")
    result_interface.add_argument("--requested-authority", default="remote")
    result_interface.add_argument("--quorum-granted", action="store_true")
    result_interface.set_defaults(func=cmd_show_result_interface)

    result_view = sub.add_parser("show-result-view")
    result_view.add_argument("kind", choices=["stale_mirror", "tombstone", "authority_transition", "reconcile_matrix"])
    result_view.add_argument("--root", required=True)
    result_view.add_argument("--stale-generation-gap", type=int, default=3)
    result_view.add_argument("--policy-allow-stale", action="store_true")
    result_view.add_argument("--signed-tombstone", action="store_true")
    result_view.add_argument("--local-dirty", action="store_true")
    result_view.add_argument("--authority-mode", default="local_first", choices=["local_first", "provider_first", "hybrid"])
    result_view.add_argument("--current-authority", default="local")
    result_view.add_argument("--requested-authority", default="remote")
    result_view.add_argument("--quorum-granted", action="store_true")
    result_view.set_defaults(func=cmd_show_result_view)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
