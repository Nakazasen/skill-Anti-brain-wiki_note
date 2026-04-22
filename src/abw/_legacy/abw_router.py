import json
from datetime import datetime, timezone
from pathlib import Path

import intent_matcher


SUPPORTED_LANES = intent_matcher.supported_lanes()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def route_log_path(workspace="."):
    return Path(workspace) / ".brain" / "route_log.jsonl"


def append_route_log(workspace, payload):
    path = route_log_path(workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def log_route_decision(workspace, task, route, *, event="selected", details=None):
    payload = {
        "timestamp": now_iso(),
        "event": event,
        "task": str(task or ""),
        "route": route or {},
    }
    if details:
        payload["details"] = details
    append_route_log(workspace, payload)
    return payload


def load_gaps(workspace="."):
    path = Path(workspace) / ".brain" / "knowledge_gaps.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    return payload.get("gaps", [])


def matching_gap_count(task, workspace="."):
    normalized_task = intent_matcher.normalize_input(task)
    if not normalized_task:
        return 0
    return sum(
        1
        for gap in load_gaps(workspace)
        if gap.get("status") == "open"
        and intent_matcher.normalize_input(gap.get("query") or "") == normalized_task
    )


def normalize_provided_route(route):
    if not isinstance(route, dict):
        return None

    lane = str(route.get("lane") or "").strip().lower()
    intent = str(route.get("intent") or "").strip().lower()
    reason = str(route.get("reason") or "").strip()
    fallback_allowed = bool(route.get("fallback_allowed", True))
    params = dict(route.get("params") or {})

    if lane in SUPPORTED_LANES:
        return {
            "intent": intent or lane,
            "lane": lane,
            "reason": reason or "caller-provided route",
            "fallback_allowed": fallback_allowed,
            "params": params,
            "source": "provided_route",
        }

    if intent in {"knowledge", "query"}:
        return {
            "intent": "query",
            "lane": "query",
            "reason": reason or "caller-provided knowledge intent",
            "fallback_allowed": fallback_allowed,
            "params": params,
            "source": "provided_route",
        }

    if intent in {"knowledge_deep", "query_deep"}:
        return {
            "intent": "query_deep",
            "lane": "query_deep",
            "reason": reason or "caller-provided deep knowledge intent",
            "fallback_allowed": fallback_allowed,
            "params": params,
            "source": "provided_route",
        }

    if intent in SUPPORTED_LANES:
        return {
            "intent": intent,
            "lane": intent,
            "reason": reason or "caller-provided lane intent",
            "fallback_allowed": fallback_allowed,
            "params": params,
            "source": "provided_route",
        }

    return None


def build_route(rule, *, source="router"):
    return {
        "intent": rule["intent"],
        "lane": rule["lane"],
        "reason": rule["reason"],
        "fallback_allowed": bool(rule.get("fallback_allowed", True)),
        "params": dict(rule.get("params") or {}),
        "source": source,
    }


def route_request(task, *, workspace=".", route=None):
    provided = normalize_provided_route(route)
    if provided:
        return provided

    normalized_task = intent_matcher.normalize_input(task)
    if not normalized_task:
        return {
            "intent": "query",
            "lane": "query",
            "reason": "empty task defaults to query safety path",
            "fallback_allowed": True,
            "params": {},
            "source": "router",
        }

    matched = intent_matcher.match_intent(task)
    if matched:
        return build_route(matched)

    repeated_gap_count = matching_gap_count(task, workspace=workspace)
    if repeated_gap_count >= 2:
        return {
            "intent": "bootstrap",
            "lane": "bootstrap",
            "reason": f"repeated unresolved knowledge gaps for the same request ({repeated_gap_count} open)",
            "fallback_allowed": True,
            "params": {},
            "source": "router",
        }

    if intent_matcher.looks_like_deep_query(task):
        return {
            "intent": "query_deep",
            "lane": "query_deep",
            "reason": "analysis-style query detected",
            "fallback_allowed": True,
            "params": {},
            "source": "router",
        }

    if intent_matcher.looks_like_query(task):
        return {
            "intent": "query",
            "lane": "query",
            "reason": "question-style query detected",
            "fallback_allowed": True,
            "params": {},
            "source": "router",
        }

    return {
        "intent": "legacy_execution",
        "lane": "legacy_execution",
        "reason": "preserve current bounded execution path for non-question tasks",
        "fallback_allowed": False,
        "params": {},
        "source": "router",
    }
