import argparse
import json
import sys
from pathlib import Path

import continuation_gate


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def write_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def count_by_status(steps):
    counts = {}
    for step in steps:
        status = step.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def dependency_summary(steps, completed_steps, step_history):
    accepted = set(completed_steps or [])
    for row in step_history:
        if row.get("accepted") is True:
            accepted.add(row.get("step_id"))
    blocked = []
    for step in steps:
        missing = [dep for dep in step.get("depends_on", []) if dep not in accepted]
        if missing and step.get("status") == "pending":
            blocked.append({"step_id": step.get("step_id"), "missing": missing})
    return {"blocked_count": len(blocked), "blocked_steps": blocked}


def active_model_claims(rows):
    claims = {}
    for row in rows:
        key = (row.get("model_id"), row.get("step_id"))
        if row.get("event") == "claimed":
            claims[key] = row
        elif row.get("event") == "released":
            claims.pop(key, None)
    return list(claims.values())


def evaluate_status(workspace):
    workspace = Path(workspace).resolve()
    brain = workspace / ".brain"
    state = load_json(brain / "resume_state.json", {})
    backlog = load_json(brain / "continuation_backlog.json", {"steps": []})
    active_execution = load_json(brain / "active_execution.json", None)
    step_history = load_jsonl(brain / "step_history.jsonl")
    handover_log = load_jsonl(brain / "handover_log.jsonl")
    model_claims = load_jsonl(brain / "model_claims.jsonl")
    steps = backlog.get("steps", [])

    try:
        gate_result = continuation_gate.evaluate_workspace(workspace)
    except Exception as exc:  # noqa: BLE001 - status should degrade to diagnostic output.
        gate_result = {"status": "error", "error": str(exc), "selected": None}

    selected = gate_result.get("selected") or {}
    required_approvals = selected.get("required_approvals", [])
    warnings = selected.get("warnings", [])
    last_history = step_history[-1] if step_history else None
    last_handover = handover_log[-1] if handover_log else None

    health = "ready"
    reasons = []
    if active_execution:
        health = "active"
        reasons.append("active execution in progress")
    elif gate_result.get("status") == "blocked":
        health = "blocked"
        reasons.append("no allowed next safe step")
    elif required_approvals:
        health = "needs_approval"
        reasons.append("selected step requires approval")
    elif gate_result.get("status") == "error":
        health = "error"
        reasons.append(gate_result.get("error", "gate error"))

    return {
        "status": "ok",
        "health": health,
        "health_reasons": reasons,
        "project_id": state.get("project_id"),
        "phase": state.get("phase"),
        "current_objective": state.get("current_objective"),
        "active_step": state.get("active_step"),
        "backlog": {
            "total": len(steps),
            "by_status": count_by_status(steps),
        },
        "dependencies": dependency_summary(steps, state.get("completed_steps"), step_history),
        "model_claims": {
            "active_count": len(active_model_claims(model_claims)),
            "active": active_model_claims(model_claims),
        },
        "next_safe_step": {
            "status": gate_result.get("status"),
            "step_id": selected.get("step_id"),
            "permission_class": selected.get("permission_class"),
            "safety_score": selected.get("safety_score"),
            "required_approvals": required_approvals,
            "warnings": warnings,
        },
        "active_execution": active_execution,
        "last_step_history": last_history,
        "last_handover_event": last_handover,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Report Continuation Runtime health.")
    parser.add_argument("--workspace", default=".", help="Workspace root containing .brain/")
    args = parser.parse_args(argv)

    try:
        result = evaluate_status(args.workspace)
    except Exception as exc:  # noqa: BLE001 - CLI should return machine-readable error.
        write_json({"status": "error", "error": str(exc)})
        return 1

    write_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
