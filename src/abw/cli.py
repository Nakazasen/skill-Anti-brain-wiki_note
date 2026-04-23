from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import entry, ingest as ingest_module, output, overview as overview_module, review, save as save_module
from .legacy import load
from .workspace import init_workspace, resolve_workspace


USER_LEVELS = ("beginner", "intermediate", "expert")
_legacy_entry = load("abw_entry")

DEPRECATED_ALIASES = {
    "health": "doctor",
    "update": "upgrade",
    "query": "ask",
    "query-deep": "ask",
    "query_deep": "ask",
}


def add_common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--debug", action="store_true", default=argparse.SUPPRESS)
    parser.add_argument("--level", choices=USER_LEVELS, default=argparse.SUPPRESS)
    return parser


def add_hidden_parser(subparsers, name):
    return add_common(subparsers.add_parser(name, help=argparse.SUPPRESS))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="abw")
    parser.add_argument("--workspace", help="Workspace directory. Defaults to ABW_WORKSPACE or the current directory.")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--level", choices=USER_LEVELS)

    sub = parser.add_subparsers(dest="command")

    help_parser = add_common(sub.add_parser("help"))
    help_parser.add_argument("--advanced", action="store_true")

    ask = add_common(sub.add_parser("ask"))
    ask.add_argument("text")

    ingest_parser = add_common(sub.add_parser("ingest"))
    ingest_parser.add_argument("path")

    add_common(sub.add_parser("review"))
    add_common(sub.add_parser("overview"))
    save_parser = add_common(sub.add_parser("save"))
    save_parser.add_argument("text", nargs="?")
    save_parser.add_argument("--stdin", action="store_true")
    add_common(sub.add_parser("doctor"))
    add_common(sub.add_parser("upgrade"))
    add_common(sub.add_parser("rollback"))
    add_common(sub.add_parser("repair"))
    add_common(sub.add_parser("research"))
    add_common(sub.add_parser("init"))
    sub.add_parser("menu")

    approve = add_hidden_parser(sub, "approve")
    approve.add_argument("path")
    add_hidden_parser(sub, "dashboard")
    add_hidden_parser(sub, "coverage")
    add_hidden_parser(sub, "health")
    add_hidden_parser(sub, "update")

    query = add_hidden_parser(sub, "query")
    query.add_argument("text")
    query_deep = add_hidden_parser(sub, "query-deep")
    query_deep.add_argument("text")
    query_deep_alt = add_hidden_parser(sub, "query_deep")
    query_deep_alt.add_argument("text")

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
    print("1. View system")
    print("2. Ask something")
    print("3. Add file")
    print("4. Review drafts")
    print("0. Exit")
    return 0


def _print_deprecation(command: str) -> None:
    replacement = DEPRECATED_ALIASES.get(command)
    if replacement:
        print(f"Deprecated command. Use: abw {replacement}")


def _doctor_result(workspace: str):
    return _legacy_entry.execute_command("/abw-health", workspace=workspace)


def _upgrade_result(workspace: str):
    return _legacy_entry.execute_command("/abw-update", workspace=workspace)


def _rollback_result(workspace: str):
    return _legacy_entry.execute_command("/abw-rollback", workspace=workspace)


def _repair_result(workspace: str):
    return _legacy_entry.execute_command("/abw-repair", workspace=workspace)


def main(argv=None) -> int:
    output.configure_stdout()
    previous_entry_caller = os.environ.get("ABW_ENTRY_CALLER")
    os.environ["ABW_ENTRY_CALLER"] = "abw_cli"

    try:
        args = parse_args(argv)
        workspace = resolve_workspace(args.workspace)
        debug = getattr(args, "debug", False)
        level = getattr(args, "level", None)

        if args.command is None or args.command == "menu":
            return _print_menu()

        if args.command == "init":
            root = init_workspace(workspace)
            print(f"ABW workspace initialized: {root}")
            print("Created: raw/, wiki/, drafts/, abw_config.json")
            return 0

        if args.command == "help":
            previous = os.environ.get("ABW_HELP_ADVANCED")
            if getattr(args, "advanced", False):
                os.environ["ABW_HELP_ADVANCED"] = "1"
            else:
                os.environ.pop("ABW_HELP_ADVANCED", None)
            try:
                result = entry.ask("help", workspace=str(workspace))
            finally:
                if previous is None:
                    os.environ.pop("ABW_HELP_ADVANCED", None)
                else:
                    os.environ["ABW_HELP_ADVANCED"] = previous
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "ask":
            if str(args.text).strip().lower() == "overview":
                print(overview_module.build_overview(workspace)["content"], end="")
                return 0
            result = entry.ask(args.text, workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "ingest":
            result = ingest_module.ingest(args.path, workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "review":
            result = review.review_drafts(workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "overview":
            print(overview_module.build_overview(workspace)["content"], end="")
            return 0

        if args.command == "save":
            text = args.text
            if getattr(args, "stdin", False):
                text = sys.stdin.read()
            try:
                saved = save_module.save_candidate(text, workspace)
            except ValueError as exc:
                print(str(exc))
                return 2
            print(f"Saved candidate note: {saved['relative_path']}")
            print(f"Suggested next step: {saved['next_step']}")
            return 0

        if args.command == "doctor":
            return _render_and_exit(_doctor_result(str(workspace)), debug=debug, level=level)

        if args.command == "upgrade":
            return _render_and_exit(_upgrade_result(str(workspace)), debug=debug, level=level)

        if args.command == "rollback":
            return _render_and_exit(_rollback_result(str(workspace)), debug=debug, level=level)

        if args.command == "repair":
            return _render_and_exit(_repair_result(str(workspace)), debug=debug, level=level)

        if args.command == "research":
            print('Research mode is not a separate public runtime command yet. Use: abw ask "..."')
            return 2

        if args.command == "approve":
            result = review.approve_draft(args.path, workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "dashboard":
            result = entry.dashboard(workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "coverage":
            result = entry.ask("coverage", workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "health":
            _print_deprecation("health")
            return _render_and_exit(_doctor_result(str(workspace)), debug=debug, level=level)

        if args.command == "update":
            _print_deprecation("update")
            return _render_and_exit(_upgrade_result(str(workspace)), debug=debug, level=level)

        if args.command == "query":
            _print_deprecation("query")
            result = entry.ask(args.text, workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command in {"query-deep", "query_deep"}:
            _print_deprecation("query-deep")
            result = entry.ask(args.text, workspace=str(workspace))
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
