import argparse
import json
import os
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))
ROOT = current_dir.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import abw_health
import abw_alias
import abw_output
import abw_proof
import abw_runner
import abw_update
from abw.migrate import build_migration_report, render_migration_report
from abw.version import build_version_report, render_version_report, stale_install_suspected


SUPPORTED_COMMANDS = {
    "/abw-ask",
    "/abw-doctor",
    "/abw-version",
    "/abw-migrate",
    "/abw-health",
    "/abw-status",
    "/abw-repair",
    "/abw-update",
    "/abw-rollback",
}
LEGACY_COMMAND_ALIASES = {
    "/abw-health": "/abw-doctor",
    "/abw-status": "/abw-doctor",
}
AI_EXECUTION_PATH = "ai_runner"


def enforce_agent_execution_path():
    is_agent_mode = os.environ.get("ABW_AGENT_MODE") == "1"
    is_inline_python = Path(sys.argv[0]).name == "-c"
    is_ai_runner = os.environ.get("ABW_EXECUTION_PATH") == AI_EXECUTION_PATH
    allow_raw_entry = os.environ.get("ABW_ALLOW_RAW_ENTRY") == "1"
    if (is_agent_mode or is_inline_python) and not is_ai_runner and not allow_raw_entry:
        raise RuntimeError("Forbidden: Agent must use ai_runner.py (single execution path).")


def final_output(result):
    enforce_agent_execution_path()
    if isinstance(result, dict) and result.get("evaluation") is None:
        result = abw_runner.apply_acceptance_validation(
            result,
            workspace=result.get("workspace") or ".",
        )
    result = abw_output.enforce_runner_output(result)
    result = abw_runner.enforce_output_acceptance(result, mode="STRICT")
    return result


def render_final_output(result, workspace="."):
    return abw_output.render(final_output(result))


def handle_input(
    user_input,
    *,
    workspace=".",
    runtime_root=None,
    task_kind="execution",
    candidate_answer=None,
):
    text = str(user_input or "").strip()
    if text.startswith("/"):
        command, _, task = text.partition(" ")
    else:
        command = "/abw-ask"
        task = text

    result = execute_command(
        command,
        task=task.strip(),
        workspace=workspace,
        runtime_root=runtime_root,
        task_kind=task_kind,
        candidate_answer=candidate_answer,
    )
    return final_output(result)


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _structured_runner_result(*, task: str, body: str, details: dict, binding_source: str = "cli"):
    return abw_update.build_result(
        task=task,
        binding_source=binding_source,
        binding_status="runner_enforced",
        current_state="checked_only",
        runner_status="completed",
        body=body,
        evidence=f"{task} rendered deterministic report",
        gaps_or_limitations="report only; no additional task execution was performed",
        next_steps="use the matching CLI command for follow-up actions if needed",
        details=details,
    )


def _append_hint_to_result(result: dict, hint: str) -> dict:
    if not isinstance(result, dict) or not hint:
        return result
    finalization_block = str(result.get("finalization_block") or "").strip()
    answer = str(result.get("answer") or "").strip()
    if not finalization_block or not answer.endswith(finalization_block):
        return result
    body = answer[: -len(finalization_block)].rstrip()
    body = f"{body}\n\n{hint}".strip()
    updated_answer = f"{body}\n\n{finalization_block}".strip()
    updated = dict(result)
    updated["answer"] = updated_answer
    updated["validation_proof"] = abw_proof.generate_proof(
        updated_answer,
        finalization_block,
        str(updated.get("runtime_id") or ""),
        str(updated.get("nonce") or ""),
        str(updated.get("binding_source") or "cli"),
    )
    return updated


def _effective_health_runtime_root(runtime_root, runtime_state):
    if runtime_root:
        return runtime_root
    integrity = runtime_state.get("integrity") if isinstance(runtime_state, dict) else {}
    if isinstance(integrity, dict):
        resolved = integrity.get("runtime_root")
        if resolved:
            return resolved
    return None


