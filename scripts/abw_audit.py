import ast
import json
from collections import Counter
from pathlib import Path


CORE_DATA_LAYERS = ("raw", "processed", "drafts", "wiki")


def read_text(path):
    return Path(path).read_text(encoding="utf-8-sig")


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


def discover_modules(workspace):
    scripts_dir = Path(workspace) / "scripts"
    if not scripts_dir.exists():
        return []
    return sorted(path.name for path in scripts_dir.glob("abw_*.py"))


def parse_execute_lane(runner_path):
    if not runner_path.exists():
        return []
    tree = ast.parse(read_text(runner_path))
    lanes = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "execute_lane":
            continue
        for child in ast.walk(node):
            if not isinstance(child, ast.Dict):
                continue
            for key in child.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    lanes.append(key.value)
    return sorted(set(lanes))


def parse_return_mappings(router_path):
    if not router_path.exists():
        return []
    tree = ast.parse(read_text(router_path))
    mappings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Return) or not isinstance(node.value, ast.Dict):
            continue
        payload = {}
        for key, value in zip(node.value.keys, node.value.values):
            if isinstance(key, ast.Constant) and isinstance(key.value, str) and isinstance(value, ast.Constant):
                payload[key.value] = value.value
        if payload.get("lane") or payload.get("intent"):
            mappings.append(
                {
                    "lane": payload.get("lane") or payload.get("intent") or "",
                    "intent": payload.get("intent") or payload.get("lane") or "",
                    "reason": payload.get("reason", ""),
                }
            )
    return mappings


