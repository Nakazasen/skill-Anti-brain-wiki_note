from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import entry, ingest as ingest_module, output, overview as overview_module, review, save as save_module
from .doctor import build_doctor_report, render_doctor_report
from .gaps import build_gap_report, render_gap_report
from .inspect import build_inspect_report, render_inspect_report
from .help import build_help_report, render_help_report
from .migrate import build_migration_report, render_migration_report
from .providers import (
    explain_route,
    list_providers,
    prepare_ask_task,
    render_provider_list,
    render_provider_route,
    render_provider_test,
    run_provider_health_checks,
    set_ask_mode,
    set_default_provider,
)
from .self_check import build_self_check_report, render_self_check_report
from .upgrade import build_upgrade_report, perform_upgrade, render_upgrade_report
from .version import build_version_report, render_version_report
from .recovery import build_recovery_report, render_recovery_report
from .recovery_verify import build_verify_report, render_verify_report
from .trend import build_trend_report, render_trend_report
from .improve import build_improvement_plan, render_improvement_plan
from .commands import DEPRECATED_ALIASES, PUBLIC_HELP
from .legacy import load
from .workspace import ensure_workspace, init_workspace, resolve_workspace


USER_LEVELS = ("beginner", "intermediate", "expert")


class _LazyLegacyModule:
    def __init__(self, name: str):
        self._name = name
        self._module = None

    def _load(self):
        if self._module is None:
            self._module = load(self._name)
        return self._module

    def __getattr__(self, item):
        return getattr(self._load(), item)


_legacy_entry = _LazyLegacyModule("abw_entry")


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
    parser.add_argument("--workspace", help="Path to workspace root")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--level", choices=USER_LEVELS)
    parser.add_argument("--json", action="store_true", help="Output report in JSON format")

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
    add_public_parser(sub, "inspect")
    add_public_parser(sub, "gaps")
    add_public_parser(sub, "recover-plan")
    add_public_parser(sub, "recover-verify")
    add_public_parser(sub, "trend")
    add_public_parser(sub, "improve")
    provider = add_public_parser(sub, "provider")
    provider_sub = provider.add_subparsers(dest="provider_command", metavar="provider-command")

    provider_sub.add_parser("list", help="List configured providers and statuses.")
    provider_sub.add_parser("test", help="Run provider health checks.")

    provider_set = provider_sub.add_parser("set-default", help="Set default provider.")
    provider_set.add_argument("name")
    provider_mode = provider_sub.add_parser("set-mode", help="Set ask mode.")
    provider_mode.add_argument("mode")

    provider_route = provider_sub.add_parser("route", help="Provider routing tools.")
    provider_route_sub = provider_route.add_subparsers(dest="provider_route_command", metavar="route-command")
    provider_explain = provider_route_sub.add_parser("explain", help="Explain route decision.")
    provider_explain.add_argument("--task", default="general")
    provider_explain.add_argument("--sensitivity", default="normal")
    provider_explain.add_argument("--cost", default="balanced")

    upgrade_parser = add_hidden_parser(sub, "upgrade")
    upgrade_parser.add_argument("--check", action="store_true")
    upgrade_parser.add_argument("--to", dest="to_version")
    upgrade_parser.add_argument("--rollback", action="store_true")
    upgrade_parser.add_argument("--channel", choices=("stable", "beta"), default="stable")
    add_hidden_parser(sub, "rollback")
    repair_parser = add_hidden_parser(sub, "repair")
    repair_parser.add_argument("--dry-run", action="store_true")
    add_hidden_parser(sub, "self-check")
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

    eval_parser = add_hidden_parser(sub, "eval")
    eval_parser.add_argument("--questions", help="Path to custom eval questions YAML/JSON.")

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
    result = _legacy_entry.execute_command("/abw-doctor", workspace=workspace)
    return _legacy_entry.final_output(result)


def _version_result(workspace: str):
    result = _legacy_entry.execute_command("/abw-version", workspace=workspace)
    return _legacy_entry.final_output(result)


def _migrate_result(workspace: str):
    result = _legacy_entry.execute_command("/abw-migrate", workspace=workspace)
    return _legacy_entry.final_output(result)


def _upgrade_result(workspace: str):
    return _legacy_entry.execute_command("/abw-update", workspace=workspace)


def _rollback_result(workspace: str):
    return _legacy_entry.execute_command("/abw-rollback", workspace=workspace)


