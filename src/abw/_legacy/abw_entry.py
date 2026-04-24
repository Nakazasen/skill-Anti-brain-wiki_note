import argparse
import json
import os
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import abw_health
import abw_alias
import abw_output
import abw_runner
import abw_update


SUPPORTED_COMMANDS = {"/abw-ask", "/abw-health", "/abw-repair", "/abw-update", "/abw-rollback"}
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
    runtime_state = abw_update.initialize_runtime(workspace)
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

    if command == "/abw-health":
        result = abw_health.run_health(
            workspace=workspace,
            runtime_root=runtime_root,
            binding_status="runner_enforced",
            mode="audit",
        )
        if isinstance(result, dict):
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

    result = abw_health.run_health(
        workspace=workspace,
        runtime_root=runtime_root,
        binding_status="runner_enforced",
        mode="repair",
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
    }


def main(argv=None):
    configure_stdout()
    previous_cli_mode = os.environ.get("ABW_CLI_MODE")
    os.environ["ABW_CLI_MODE"] = "1"
    try:
        args = parse_args(argv)
        payload = _read_payload(args)
        result = execute_command(
            args.command,
            task=payload["task"],
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