def execute_command(
    command,
    *,
    task="",
    workspace=".",
    runtime_root=None,
    task_kind="execution",
    candidate_answer=None,
):
    enforce_agent_execution_path()
    command, task = abw_alias.rewrite_entry_command(command, task)
    command = LEGACY_COMMAND_ALIASES.get(command, command)
    runtime_state_root = runtime_root or str(Path(__file__).resolve().parent.parent)
    runtime_state = abw_update.initialize_runtime(runtime_state_root)
    effective_health_runtime_root = _effective_health_runtime_root(runtime_root, runtime_state)
    if command not in SUPPORTED_COMMANDS:
        if str(command or "").startswith("/abw-"):
            command, task = "/abw-ask", f"{command} {task}".strip()
        else:
            return {
                "binding_status": "rejected",
                "current_state": "blocked",
                "reason": "unsupported command",
                "workspace": workspace,
            }

    if command not in SUPPORTED_COMMANDS:
        return {
            "binding_status": "rejected",
            "current_state": "blocked",
            "reason": "unsupported command",
            "workspace": workspace,
        }

    if (
        runtime_state["integrity"]["state"] == "integrity_compromised"
        and command == "/abw-ask"
    ):
        return {
            "binding_status": "rejected",
            "current_state": "integrity_compromised",
            "reason": "runtime integrity mismatch detected",
            "integrity": runtime_state["integrity"],
            "workspace": workspace,
        }

    if command == "/abw-ask":
        result = abw_runner.dispatch_request(
            task=task,
            workspace=workspace,
            task_kind=task_kind,
            candidate_answer=candidate_answer,
            binding_mode="STRICT",
            binding_source="cli",
        )
        if isinstance(result, dict):
            result.setdefault("workspace", workspace)
        return result

    if command == "/abw-doctor":
        result = abw_health.run_health(
            workspace=workspace,
            runtime_root=effective_health_runtime_root,
            binding_status="runner_enforced",
            mode="audit",
        )
        version_report = build_version_report(workspace)
        if version_report.get("release_verification_status") == "unverified_wheel_release":
            result = _append_hint_to_result(
                result,
                "Release verification: unverified_wheel_release. Wheel package version is primary truth; git tag metadata is unavailable.",
            )
        if stale_install_suspected(version_report):
            result = _append_hint_to_result(
                result,
                "Stale install suspected. Run `abw self-check`.",
            )
        if isinstance(result, dict):
            result.setdefault("workspace", workspace)
        return result

    if command == "/abw-version":
        report = build_version_report(workspace)
        result = _structured_runner_result(
            task="/abw-version",
            body=render_version_report(report),
            details={"version_report": report},
        )
        result.setdefault("workspace", workspace)
        return result

    if command == "/abw-migrate":
        report = build_migration_report(workspace)
        result = _structured_runner_result(
            task="/abw-migrate",
            body=render_migration_report(report),
            details={"migration_report": report},
        )
        result.setdefault("workspace", workspace)
        return result

    if command == "/abw-update":
        target_ref = str(task or "").strip() or None
        result = abw_update.perform_update(workspace=workspace, target_ref=target_ref)
        if isinstance(result, dict):
            result.setdefault("workspace", workspace)
        return result

    if command == "/abw-rollback":
        result = abw_update.perform_rollback(workspace=workspace)
        if isinstance(result, dict):
            result.setdefault("workspace", workspace)
        return result

    dry_run = "--dry-run" in str(task or "").split()
    result = abw_health.run_health(
        workspace=workspace,
        runtime_root=effective_health_runtime_root,
        binding_status="runner_enforced",
        mode="repair",
        dry_run=dry_run,
    )
    if isinstance(result, dict):
        result.setdefault("workspace", workspace)
    return result


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Canonical CLI-first ABW entrypoint.")
    parser.add_argument("command")
    parser.add_argument("task_parts", nargs="*", help="Task text for /abw-ask.")
    parser.add_argument("--task", help="Explicit task text for /abw-ask.")
    parser.add_argument("--debug", action="store_true", help="Show the full trusted runner payload.")
    parser.add_argument("--level", choices=sorted(abw_output.USER_LEVELS), help="Override adaptive agent output level.")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--runtime-root")
    parser.add_argument("--task-kind", default="execution")
    parser.add_argument("--candidate-answer")
    parser.add_argument("--dry-run", action="store_true", help="For /abw-repair, report repair actions without changing files.")
    parser.add_argument("--input-json", action="store_true", help="Read JSON payload from stdin.")
    return parser.parse_args(argv)


def _read_payload(args):
    payload = {}
    if args.input_json:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}

    task = args.task
    if task is None:
        task = payload.get("task")
    if task is None:
        task = " ".join(args.task_parts).strip()

    return {
        "task": task,
        "debug": bool(payload.get("debug", args.debug)),
        "level": payload.get("level", args.level),
        "workspace": payload.get("workspace", args.workspace),
        "runtime_root": payload.get("runtime_root", args.runtime_root),
        "task_kind": payload.get("task_kind", args.task_kind),
        "candidate_answer": payload.get("candidate_answer", args.candidate_answer),
        "dry_run": bool(payload.get("dry_run", args.dry_run)),
    }


def main(argv=None):
    configure_stdout()
    previous_cli_mode = os.environ.get("ABW_CLI_MODE")
    os.environ["ABW_CLI_MODE"] = "1"
    try:
        args = parse_args(argv)
        payload = _read_payload(args)
        task = payload["task"]
        if args.command == "/abw-repair" and payload["dry_run"] and "--dry-run" not in str(task or "").split():
            task = f"{task} --dry-run".strip()
        result = execute_command(
            args.command,
            task=task,
            workspace=payload["workspace"],
            runtime_root=payload["runtime_root"],
            task_kind=payload["task_kind"],
            candidate_answer=payload["candidate_answer"],
        )
        trusted_result = final_output(result)
        print(abw_output.render(trusted_result, debug=payload["debug"], level=payload["level"]))
        return 0 if trusted_result.get("binding_status") != "rejected" and trusted_result.get("runner_status") != "blocked" else 3
    finally:
        if previous_cli_mode is None:
            os.environ.pop("ABW_CLI_MODE", None)
        else:
            os.environ["ABW_CLI_MODE"] = previous_cli_mode


if __name__ == "__main__":
    if os.environ.get("ABW_ENTRY_CALLER") != "abw_cli" and os.environ.get("ABW_DEV_ENTRY") != "1":
        print("Do not run abw_entry directly. Use 'abw' CLI. Set ABW_DEV_ENTRY=1 for dev mode.", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())
