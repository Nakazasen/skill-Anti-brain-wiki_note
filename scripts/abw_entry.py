import argparse
import json
import sys
from pathlib import Path

current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import abw_health
import abw_output
import abw_runner
import abw_update


SUPPORTED_COMMANDS = {"/abw-ask", "/abw-health", "/abw-repair", "/abw-update", "/abw-rollback"}


def final_output(result):
    result = abw_output.enforce_runner_output(result)
    result = abw_runner.enforce_output_acceptance(result, mode="STRICT")
    return result


def render_final_output(result, workspace="."):
    return abw_runner.render_with_visibility_lock(final_output(result), workspace=workspace)


def execute_command(
    command,
    *,
    task="",
    workspace=".",
    runtime_root=None,
    task_kind="execution",
    candidate_answer=None,
):
    runtime_state = abw_update.initialize_runtime(workspace)
    if command not in SUPPORTED_COMMANDS:
        return {"binding_status": "rejected", "current_state": "blocked", "reason": "unsupported command"}

    if (
        runtime_state["integrity"]["state"] == "integrity_compromised"
        and command == "/abw-ask"
    ):
        return {
            "binding_status": "rejected",
            "current_state": "integrity_compromised",
            "reason": "runtime integrity mismatch detected",
            "integrity": runtime_state["integrity"],
        }

    if command == "/abw-ask":
        return abw_runner.dispatch_request(
            task=task,
            workspace=workspace,
            task_kind=task_kind,
            candidate_answer=candidate_answer,
            binding_mode="STRICT",
            binding_source="cli",
        )

    if command == "/abw-health":
        return abw_health.run_health(
            workspace=workspace,
            runtime_root=runtime_root,
            binding_status="runner_enforced",
            mode="audit",
        )

    if command == "/abw-update":
        target_ref = str(task or "").strip() or None
        return abw_update.perform_update(workspace=workspace, target_ref=target_ref)

    if command == "/abw-rollback":
        return abw_update.perform_rollback(workspace=workspace)

    return abw_health.run_health(
        workspace=workspace,
        runtime_root=runtime_root,
        binding_status="runner_enforced",
        mode="repair",
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Canonical CLI-first ABW entrypoint.")
    parser.add_argument("command", choices=sorted(SUPPORTED_COMMANDS))
    parser.add_argument("task_parts", nargs="*", help="Task text for /abw-ask.")
    parser.add_argument("--task", help="Explicit task text for /abw-ask.")
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
        "workspace": payload.get("workspace", args.workspace),
        "runtime_root": payload.get("runtime_root", args.runtime_root),
        "task_kind": payload.get("task_kind", args.task_kind),
        "candidate_answer": payload.get("candidate_answer", args.candidate_answer),
    }


def main(argv=None):
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
    print(abw_runner.render_with_visibility_lock(trusted_result, workspace=payload["workspace"]))
    return 0 if trusted_result.get("binding_status") != "rejected" and trusted_result.get("runner_status") != "blocked" else 3


if __name__ == "__main__":
    raise SystemExit(main())
