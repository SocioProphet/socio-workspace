from __future__ import annotations

import argparse

from .result_html_cli import cmd_show_result_html
from .result_page_cli import cmd_show_result_page
from .result_preview_cli import cmd_show_result_preview


_OUTPUT_MODES = {
    "preview": cmd_show_result_preview,
    "html": cmd_show_result_html,
    "page": cmd_show_result_page,
}


def cmd_show_result_output(args: argparse.Namespace) -> int:
    handler = _OUTPUT_MODES.get(args.output_mode)
    if handler is None:
        return 2
    return handler(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fabric-output")
    parser.add_argument("output_mode", choices=sorted(_OUTPUT_MODES))
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
    return cmd_show_result_output(args)


if __name__ == "__main__":
    raise SystemExit(main())
