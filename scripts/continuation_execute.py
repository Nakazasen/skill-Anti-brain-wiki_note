import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import continuation_gate


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def find_step(backlog, step_id):
    for step in backlog.get("steps", []):
        if step.get("step_id") == step_id:
            return step
    return None


def update_step_status(backlog, step_id, status):
    step = find_step(backlog, step_id)
    if step is not None:
        step["status"] = status
    return step


def brain_paths(workspace):
    brain = Path(workspace) / ".brain"
    return {
        "brain": brain,
        "resume_state": brain / "resume_state.json",
        "backlog": brain / "continuation_backlog.json",
        "handover_log": brain / "handover_log.jsonl",
        "step_history": brain / "step_history.jsonl",
        "active_execution": brain / "active_execution.json",
    }


def prepare_execution(workspace, step_id=None, approved=False, approval_note=None, session_id=None):
    workspace = Path(workspace).resolve()
    paths = brain_paths(workspace)
    gate_result = continuation_gate.evaluate_workspace(workspace, step_id=step_id)
    selected = gate_result.get("selected")
    if not selected:
        return {
            "status": "blocked",
            "reason": "no allowed continuation step",
            "gate": gate_result,
        }

    approvals = selected.get("required_approvals", [])
    if approvals and not approved:
        return {
            "status": "approval_required",
            "step_id": selected.get("step_id"),
            "required_approvals": approvals,
            "gate": gate_result,
        }

    state = load_json(paths["resume_state"], {})
    backlog = load_json(paths["backlog"], {"steps": []})
    step = find_step(backlog, selected["step_id"])
    if step is None:
        return {
            "status": "error",
            "error": f"Selected step not found in backlog: {selected['step_id']}",
            "gate": gate_result,
        }

    timestamp = now_iso()
    update_step_status(backlog, selected["step_id"], "active")
    state["active_step"] = selected["step_id"]
    state["last_updated_at"] = timestamp

    execution = {
        "status": "prepared",
        "step_id": selected["step_id"],
        "prepared_at": timestamp,
        "session_id": session_id,
        "approved": bool(approved),
        "approval_note": approval_note,
        "gate": selected,
        "step": step,
    }

    save_json(paths["resume_state"], state)
    save_json(paths["backlog"], backlog)
    save_json(paths["active_execution"], execution)
    append_jsonl(
        paths["handover_log"],
        {
            "event": "step_started",
            "step_id": selected["step_id"],
            "outcome": "active",
            "session_id": session_id,
            "timestamp": timestamp,
            "approvals": approvals,
        },
    )

    return execution


def record_execution(
    workspace,
    step_id,
    outcome,
    changed_files=None,
    test_result=None,
    errors_introduced=0,
    session_id=None,
):
    workspace = Path(workspace).resolve()
    paths = brain_paths(workspace)
    state = load_json(paths["resume_state"], {})
    backlog = load_json(paths["backlog"], {"steps": []})
    active_execution = load_json(paths["active_execution"], {})

    timestamp = now_iso()
    changed_files = changed_files or []
    test_result = test_result if test_result is not None else None

    if not active_execution:
        return {
            "status": "error",
            "error": "No active execution found. Run prepare before record.",
        }

    if active_execution.get("step_id") != step_id:
        return {
            "status": "error",
            "error": f"Active execution is {active_execution.get('step_id')}, not {step_id}",
        }

    step_status = "completed" if outcome == "success" else outcome
    update_step_status(backlog, step_id, step_status)

    completed_steps = state.setdefault("completed_steps", [])
    if outcome == "success":
        state["last_completed_step"] = step_id
        if step_id not in completed_steps:
            completed_steps.append(step_id)
    state["active_step"] = None
    state["last_updated_at"] = timestamp

    history_row = {
        "step_id": step_id,
        "outcome": outcome,
        "changed_files": changed_files,
        "test_result": test_result,
        "errors_introduced": int(errors_introduced),
        "executed_at": timestamp,
    }

    append_jsonl(paths["step_history"], history_row)
    append_jsonl(
        paths["handover_log"],
        {
            "event": "step_completed",
            "step_id": step_id,
            "outcome": outcome,
            "session_id": session_id,
            "timestamp": timestamp,
        },
    )
    save_json(paths["resume_state"], state)
    save_json(paths["backlog"], backlog)
    if paths["active_execution"].exists():
        paths["active_execution"].unlink()

    return {
        "status": "recorded",
        "step_id": step_id,
        "outcome": outcome,
        "history": history_row,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare or record a governed continuation execution.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Run gate and mark the selected step active.")
    prepare.add_argument("--workspace", default=".")
    prepare.add_argument("--step-id")
    prepare.add_argument("--approved", action="store_true", help="Confirm user approval for required approvals.")
    prepare.add_argument("--approval-note")
    prepare.add_argument("--session-id")

    record = subparsers.add_parser("record", help="Record the outcome of an executed step.")
    record.add_argument("--workspace", default=".")
    record.add_argument("--step-id", required=True)
    record.add_argument("--outcome", required=True, choices=["success", "partial", "failed"])
    record.add_argument("--changed-file", action="append", default=[])
    record.add_argument("--test-result", choices=["pass", "fail", "skipped", "null"], default="null")
    record.add_argument("--errors-introduced", type=int, default=0)
    record.add_argument("--session-id")

    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_execution(
                args.workspace,
                step_id=args.step_id,
                approved=args.approved,
                approval_note=args.approval_note,
                session_id=args.session_id,
            )
        else:
            result = record_execution(
                args.workspace,
                args.step_id,
                args.outcome,
                changed_files=args.changed_file,
                test_result=None if args.test_result == "null" else args.test_result,
                errors_introduced=args.errors_introduced,
                session_id=args.session_id,
            )
    except Exception as exc:  # noqa: BLE001 - CLI must return machine-readable errors.
        write_json({"status": "error", "error": str(exc)})
        return 1

    write_json(result)
    if result.get("status") in {"prepared", "recorded"}:
        return 0
    if result.get("status") == "approval_required":
        return 3
    return 2


if __name__ == "__main__":
    sys.exit(main())
