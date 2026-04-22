from __future__ import annotations

import argparse
import os
from pathlib import Path

from . import entry, ingest as ingest_module, output, review
from .workspace import init_workspace, resolve_workspace


USER_LEVELS = ("beginner", "intermediate", "expert")


def add_common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--debug", action="store_true", default=argparse.SUPPRESS)
    parser.add_argument("--level", choices=USER_LEVELS, default=argparse.SUPPRESS)
    return parser


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="abw")
    parser.add_argument("--workspace", help="Workspace directory. Defaults to ABW_WORKSPACE or the current directory.")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--level", choices=USER_LEVELS)

    sub = parser.add_subparsers(dest="command")

    add_common(sub.add_parser("help"))

    ask = add_common(sub.add_parser("ask"))
    ask.add_argument("text")

    ingest_parser = add_common(sub.add_parser("ingest"))
    ingest_parser.add_argument("path")

    add_common(sub.add_parser("dashboard"))
    add_common(sub.add_parser("init"))
    add_common(sub.add_parser("review"))

    approve = add_common(sub.add_parser("approve"))
    approve.add_argument("path")

    add_common(sub.add_parser("coverage"))
    add_common(sub.add_parser("health"))

    return parser.parse_args(argv)


def _result_exit_code(result) -> int:
    if result.get("binding_status") == "rejected":
        return 3
    if result.get("runner_status") == "blocked":
        return 3
    return 0


def _render_and_exit(result, *, debug: bool = False, level: str | None = None) -> int:
    print(output.render(result, debug=debug, level=level))
    return _result_exit_code(result)


def _print_menu() -> int:
    print("ABW")
    print("---")
    print()
    print('Use: abw ask "what you want to do"')
    print()
    print("Common commands:")
    print('  abw ask "dashboard"')
    print('  abw ask "help"')
    print("  abw ingest raw/<file>")
    print("  abw init")
    return 0


def main(argv=None) -> int:
    output.configure_stdout()
    previous_entry_caller = os.environ.get("ABW_ENTRY_CALLER")
    os.environ["ABW_ENTRY_CALLER"] = "abw_cli"

    try:
        args = parse_args(argv)
        workspace = resolve_workspace(args.workspace)
        debug = getattr(args, "debug", False)
        level = getattr(args, "level", None)

        if args.command is None:
            return _print_menu()

        if args.command == "init":
            root = init_workspace(workspace)
            print(f"ABW workspace initialized: {root}")
            print("Created: raw/, wiki/, drafts/, abw_config.json")
            return 0

        if args.command == "help":
            result = entry.ask("help", workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "ask":
            result = entry.ask(args.text, workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "ingest":
            result = ingest_module.ingest(args.path, workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "dashboard":
            result = entry.dashboard(workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "review":
            result = review.review_drafts(workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "approve":
            result = review.approve_draft(args.path, workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "coverage":
            result = entry.ask("coverage", workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "health":
            result = entry.ask("health", workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        print("Unknown command")
        return 2
    finally:
        if previous_entry_caller is None:
            os.environ.pop("ABW_ENTRY_CALLER", None)
        else:
            os.environ["ABW_ENTRY_CALLER"] = previous_entry_caller


if __name__ == "__main__":
    raise SystemExit(main())
