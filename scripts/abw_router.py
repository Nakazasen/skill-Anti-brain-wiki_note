import json
from datetime import datetime, timezone
from pathlib import Path


SUPPORTED_LANES = {
    "coverage",
    "query",
    "query_deep",
    "resume",
    "bootstrap",
    "ingest",
    "legacy_execution",
}
QUERY_INTENTS = {"knowledge", "query"}
DEEP_INTENTS = {"knowledge_deep", "query_deep"}
RESUME_TOKENS = (
    "/abw-resume",
    "resume",
    "continue",
    "pick up where we left off",
    "pick up previous work",
    "continue prior work",
    "continue previous work",
    "tiep tuc",
    "dang do",
)
INGEST_TOKENS = (
    "/abw-ingest",
    "ingest",
    "add to wiki",
    "process source",
    "process raw",
    "review raw",
    "queue source",
)
BOOTSTRAP_TOKENS = (
    "/abw-bootstrap",
    "bootstrap",
    "greenfield",
    "new project",
    "new idea",
    "start from scratch",
    "project setup",
    "setup project",
)
COVERAGE_TOKENS = (
    "coverage",
    "knowledge coverage",
    "gap report",
    "coverage report",
    "missing knowledge",
    "top gaps",
)
DEEP_QUERY_TOKENS = (
    "compare",
    "comparison",
    "tradeoff",
    "trade-off",
    "versus",
    " vs ",
    "root cause",
    "rca",
    "architecture",
    "contradiction",
    "pros and cons",
)
QUERY_TOKENS = (
    "what is",
    "explain",
    "why",
    "how",
    "which",
    "where",
    "who",
    "la gi",
    "giai thich",
    "tra cuu",
    "tim trong wiki",
)


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


def _normalize_provided_route(route):
    if not isinstance(route, dict):
        return None

    lane = str(route.get("lane") or "").strip().lower()
    intent = str(route.get("intent") or "").strip().lower()
    reason = str(route.get("reason") or "").strip()
    fallback_allowed = bool(route.get("fallback_allowed", True))

    if lane in SUPPORTED_LANES:
        return {
            "intent": intent or lane,
            "lane": lane,
            "reason": reason or "caller-provided route",
            "fallback_allowed": fallback_allowed,
            "source": "provided_route",
        }

    if intent in QUERY_INTENTS:
        return {
            "intent": "query",
            "lane": "query",
            "reason": reason or "caller-provided knowledge intent",
            "fallback_allowed": fallback_allowed,
            "source": "provided_route",
        }

    if intent in DEEP_INTENTS:
        return {
            "intent": "query_deep",
            "lane": "query_deep",
            "reason": reason or "caller-provided deep knowledge intent",
            "fallback_allowed": fallback_allowed,
            "source": "provided_route",
        }

    if intent in {"resume", "bootstrap", "ingest", "coverage"}:
        return {
            "intent": intent,
            "lane": intent,
            "reason": reason or "caller-provided lane intent",
            "fallback_allowed": fallback_allowed,
            "source": "provided_route",
        }

    return None


def _task_has_any(task, tokens):
    lowered = str(task or "").lower()
    return any(token in lowered for token in tokens)


def _looks_like_deep_query(task):
    lowered = str(task or "").lower()
    if _task_has_any(lowered, DEEP_QUERY_TOKENS):
        return True
    if lowered.count("?") >= 2:
        return True
    if " and " in lowered and any(token in lowered for token in QUERY_TOKENS):
        return True
    return False


def _looks_like_query(task):
    lowered = str(task or "").lower()
    if _task_has_any(lowered, QUERY_TOKENS):
        return True
    return lowered.endswith("?")


def _raw_source_mentioned(task):
    lowered = str(task or "").lower()
    if "raw/" in lowered or "raw\\" in lowered:
        return True
    return any(
        token in lowered
        for token in (".pdf", ".md", ".txt", ".docx", ".json", ".csv")
    )


def _workspace_has_any_files(path):
    root = Path(path)
    if not root.exists():
        return False
    return any(item.is_file() for item in root.rglob("*"))


def _load_gaps(workspace="."):
    path = Path(workspace) / ".brain" / "knowledge_gaps.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return []
    return payload.get("gaps", [])


def _open_knowledge_gap_count(workspace="."):
    gaps = _load_gaps(workspace)
    return sum(1 for gap in gaps if gap.get("status") == "open")


def _matching_gap_count(task, workspace="."):
    normalized_task = str(task or "").strip().lower()
    if not normalized_task:
        return 0
    gaps = _load_gaps(workspace)
    return sum(
        1
        for gap in gaps
        if gap.get("status") == "open" and str(gap.get("query") or "").strip().lower() == normalized_task
    )


def _bootstrap_signal(task, workspace="."):
    if _task_has_any(task, BOOTSTRAP_TOKENS):
        return True, "explicit bootstrap/setup intent"

    matching_gaps = _matching_gap_count(task, workspace)
    if matching_gaps >= 2:
        return True, f"repeated unresolved knowledge gaps for the same request ({matching_gaps} open)"

    return False, ""


def route_request(task, *, workspace=".", route=None):
    provided = _normalize_provided_route(route)
    if provided:
        return provided

    lowered = str(task or "").strip().lower()
    if not lowered:
        return {
            "intent": "query",
            "lane": "query",
            "reason": "empty task defaults to query safety path",
            "fallback_allowed": True,
            "source": "router",
        }

    if _task_has_any(lowered, RESUME_TOKENS):
        return {
            "intent": "resume",
            "lane": "resume",
            "reason": "resume intent detected",
            "fallback_allowed": True,
            "source": "router",
        }

    if _task_has_any(lowered, COVERAGE_TOKENS):
        return {
            "intent": "coverage",
            "lane": "coverage",
            "reason": "coverage/gap analysis intent detected",
            "fallback_allowed": True,
            "source": "router",
        }

    if _task_has_any(lowered, INGEST_TOKENS) or _raw_source_mentioned(lowered):
        return {
            "intent": "ingest",
            "lane": "ingest",
            "reason": "ingest/source handling intent detected",
            "fallback_allowed": True,
            "source": "router",
        }

    bootstrap, bootstrap_reason = _bootstrap_signal(lowered, workspace=workspace)
    if bootstrap:
        return {
            "intent": "bootstrap",
            "lane": "bootstrap",
            "reason": bootstrap_reason,
            "fallback_allowed": True,
            "source": "router",
        }

    if _looks_like_deep_query(lowered):
        return {
            "intent": "query_deep",
            "lane": "query_deep",
            "reason": "analysis-style query detected",
            "fallback_allowed": True,
            "source": "router",
        }

    if _looks_like_query(lowered):
        return {
            "intent": "query",
            "lane": "query",
            "reason": "question-style query detected",
            "fallback_allowed": True,
            "source": "router",
        }

    return {
        "intent": "legacy_execution",
        "lane": "legacy_execution",
        "reason": "preserve current bounded execution path for non-question tasks",
        "fallback_allowed": False,
        "source": "router",
    }
