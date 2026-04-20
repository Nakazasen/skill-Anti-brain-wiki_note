import json
from pathlib import Path


ACTION_LABELS = {
    "audit system": "Audit hệ thống",
    "coverage": "Kiểm tra coverage tri thức",
    "help": "Xem hướng dẫn",
    "improve knowledge base": "Cải thiện kho tri thức",
    "ingest more knowledge": "Nạp thêm tri thức",
    "ingest raw/<file>": "Nạp tài liệu raw",
    "review drafts": "Duyệt các bản nháp",
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


def label_for_command(command):
    command = str(command or "").strip()
    return ACTION_LABELS.get(command, command)


def normalize_next_action(action):
    if isinstance(action, dict):
        command = str(action.get("command") or "").strip()
        if not command:
            return None
        label = str(action.get("label") or "").strip() or label_for_command(command)
        return {
            "label": label,
            "command": command,
        }

    command = str(action or "").strip()
    if not command:
        return None
    return {
        "label": label_for_command(command),
        "command": command,
    }


def normalize_next_actions(actions):
    normalized = []
    seen = set()
    for action in actions or []:
        item = normalize_next_action(action)
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

    return normalize_next_actions(actions)
