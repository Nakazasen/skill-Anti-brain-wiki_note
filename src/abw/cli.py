from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import entry, ingest as ingest_module, output, overview as overview_module, review, save as save_module
from .doctor import build_doctor_report, render_doctor_report
from .help import build_help_report, render_help_report
from .migrate import build_migration_report, render_migration_report
from .upgrade import build_upgrade_report, render_upgrade_report
from .version import build_version_report, render_version_report
from .commands import DEPRECATED_ALIASES, PUBLIC_HELP
from .legacy import load
from .workspace import ensure_workspace, init_workspace, resolve_workspace


USER_LEVELS = ("beginner", "intermediate", "expert")
_legacy_entry = load("abw_entry")


def add_common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument("--debug", action="store_true", default=argparse.SUPPRESS)
    parser.add_argument("--level", choices=USER_LEVELS, default=argparse.SUPPRESS)
    return parser


def add_hidden_parser(subparsers, name):
    parser = add_common(subparsers.add_parser(name, help=argparse.SUPPRESS))
    subparsers._choices_actions = [action for action in subparsers._choices_actions if action.dest != name]
    return parser


def add_public_parser(subparsers, name):
    return add_common(subparsers.add_parser(name, help=PUBLIC_HELP.get(name)))


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="abw")
    parser.add_argument("--workspace", help="Workspace directory. Defaults to ABW_WORKSPACE or the current directory.")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--level", choices=USER_LEVELS)

    sub = parser.add_subparsers(dest="command", metavar="command")

    help_parser = add_public_parser(sub, "help")
    help_parser.add_argument("--advanced", action="store_true")

    ask = add_public_parser(sub, "ask")
    ask.add_argument("text")

    ingest_parser = add_public_parser(sub, "ingest")
    ingest_parser.add_argument("path")

    add_public_parser(sub, "review")
    add_hidden_parser(sub, "overview")
    add_public_parser(sub, "version")
    add_public_parser(sub, "migrate")
    save_parser = add_hidden_parser(sub, "save")
    save_parser.add_argument("text", nargs="?")
    save_parser.add_argument("--stdin", action="store_true")
    add_public_parser(sub, "doctor")
    add_hidden_parser(sub, "upgrade")
    add_hidden_parser(sub, "rollback")
    add_hidden_parser(sub, "repair")
    add_hidden_parser(sub, "research")
    add_public_parser(sub, "init")
    sub.add_parser("menu", help=argparse.SUPPRESS)
    sub._choices_actions = [action for action in sub._choices_actions if action.dest != "menu"]

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
            report = ensure_workspace(workspace)
            print(f"ABW workspace initialized: {report['root']}")
            if report["config_status"] == "invalid":
                print("Preserved invalid abw_config.json. Run: abw doctor")
                return 2
            created_dirs = ", ".join(f"{name}/" for name in report["created_dirs"]) or "no new folders"
            print(f"Workspace state: {created_dirs}")
            print(f"Workspace schema: {report['config'].get('workspace_schema', 'unknown')}")
            return 0

        if args.command == "help":
            print(render_help_report(build_help_report(workspace, advanced=getattr(args, "advanced", False))))
            return 0

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

        if args.command == "version":
            print(render_version_report(build_version_report(workspace)))
            return 0

        if args.command == "migrate":
            print(render_migration_report(build_migration_report(workspace)))
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
            print(render_doctor_report(build_doctor_report(workspace)))
            return 0

        if args.command == "upgrade":
            print(render_upgrade_report(build_upgrade_report(workspace)))
            return 0

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
            print(render_doctor_report(build_doctor_report(workspace)))
            return 0

        if args.command == "update":
            _print_deprecation("update")
            print(render_upgrade_report(build_upgrade_report(workspace)))
            return 0

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
