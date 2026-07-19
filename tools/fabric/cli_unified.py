from __future__ import annotations

import argparse

from .cli import (
    cmd_register_demo,
    cmd_run_authority_flow,
    cmd_run_harness,
    cmd_run_stale_mirror_flow,
    cmd_run_tombstone_flow,
    cmd_show_planner_surface,
    cmd_show_result_interface,
    cmd_show_result_plan,
    cmd_show_result_view,
    cmd_show_surface,
    cmd_validate,
)
from .result_output_cli import cmd_show_result_output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fabric-unified")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate-json")
    validate.add_argument("schema")
    validate.add_argument("instance")
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

    output = sub.add_parser("show-output")
    output.add_argument("output_mode", choices=["preview", "html", "page"])
    output.add_argument("kind", choices=["stale_mirror", "tombstone", "authority_transition", "reconcile_matrix"])
    output.add_argument("--root", required=True)
    output.add_argument("--title", default="Fabric Result Preview")
    output.add_argument("--stale-generation-gap", type=int, default=3)
    output.add_argument("--policy-allow-stale", action="store_true")
    output.add_argument("--signed-tombstone", action="store_true")
    output.add_argument("--local-dirty", action="store_true")
    output.add_argument("--authority-mode", default="local_first", choices=["local_first", "provider_first", "hybrid"])
    output.add_argument("--current-authority", default="local")
    output.add_argument("--requested-authority", default="remote")
    output.add_argument("--quorum-granted", action="store_true")
    output.set_defaults(func=cmd_show_result_output)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
