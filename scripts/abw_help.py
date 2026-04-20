import json
from pathlib import Path

import abw_suggestions


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def count_files(path):
    path = Path(path)
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def ingest_queue(workspace):
    payload = load_json(Path(workspace) / ".brain" / "ingest_queue.json", {"items": []}) or {"items": []}
    items = payload.get("items", [])
    return items if isinstance(items, list) else []


def coverage_ratio(workspace):
    payload = load_json(Path(workspace) / ".brain" / "coverage_report.json", {}) or {}
    try:
        return float(payload.get("coverage_ratio"))
    except (TypeError, ValueError):
        return None


def build_state_snapshot(workspace):
    workspace = Path(workspace or ".")
    queue_items = ingest_queue(workspace)
    pending_drafts = [item for item in queue_items if item.get("status") == "review_needed"]
    approved_drafts = [item for item in queue_items if item.get("status") == "approved"]
    return {
        "raw_files": count_files(workspace / "raw"),
        "draft_files": count_files(workspace / "drafts"),
        "wiki_files": count_files(workspace / "wiki"),
        "queue_total": len(queue_items),
        "pending_drafts": len(pending_drafts),
        "approved_drafts": len(approved_drafts),
        "coverage_ratio": coverage_ratio(workspace),
    }


def format_coverage(value):
    if value is None:
        return "unknown"
    return f"{value:.2f}"


def situational_guidance(snapshot, next_actions):
    guidance = []
    if snapshot["raw_files"] == 0 and snapshot["wiki_files"] == 0 and snapshot["draft_files"] == 0:
        guidance.append("Chưa có dữ liệu tri thức. Bắt đầu bằng cách đưa tài liệu vào raw/ rồi chạy ingest.")
    if snapshot["pending_drafts"] > 0:
        guidance.append("Đang có bản nháp cần duyệt trước khi trở thành wiki tin cậy.")
    if snapshot["coverage_ratio"] is not None and snapshot["coverage_ratio"] < 0.6:
        guidance.append("Coverage đang thấp. Nên bổ sung hoặc chuẩn hóa thêm tri thức.")
    if snapshot["raw_files"] > 0 and snapshot["pending_drafts"] == 0 and snapshot["wiki_files"] == 0:
        guidance.append("Đã có raw nhưng chưa có wiki tin cậy. Hãy tạo draft ingest trước.")
    if not guidance and next_actions:
        guidance.append("Hệ đang có đủ dữ liệu cơ bản. Chọn một bước tiếp theo phù hợp.")
    return guidance


def minimal_commands(snapshot):
    commands = []
    if snapshot["raw_files"] > 0:
        commands.append("ingest raw/<file>")
    else:
        commands.append("thêm tài liệu vào raw/ rồi chạy ingest raw/<file>")
    if snapshot["pending_drafts"] > 0:
        commands.extend(["review drafts", "approve draft drafts/<file>"])
    if snapshot["wiki_files"] > 0:
        commands.append("hỏi trực tiếp")
    commands.extend(["coverage", "audit system"])

    deduped = []
    seen = set()
    for command in commands:
        if command in seen:
            continue
        seen.add(command)
        deduped.append(command)
    return deduped


def build_sections(snapshot, next_actions):
    guidance = situational_guidance(snapshot, next_actions)
    return [
        {
            "title": "Overview",
            "items": [
                f"raw_files: {snapshot['raw_files']}",
                f"draft_files: {snapshot['draft_files']}",
                f"wiki_files: {snapshot['wiki_files']}",
                f"pending_drafts: {snapshot['pending_drafts']}",
                f"coverage_ratio: {format_coverage(snapshot['coverage_ratio'])}",
            ],
        },
        {
            "title": "Next actions",
            "items": list(next_actions),
        },
        {
            "title": "Situational guidance",
            "items": guidance,
        },
        {
            "title": "Minimal commands",
            "items": minimal_commands(snapshot),
        },
    ]


def run(workspace="."):
    workspace = str(workspace or ".")
    snapshot = build_state_snapshot(workspace)
    next_actions = abw_suggestions.suggest_next_actions(workspace)
    sections = build_sections(snapshot, next_actions)
    return {
        "message": "Bạn có thể làm tiếp dựa trên trạng thái hiện tại:",
        "state_snapshot": snapshot,
        "sections": sections,
        "next_actions": next_actions,
    }
