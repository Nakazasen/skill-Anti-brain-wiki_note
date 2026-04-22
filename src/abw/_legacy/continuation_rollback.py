import argparse
import json
import subprocess
import sys
from pathlib import Path


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def brain_paths(workspace):
    brain = Path(workspace) / ".brain"
    return {
        "active_execution": brain / "active_execution.json",
        "backlog": brain / "continuation_backlog.json",
    }


def find_step(backlog, step_id):
    for step in backlog.get("steps", []):
        if step.get("step_id") == step_id:
            return step
    return None


def rollback_plan(workspace, step_id=None):
    workspace = Path(workspace).resolve()
    paths = brain_paths(workspace)
    active = load_json(paths["active_execution"], {})
    backlog = load_json(paths["backlog"], {"steps": []})
    resolved_step_id = step_id or active.get("step_id")
    step = active.get("step") if active.get("step_id") == resolved_step_id else find_step(backlog, resolved_step_id)
    if not step:
        return {"status": "error", "error": "No step found for rollback planning."}

    rollback = step.get("rollback_contract", {})
    method = rollback.get("method", "")
    candidate_files = step.get("candidate_files", [])
    executable = method == "restore file" and bool(candidate_files)
    return {
        "status": "planned",
        "step_id": resolved_step_id,
        "method": method,
        "candidate_files": candidate_files,
        "cost": rollback.get("cost"),
        "confidence": rollback.get("confidence"),
        "executable": executable,
        "command": ["git", "restore", "--"] + candidate_files if executable else None,
        "requires_confirm": True,
    }


def execute_rollback(workspace, step_id=None, confirm=False):
    plan = rollback_plan(workspace, step_id=step_id)
    if plan.get("status") != "planned":
        return plan
    if not plan.get("executable"):
        return {**plan, "status": "blocked", "error": "Rollback method is not allowlisted for automation."}
    if not confirm:
        return {**plan, "status": "needs_confirm", "error": "Pass --confirm to execute this rollback."}
    subprocess.run(plan["command"], cwd=workspace, check=True)
    return {**plan, "status": "rolled_back"}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plan or execute a guarded continuation rollback.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan = subparsers.add_parser("plan")
    plan.add_argument("--workspace", default=".")
    plan.add_argument("--step-id")
    execute = subparsers.add_parser("execute")
    execute.add_argument("--workspace", default=".")
    execute.add_argument("--step-id")
    execute.add_argument("--confirm", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.command == "plan":
            result = rollback_plan(args.workspace, step_id=args.step_id)
        else:
            result = execute_rollback(args.workspace, step_id=args.step_id, confirm=args.confirm)
    except Exception as exc:  # noqa: BLE001 - machine-readable CLI error.
        write_json({"status": "error", "error": str(exc)})
        return 1
    write_json(result)
    return 0 if result.get("status") in {"planned", "rolled_back"} else 2


if __name__ == "__main__":
    sys.exit(main())