def _repair_result(workspace: str, *, dry_run: bool = False):
    task = "--dry-run" if dry_run else ""
    return _legacy_entry.execute_command("/abw-repair", task=task, workspace=workspace)


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
            ask_plan = prepare_ask_task(workspace, args.text)
            result = _legacy_entry.final_output(
                _legacy_entry.execute_command("/abw-ask", task=ask_plan["task"], workspace=str(workspace))
            )
            if isinstance(result, dict):
                result["provider"] = ask_plan["provider"]
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "ingest":
            result = ingest_module.ingest(args.path, workspace=str(workspace))
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "review":
            result = _legacy_entry.final_output(
                _legacy_entry.execute_command("/abw-review", workspace=str(workspace))
            )
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "overview":
            print(overview_module.build_overview(workspace)["content"], end="")
            return 0

        if args.command == "version":
            return _render_and_exit(_version_result(str(workspace)), debug=debug, level=level)

        if args.command == "migrate":
            return _render_and_exit(_migrate_result(str(workspace)), debug=debug, level=level)

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

        if args.command == "inspect":
            report = build_inspect_report(workspace)
            print(render_inspect_report(report))
            return 0

        if args.command == "gaps":
            print(render_gap_report(build_gap_report(workspace)))
            return 0

        if args.command == "recover-plan":
            print(render_recovery_report(build_recovery_report(workspace)))
            return 0

        if args.command == "recover-verify":
            report = build_verify_report(workspace)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(render_verify_report(report))
            return 0

        if args.command == "trend":
            report = build_trend_report(workspace)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(render_trend_report(report))
            return 0

        if args.command == "improve":
            report = build_improvement_plan(workspace)
            if args.json:
                print(json.dumps(report, indent=2))
            else:
                print(render_improvement_plan(report))
            return 0

        if args.command == "provider":
            if args.provider_command == "list":
                print(render_provider_list(list_providers(workspace)))
                return 0
            if args.provider_command == "test":
                print(render_provider_test(run_provider_health_checks(workspace)))
                return 0
            if args.provider_command == "set-default":
                try:
                    result = set_default_provider(workspace, args.name)
                except ValueError as exc:
                    print(str(exc))
                    return 2
                print(f"default provider set to: {result['default']}")
                print(f"fallback_chain: {', '.join(result['fallback_chain'])}")
                return 0
            if args.provider_command == "set-mode":
                try:
                    result = set_ask_mode(workspace, args.mode)
                except ValueError as exc:
                    print(str(exc))
                    return 2
                print(f"ask mode set to: {result['ask_mode']}")
                return 0
            if args.provider_command == "route" and args.provider_route_command == "explain":
                report = explain_route(
                    workspace,
                    task=getattr(args, "task", "general"),
                    sensitivity=getattr(args, "sensitivity", "normal"),
                    cost_mode=getattr(args, "cost", "balanced"),
                )
                print(render_provider_route(report))
                return 0
            print("Unknown provider command")
            return 2

        if args.command == "upgrade":
            if getattr(args, "check", False):
                report = build_upgrade_report(
                    workspace,
                    channel=getattr(args, "channel", "stable"),
                    to_version=getattr(args, "to_version", None),
                    rollback=getattr(args, "rollback", False),
                )
            else:
                report = perform_upgrade(
                    workspace,
                    check=False,
                    to_version=getattr(args, "to_version", None),
                    rollback=getattr(args, "rollback", False),
                    channel=getattr(args, "channel", "stable"),
                )
            print(render_upgrade_report(report))
            status = str(report.get("status") or "check")
            return 0 if status in {"check", "success"} else 2

        if args.command == "rollback":
            return _render_and_exit(_rollback_result(str(workspace)), debug=debug, level=level)

        if args.command == "repair":
            return _render_and_exit(_repair_result(str(workspace), dry_run=getattr(args, "dry_run", False)), debug=debug, level=level)

        if args.command == "self-check":
            print(render_self_check_report(build_self_check_report(workspace)))
            return 0

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

        if args.command == "eval":
            from .eval import EvalHarness

            harness = EvalHarness(str(workspace), abw_version="0.7.1")
            questions = harness.load_questions(getattr(args, "questions", None))
            
            def runner(q_text):
                ask_plan = prepare_ask_task(workspace, q_text)
                res = _legacy_entry.final_output(
                    _legacy_entry.execute_command("/abw-ask", task=ask_plan["task"], workspace=str(workspace))
                )
                # Res looks like {"content": "...", "citations": [...], "logs": [...]}
                return res.get("content", ""), res.get("citations", []), res.get("logs", [])

            harness.run_eval(questions, runner)
            report = harness.generate_report()
            report_path = harness.save_report(os.path.join(str(workspace), ".brain", "eval"))
            print(f"Eval complete. Report saved to: {report_path}")
            return _render_and_exit(report, debug=debug, level=level)

        print("Unknown command")
        return 2
    finally:
        if previous_entry_caller is None:
            os.environ.pop("ABW_ENTRY_CALLER", None)
        else:
            os.environ["ABW_ENTRY_CALLER"] = previous_entry_caller


if __name__ == "__main__":
    raise SystemExit(main())
