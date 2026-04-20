import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import abw_version


SNAPSHOT_LOG = ".brain/system_snapshots.jsonl"
DATA_LAYERS = ("raw", "processed", "drafts", "wiki")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path, default=None):
    path = Path(path)
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


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


def append_jsonl(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def count_files(path):
    path = Path(path)
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def file_counts(workspace):
    root = Path(workspace)
    return {name: count_files(root / name) for name in DATA_LAYERS}


def usage_summary(workspace):
    rows = load_jsonl(Path(workspace) / ".brain" / "route_log.jsonl")
    counts = Counter()
    for row in rows:
        route = row.get("route") or {}
        lane = str(route.get("lane") or "").strip()
        if lane:
            counts[lane] += 1
    return {
        "route_total": len(rows),
        "routes_by_lane": dict(sorted(counts.items())),
    }


def health_summary(workspace):
    rows = load_jsonl(Path(workspace) / ".brain" / "acceptance_log.jsonl")
    accepted = sum(1 for row in rows if row.get("accepted") is True)
    return {
        "acceptance_total": len(rows),
        "accepted": accepted,
        "acceptance_ratio": round(accepted / len(rows), 4) if rows else None,
    }


def coverage_summary(workspace):
    payload = load_json(Path(workspace) / ".brain" / "coverage_report.json", {}) or {}
    return {
        "coverage_ratio": payload.get("coverage_ratio"),
        "total_questions": int(payload.get("total_questions", 0) or 0),
        "success": int(payload.get("success", 0) or 0),
        "weak": int(payload.get("weak", 0) or 0),
        "fail": int(payload.get("fail", 0) or 0),
        "top_gaps": payload.get("top_gaps", []) if isinstance(payload.get("top_gaps", []), list) else [],
    }


def ingest_summary(workspace):
    payload = load_json(Path(workspace) / ".brain" / "ingest_queue.json", {"items": []}) or {"items": []}
    items = payload.get("items", [])
    if not isinstance(items, list):
        items = []
    return {
        "queue_total": len(items),
        "pending_drafts": sum(1 for item in items if item.get("status") == "review_needed"),
        "approved_drafts": sum(1 for item in items if item.get("status") == "approved"),
    }


def snapshot_path(workspace):
    return Path(workspace) / SNAPSHOT_LOG


def capture_snapshot(workspace="."):
    workspace = str(workspace or ".")
    snapshot = {
        "timestamp": now_iso(),
        "version": abw_version.resolve_version(workspace),
        "health": health_summary(workspace),
        "usage": usage_summary(workspace),
        "coverage": coverage_summary(workspace),
        "ingest": ingest_summary(workspace),
        "files": file_counts(workspace),
    }
    path = snapshot_path(workspace)
    append_jsonl(path, snapshot)
    snapshot["snapshot_file"] = str(path)
    return snapshot


def read_snapshots(workspace=".", limit=10):
    rows = load_jsonl(snapshot_path(workspace))
    if limit is None:
        return rows
    return rows[-int(limit):]


def numeric_delta(before, after):
    if before is None or after is None:
        return None
    try:
        return after - before
    except TypeError:
        return None


def analyze_change(label, before, after, good_when):
    delta = numeric_delta(before, after)
    if delta is None or delta == 0:
        state = "neutral"
    elif (good_when == "up" and delta > 0) or (good_when == "down" and delta < 0):
        state = "good"
    else:
        state = "warning"
    return {
        "metric": label,
        "before": before,
        "after": after,
        "delta": delta,
        "state": state,
    }


def build_trend(snapshots):
    if len(snapshots) < 2:
        return {
            "status": "insufficient_history",
            "summary": "Need at least 2 snapshots to compute trend.",
            "changes": [],
            "findings": ["Chưa đủ lịch sử. Chạy system trend thêm lần nữa sau khi hệ thay đổi."],
        }

    first = snapshots[0]
    last = snapshots[-1]
    changes = [
        analyze_change(
            "coverage_ratio",
            (first.get("coverage") or {}).get("coverage_ratio"),
            (last.get("coverage") or {}).get("coverage_ratio"),
            "up",
        ),
        analyze_change(
            "fail",
            (first.get("coverage") or {}).get("fail"),
            (last.get("coverage") or {}).get("fail"),
            "down",
        ),
        analyze_change(
            "pending_drafts",
            (first.get("ingest") or {}).get("pending_drafts"),
            (last.get("ingest") or {}).get("pending_drafts"),
            "down",
        ),
    ]

    findings = []
    for item in changes:
        if item["metric"] == "coverage_ratio" and item["state"] == "good":
            findings.append("Coverage tăng: tốt.")
        if item["metric"] == "fail" and item["state"] == "good":
            findings.append("Fail giảm: tốt.")
        if item["metric"] == "pending_drafts" and item["state"] == "warning":
            findings.append("Draft pending tăng: có nguy cơ nghẽn review.")

    if not findings:
        findings.append("Chưa thấy xu hướng mạnh từ các snapshot hiện có.")

    warning_count = sum(1 for item in changes if item["state"] == "warning")
    status = "watch" if warning_count else "ok"
    return {
        "status": status,
        "summary": f"Compared {len(snapshots)} snapshots from {first.get('timestamp')} to {last.get('timestamp')}.",
        "changes": changes,
        "findings": findings,
    }


def render_trend(report):
    lines = [
        "ABW System Trend",
        report["summary"],
        "",
        "Changes:",
    ]
    for item in report.get("changes", []):
        lines.append(
            f"- {item['metric']}: {item['before']} -> {item['after']} "
            f"(delta={item['delta']}, state={item['state']})"
        )
    if not report.get("changes"):
        lines.append("- none")

    lines.append("")
    lines.append("Findings:")
    for finding in report.get("findings", []):
        lines.append(f"- {finding}")
    return "\n".join(lines)


def run_trend(workspace=".", limit=10, capture_current=True):
    if capture_current:
        capture_snapshot(workspace)
    snapshots = read_snapshots(workspace, limit=limit)
    trend = build_trend(snapshots)
    trend["snapshot_count"] = len(snapshots)
    trend["rendered"] = render_trend(trend)
    return trend
