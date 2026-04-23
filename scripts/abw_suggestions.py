import json
from pathlib import Path

import abw_i18n


ACTION_LABELS = {
    "audit system": "Audit system",
    "coverage": "Check knowledge coverage",
    "help": "Show help",
    "improve knowledge base": "Improve knowledge base",
    "ingest more knowledge": "Ingest more knowledge",
    "ingest raw/<file>": "Ingest raw file",
    "review drafts": "Review drafts",
}


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def draft_total(workspace):
    queue = load_json(Path(workspace) / ".brain" / "ingest_queue.json", {"items": []}) or {"items": []}
    return sum(1 for item in queue.get("items", []) if item.get("status") == "review_needed")


def coverage_ratio(workspace):
    report = load_json(Path(workspace) / ".brain" / "coverage_report.json", {}) or {}
    try:
        return float(report.get("coverage_ratio"))
    except (TypeError, ValueError):
        return None


def fail_rate(workspace):
    rows = load_jsonl(Path(workspace) / ".brain" / "query_deep_runs.jsonl")
    if not rows:
        return None
    fail_count = 0
    for row in rows:
        result = row.get("result") or {}
        if result.get("status") == "insufficient_evidence":
            fail_count += 1
    return fail_count / len(rows) if rows else None


def raw_file_count(workspace):
    raw_dir = Path(workspace) / "raw"
    if not raw_dir.exists():
        return 0
    return len([path for path in raw_dir.rglob("*") if path.is_file()])


def label_for_command(command, workspace="."):
    command = str(command or "").strip()
    return abw_i18n.action_label(command, workspace=workspace)


def normalize_next_action(action, workspace="."):
    if isinstance(action, dict):
        command = str(action.get("command") or "").strip()
        if not command:
            return None
        label = str(action.get("label") or "").strip() or label_for_command(command, workspace=workspace)
        return {
            "label": label,
            "command": command,
        }

    command = str(action or "").strip()
    if not command:
        return None
    return {
        "label": label_for_command(command, workspace=workspace),
        "command": command,
    }


def normalize_next_actions(actions, workspace="."):
    normalized = []
    seen = set()
    for action in actions or []:
        item = normalize_next_action(action, workspace=workspace)
        if not item:
            continue
        command = item["command"]
        if command in seen:
            continue
        seen.add(command)
        normalized.append(item)
    return normalized


def suggest_next_actions(workspace):
    workspace = str(workspace or ".")
    actions = []
    pending_drafts = draft_total(workspace)
    current_coverage = coverage_ratio(workspace)
    current_fail_rate = fail_rate(workspace)
    raw_count = raw_file_count(workspace)

    if pending_drafts > 0:
        actions.append("review drafts")
    if current_coverage is not None and current_coverage < 0.6:
        actions.append("ingest more knowledge")
    if current_fail_rate is not None and current_fail_rate > 0.3:
        actions.append("improve knowledge base")
    if raw_count > 0 and pending_drafts == 0:
        actions.append("ingest raw/<file>")
    if not actions:
        actions.extend(["help", "audit system"])

    return normalize_next_actions(actions, workspace=workspace)
