from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import __version__, entry, ingest as ingest_module, output, overview as overview_module, review, save as save_module
from .api import _normalize_ask_result
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
from .apply import ACTIONS as APPLY_ACTIONS, render_apply_report, run_apply, run_rollback
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
    apply_parser = add_public_parser(sub, "apply")
    apply_parser.add_argument("--dry-run", action="store_true", help="Plan only. This is the default unless --yes is used.")
    apply_parser.add_argument("--yes", action="store_true", help="Apply the planned remediation.")
    apply_parser.add_argument("apply_action", choices=(*APPLY_ACTIONS, "rollback"))
    apply_parser.add_argument("rollback_id", nargs="?")
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


def _json_status(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return "success"
    retrieval_status = str(payload.get("retrieval_status") or "").strip()
    if retrieval_status in {"no_match", "wrong_workspace", "ambiguous", "no_confident_workspace", "blocked"}:
        return retrieval_status
    current_state = str(payload.get("current_state") or "").strip()
    if current_state in {"knowledge_gap_logged", "blocked", "approval_required"}:
        return current_state
    runner_status = str(payload.get("runner_status") or "").strip()
    if runner_status == "blocked":
        return "blocked"
    status = str(payload.get("status") or "").strip().lower()
    if status in {"blocked", "warning", "error", "failed"}:
        return status
    overall = str(payload.get("overall") or "").strip().upper()
    if overall == "WARN":
        return "warning"
    ok_value = payload.get("ok")
    if ok_value is False:
        return "warning"
    return "success"


def _standardize_json(data: dict, command_name: str, workspace: Path | str, status: str | None = None) -> dict:
    return {
        "schema_version": "1",
        "command_name": command_name,
        "workspace": str(workspace),
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": status or _json_status(data),
        "data": data,
    }


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


def _ask_json_data(result: Any, workspace: Path | str) -> dict[str, Any]:
    normalized = _normalize_ask_result(result, workspace_root=Path(workspace))
    if not isinstance(result, dict):
        return {
            "answer": normalized["answer"],
            "retrieval_status": normalized["retrieval_status"],
            "trust_score": normalized["trust_score"],
            "sources": normalized["sources"],
            "warnings": normalized["warnings"],
            "gap_logged": False,
            "gap_id": None,
            "current_state": None,
            "knowledge_evidence_tier": None,
            "knowledge_source_score": None,
            "source_summary": None,
            "logs": normalized.get("logs", []),
            "provider": None,
            "gap_log_suppressed": False,
            "would_log_gap": False,
            "runtime_write_suppressed": False,
        }
    knowledge = (
        result.get("knowledge_output")
        if isinstance(result.get("knowledge_output"), dict)
        else (result.get("knowledge") if isinstance(result.get("knowledge"), dict) else {})
    )
    explicit_gap_logged = result.get("gap_logged")
    if explicit_gap_logged is None and "gap_logged" in knowledge:
        explicit_gap_logged = knowledge.get("gap_logged")
    if explicit_gap_logged is None:
        gap_logged = str(result.get("current_state") or "").strip() == "knowledge_gap_logged"
    else:
        gap_logged = bool(explicit_gap_logged)
    return {
        "answer": normalized["answer"],
        "retrieval_status": normalized["retrieval_status"],
        "trust_score": normalized["trust_score"],
        "sources": normalized["sources"],
        "warnings": normalized["warnings"],
        "gap_logged": gap_logged,
        "gap_id": result.get("gap_id") or knowledge.get("gap_id"),
        "current_state": result.get("current_state"),
        "knowledge_evidence_tier": result.get("knowledge_evidence_tier") or knowledge.get("tier"),
        "knowledge_source_score": result.get("knowledge_source_score") or knowledge.get("score"),
        "source_summary": result.get("source_summary") or knowledge.get("source_summary"),
        "logs": normalized.get("logs", []),
        "provider": result.get("provider"),
        "gap_log_suppressed": bool(result.get("gap_log_suppressed") or knowledge.get("gap_log_suppressed")),
        "would_log_gap": bool(result.get("would_log_gap") or knowledge.get("would_log_gap")),
        "runtime_write_suppressed": bool(result.get("runtime_write_suppressed") or knowledge.get("runtime_write_suppressed")),
    }


def _doctor_json_data(workspace: Path | str) -> dict[str, Any]:
    report = build_doctor_report(workspace)
    return {
        "checks": report.get("checks", []),
        "ok": str(report.get("overall") or "").upper() == "OK",
        "warnings": report.get("top_warnings", []),
        "workspace_health": report.get("workspace_health"),
        "engine_health": report.get("engine_health"),
    }


def _version_json_data(workspace: Path | str) -> dict[str, Any]:
    report = build_version_report(workspace)
    return {
        "version": report.get("package_version") or __version__,
        "package": "abw_skill",
        "python": report.get("python"),
        "git_commit": report.get("git_commit"),
        "git_tag": report.get("git_tag"),
        "install_mode": report.get("install_mode"),
        "runtime_source": report.get("runtime_source"),
    }


def _ingest_json_data(result: Any) -> dict[str, Any]:
    payload = result if isinstance(result, dict) else {}
    ingest_result = payload.get("ingest_result") if isinstance(payload.get("ingest_result"), dict) else {}
    return {
        "ingested": int(ingest_result.get("ingested_count") or 0),
        "skipped": int(ingest_result.get("skipped_count") or 0),
        "errors": _as_list(ingest_result.get("errors")),
        "report_path": ingest_result.get("report_path"),
        "gaps_path": ingest_result.get("gaps_path"),
        "promotion_performed": bool(ingest_result.get("promotion_performed", False)),
        "current_state": payload.get("current_state"),
        "runner_status": payload.get("runner_status"),
        "warnings": _as_list(payload.get("warnings")),
    }


def _review_json_data(result: Any) -> dict[str, Any]:
    payload = result if isinstance(result, dict) else {}
    batch = payload.get("draft_batch_review") if isinstance(payload.get("draft_batch_review"), dict) else {}
    items = batch.get("items") if isinstance(batch.get("items"), list) else []
    pending_drafts = payload.get("pending_drafts") if isinstance(payload.get("pending_drafts"), list) else []
    return {
        "pending": len(pending_drafts) if pending_drafts else len(items),
        "reviewed": len(items),
        "actions": payload.get("next_actions") if isinstance(payload.get("next_actions"), list) else [],
        "warnings": _as_list(payload.get("warnings")),
        "current_state": payload.get("current_state"),
        "runner_status": payload.get("runner_status"),
    }


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
            if args.json:
                print(json.dumps(_standardize_json(_ask_json_data(result, workspace), "ask", workspace), indent=2))
                return _result_exit_code(result if isinstance(result, dict) else {})
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "ingest":
            result = ingest_module.ingest(args.path, workspace=str(workspace))
            if args.json:
                print(json.dumps(_standardize_json(_ingest_json_data(result), "ingest", workspace), indent=2))
                return _result_exit_code(result if isinstance(result, dict) else {})
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "review":
            result = _legacy_entry.final_output(
                _legacy_entry.execute_command("/abw-review", workspace=str(workspace))
            )
            if args.json:
                print(json.dumps(_standardize_json(_review_json_data(result), "review", workspace), indent=2))
                return _result_exit_code(result if isinstance(result, dict) else {})
            return _render_and_exit(result, debug=debug, level=level)

        if args.command == "overview":
            print(overview_module.build_overview(workspace)["content"], end="")
            return 0

        if args.command == "version":
            if args.json:
                print(json.dumps(_standardize_json(_version_json_data(workspace), "version", workspace), indent=2))
                return 0
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
            if args.json:
                print(json.dumps(_standardize_json(_doctor_json_data(workspace), "doctor", workspace), indent=2))
                return 0
            return _render_and_exit(_doctor_result(str(workspace)), debug=debug, level=level)

        if args.command == "inspect":
            report = build_inspect_report(workspace)
            if args.json:
                print(json.dumps(_standardize_json(report, "inspect", workspace), indent=2))
            else:
                print(render_inspect_report(report))
            return 0

        if args.command == "gaps":
            report = build_gap_report(workspace)
            if args.json:
                print(json.dumps(_standardize_json(report, "gaps", workspace), indent=2))
            else:
                print(render_gap_report(report))
            return 0

        if args.command == "recover-plan":
            report = build_recovery_report(workspace)
            if args.json:
                print(json.dumps(_standardize_json(report, "recover-plan", workspace), indent=2))
            else:
                print(render_recovery_report(report))
            return 0

        if args.command == "recover-verify":
            report = build_verify_report(workspace)
            if args.json:
                print(json.dumps(_standardize_json(report, "recover-verify", workspace), indent=2))
            else:
                print(render_verify_report(report))
            return 0

        if args.command == "trend":
            report = build_trend_report(workspace)
            if args.json:
                print(json.dumps(_standardize_json(report, "trend", workspace), indent=2))
            else:
                print(render_trend_report(report))
            return 0

        if args.command == "improve":
            report = build_improvement_plan(workspace)
            if args.json:
                print(json.dumps(_standardize_json(report, "improve", workspace), indent=2))
            else:
                print(render_improvement_plan(report))
            return 0

        if args.command == "apply":
            try:
                if args.apply_action == "rollback":
                    if not args.rollback_id:
                        print("Missing action id. Use: abw apply rollback <action-id> --yes")
                        return 2
                    report = run_rollback(workspace, args.rollback_id, yes=getattr(args, "yes", False))
                else:
                    report = run_apply(workspace, args.apply_action, yes=getattr(args, "yes", False))
            except ValueError as exc:
                print(str(exc))
                return 2
            if args.json:
                print(json.dumps(_standardize_json(report, "apply", workspace), indent=2))
            else:
                print(render_apply_report(report))
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

            harness = EvalHarness(str(workspace), abw_version=__version__)
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
