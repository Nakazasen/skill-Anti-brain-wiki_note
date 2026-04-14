import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import continuation_gate


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))


def latest_claims(rows):
    claims = {}
    for row in rows:
        key = (row.get("model_id"), row.get("step_id"))
        if row.get("event") == "claimed":
            claims[key] = row
        elif row.get("event") == "released":
            claims.pop(key, None)
    return list(claims.values())


def overlaps(a, b):
    return bool(set(a or []) & set(b or []))


def claim_step(workspace, model_id, step_id=None):
    workspace = Path(workspace).resolve()
    brain = workspace / ".brain"
    claims_path = brain / "model_claims.jsonl"
    gate = continuation_gate.evaluate_workspace(workspace, step_id=step_id)
    selected = gate.get("selected")
    if not selected:
        return {"status": "blocked", "reason": "no claimable gated step", "gate": gate}
    resolved_step_id = selected["step_id"]
    backlog = continuation_gate.load_workspace(workspace)["backlog"]
    step = next((s for s in backlog.get("steps", []) if s.get("step_id") == resolved_step_id), {})
    files = step.get("candidate_files", [])
    active_claims = latest_claims(load_jsonl(claims_path))
    conflicts = [
        claim for claim in active_claims
        if claim.get("model_id") != model_id and overlaps(claim.get("candidate_files"), files)
    ]
    if conflicts:
        return {"status": "conflict", "step_id": resolved_step_id, "conflicts": conflicts}
    row = {
        "event": "claimed",
        "model_id": model_id,
        "step_id": resolved_step_id,
        "candidate_files": files,
        "timestamp": now_iso(),
    }
    append_jsonl(claims_path, row)
    return {"status": "claimed", "claim": row}


def release_step(workspace, model_id, step_id):
    workspace = Path(workspace).resolve()
    row = {
        "event": "released",
        "model_id": model_id,
        "step_id": step_id,
        "timestamp": now_iso(),
    }
    append_jsonl(workspace / ".brain" / "model_claims.jsonl", row)
    return {"status": "released", "release": row}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Coordinate continuation work across multiple models.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    claim = subparsers.add_parser("claim")
    claim.add_argument("--workspace", default=".")
    claim.add_argument("--model-id", required=True)
    claim.add_argument("--step-id")
    release = subparsers.add_parser("release")
    release.add_argument("--workspace", default=".")
    release.add_argument("--model-id", required=True)
    release.add_argument("--step-id", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command == "claim":
            result = claim_step(args.workspace, args.model_id, step_id=args.step_id)
        else:
            result = release_step(args.workspace, args.model_id, args.step_id)
    except Exception as exc:  # noqa: BLE001 - machine-readable CLI error.
        write_json({"status": "error", "error": str(exc)})
        return 1
    write_json(result)
    return 0 if result.get("status") in {"claimed", "released"} else 2


if __name__ == "__main__":
    sys.exit(main())