def parse_intent_matcher_module(matcher_path):
    if not matcher_path.exists():
        return []
    tree = ast.parse(read_text(matcher_path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "INTENT_PATTERNS" for target in node.targets):
            continue
        try:
            rules = ast.literal_eval(node.value)
        except Exception:
            return []
        mappings = []
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            mappings.append(
                {
                    "lane": str(rule.get("lane") or rule.get("intent") or ""),
                    "intent": str(rule.get("intent") or rule.get("lane") or ""),
                    "reason": str(rule.get("reason") or ""),
                }
            )
        return mappings
    return []


def parse_router_intents(workspace):
    root = Path(workspace)
    mappings = []
    mappings.extend(parse_return_mappings(root / "scripts" / "abw_router.py"))
    mappings.extend(parse_intent_matcher_module(root / "scripts" / "intent_matcher.py"))
    deduped = {}
    for item in mappings:
        key = (item["lane"], item["intent"])
        if any(key):
            deduped[key] = item
    return sorted(deduped.values(), key=lambda item: (item["lane"], item["intent"]))


def classify_log_type(path):
    stem = path.stem.lower()
    for token in ("route", "query", "ingest", "coverage", "acceptance", "review", "health", "resume"):
        if token in stem:
            return token
    return "generic"


def discover_logs(workspace):
    brain_dir = Path(workspace) / ".brain"
    if not brain_dir.exists():
        return []
    logs = []
    for path in sorted(brain_dir.iterdir()):
        if not path.is_file() or path.suffix not in {".json", ".jsonl"}:
            continue
        logs.append(
            {
                "name": path.name,
                "type": classify_log_type(path),
                "rows": len(load_jsonl(path)) if path.suffix == ".jsonl" else None,
            }
        )
    return logs


def discover_data_layers(workspace):
    root = Path(workspace)
    layers = []
    for name in CORE_DATA_LAYERS:
        path = root / name
        exists = path.exists() and path.is_dir()
        file_count = len([item for item in path.rglob("*") if item.is_file()]) if exists else 0
        layers.append({"name": name, "exists": exists, "file_count": file_count})
    return layers


def discover_features(workspace, modules):
    scripts_dir = Path(workspace) / "scripts"
    features = []
    for module_name in modules:
        path = scripts_dir / module_name
        if not path.exists():
            continue
        try:
            tree = ast.parse(read_text(path))
        except SyntaxError:
            continue
        functions = sorted(node.name for node in tree.body if isinstance(node, ast.FunctionDef))
        features.append({"module": module_name, "functions": functions})
    return features


def discover_system(workspace):
    workspace = str(workspace or ".")
    modules = discover_modules(workspace)
    return {
        "modules": modules,
        "lanes": parse_execute_lane(Path(workspace) / "scripts" / "abw_runner.py"),
        "intent_mapping": parse_router_intents(workspace),
        "logs": discover_logs(workspace),
        "data_layers": discover_data_layers(workspace),
        "features": discover_features(workspace, modules),
    }


def lane_usage_from_route_log(workspace):
    counts = Counter()
    for row in load_jsonl(Path(workspace) / ".brain" / "route_log.jsonl"):
        route = row.get("route") or {}
        lane = str(route.get("lane") or "").strip()
        if lane:
            counts[lane] += 1
    return dict(counts)


def detect_review_bottleneck(workspace):
    queue = load_json(Path(workspace) / ".brain" / "ingest_queue.json", {"items": []}) or {"items": []}
    pending = [item for item in queue.get("items", []) if item.get("status") == "review_needed"]
    if len(pending) >= 3:
        return {"type": "review_bottleneck", "detail": f"Có {len(pending)} draft đang chờ duyệt."}
    return None


def detect_knowledge_gap(workspace):
    fail_count = 0
    for row in load_jsonl(Path(workspace) / ".brain" / "query_deep_runs.jsonl"):
        result = row.get("result") or {}
        if result.get("status") == "insufficient_evidence":
            fail_count += 1
    if fail_count:
        return {"type": "knowledge_gap", "detail": f"Có {fail_count} deep query thiếu bằng chứng."}
    return None


def detect_trust_issue(workspace):
    rows = load_jsonl(Path(workspace) / ".brain" / "acceptance_log.jsonl")
    if not rows:
        return None
    accepted = sum(1 for row in rows if row.get("accepted") is True)
    ratio = accepted / len(rows) if rows else 0.0
    if ratio < 0.5:
        return {"type": "low_runner_enforced_rate", "detail": f"Tỷ lệ accepted chỉ là {ratio:.2f}."}
    return None


def detect_missing_usage(system_map, lane_usage):
    return [lane for lane in system_map.get("lanes", []) if lane_usage.get(lane, 0) == 0]


def analyze_system(system_map, workspace="."):
    workspace = str(workspace or ".")
    lane_usage = lane_usage_from_route_log(workspace)
    bottlenecks = []
    for detector in (detect_review_bottleneck, detect_knowledge_gap, detect_trust_issue):
        finding = detector(workspace)
        if finding:
            bottlenecks.append(finding)

    missing_parts = []
    unused_lanes = detect_missing_usage(system_map, lane_usage)
    if unused_lanes:
        missing_parts.append(
            {
                "type": "feature_exists_but_unused",
                "detail": f"Các lane chưa thấy usage: {', '.join(unused_lanes)}",
            }
        )

    recommendations = []
    if any(item["type"] == "review_bottleneck" for item in bottlenecks):
        recommendations.append("Ưu tiên review drafts để giải phóng hàng chờ tri thức.")
    if any(item["type"] == "knowledge_gap" for item in bottlenecks):
        recommendations.append("Bổ sung raw hoặc wiki cho các câu hỏi còn thiếu bằng chứng.")
    if any(item["type"] == "low_runner_enforced_rate" for item in bottlenecks):
        recommendations.append("Kiểm tra lại các luồng acceptance để tăng tỷ lệ output được chấp nhận.")
    if not recommendations:
        recommendations.append("Tiếp tục theo dõi route_log và acceptance_log để giữ hệ ổn định.")

    return {
        "lane_usage": sorted(
            [{"lane": lane, "count": count} for lane, count in lane_usage.items()],
            key=lambda item: (-item["count"], item["lane"]),
        ),
        "unused_lanes": unused_lanes,
        "bottlenecks": bottlenecks,
        "missing_parts": missing_parts,
        "recommendations": recommendations,
    }


def render_report(system_map, analysis):
    lines = [
        "📋 Audit toàn hệ ABW",
        "",
        "🔎 Hệ đang có:",
        f"- {len(system_map.get('lanes', []))} lane",
        f"- {len(system_map.get('modules', []))} module",
        f"- {sum(1 for layer in system_map.get('data_layers', []) if layer.get('exists'))} data layer",
        "",
        "📊 Hoạt động:",
    ]
    if analysis.get("lane_usage"):
        for item in analysis["lane_usage"]:
            lines.append(f"- {item['lane']}: dùng {item['count']} lần")
    else:
        lines.append("- Chưa có route log để đo usage lane.")

    if analysis.get("unused_lanes"):
        lines.append(f"- Lane chưa thấy usage: {', '.join(analysis['unused_lanes'])}")

    lines.extend(["", "⚠️ Điểm nghẽn:"])
    if analysis.get("bottlenecks"):
        for item in analysis["bottlenecks"]:
            lines.append(f"- {item['detail']}")
    else:
        lines.append("- Chưa phát hiện điểm nghẽn rõ ràng từ log hiện có.")

    if analysis.get("missing_parts"):
        for item in analysis["missing_parts"]:
            lines.append(f"- {item['detail']}")

    lines.extend(["", "👉 Bạn nên làm tiếp:"])
    for item in analysis.get("recommendations", []):
        lines.append(f"- {item}")
    return "\n".join(lines)


def run_audit(workspace="."):
    system_map = discover_system(workspace)
    analysis = analyze_system(system_map, workspace=workspace)
    return {
        "system_map": system_map,
        "analysis": analysis,
        "report": render_report(system_map, analysis),
    }
