import re
import unicodedata


DRAFT_PATH_PATTERN = re.compile(
    r"(?P<draft>(?:drafts[\\/])[A-Za-z0-9_./\\-]+\.md)\b",
    flags=re.IGNORECASE,
)

INTENT_PATTERNS = [
    {
        "intent": "resume",
        "lane": "resume",
        "reason": "resume intent detected",
        "fallback_allowed": True,
        "patterns": [
            "resume",
            "continue",
            "pick up where we left off",
            "pick up previous work",
            "continue prior work",
            "continue previous work",
            "tiep tuc",
            "dang do",
        ],
    },
    {
        "intent": "help",
        "lane": "help",
        "reason": "help intent detected",
        "fallback_allowed": True,
        "patterns": [
            "help",
            "/help",
            "giup",
            "tro giup",
        ],
    },
    {
        "intent": "dashboard",
        "lane": "dashboard",
        "reason": "dashboard intent detected",
        "fallback_allowed": True,
        "patterns": [
            "dashboard",
            "system dashboard",
            "abw dashboard",
            "bang dieu khien",
            "tong quan he",
        ],
    },
    {
        "intent": "wizard",
        "lane": "wizard",
        "reason": "guided wizard intent detected",
        "fallback_allowed": True,
        "patterns": [
            "wizard",
            "guided workflow",
            "guide me",
            "start wizard",
            "huong dan tung buoc",
        ],
    },
    {
        "intent": "system_trend",
        "lane": "system_trend",
        "reason": "system trend intent detected",
        "fallback_allowed": True,
        "patterns": [
            "system trend",
            "trend system",
            "monitor trend",
            "abw trend",
            "xu huong he",
            "theo doi he",
        ],
    },
    {
        "intent": "list_drafts",
        "lane": "list_drafts",
        "reason": "draft review listing intent detected",
        "fallback_allowed": True,
        "patterns": [
            "list drafts",
            "pending drafts",
            "danh sach nhap",
            "ban nhap dang cho",
        ],
    },
    {
        "intent": "review_drafts",
        "lane": "review_drafts",
        "reason": "batch draft review intent detected",
        "fallback_allowed": True,
        "patterns": [
            "review drafts",
            "duyet cac nhap",
            "xem cac nhap",
        ],
    },
    {
        "intent": "approve_draft",
        "lane": "approve_draft",
        "reason": "explicit draft approval intent with draft path detected",
        "fallback_allowed": False,
        "requires_draft_path": True,
        "patterns": [
            "approve draft",
            "duyet nhap",
        ],
    },
    {
        "intent": "explain_draft",
        "lane": "explain_draft",
        "reason": "explicit draft explanation intent with draft path detected",
        "fallback_allowed": True,
        "requires_draft_path": True,
        "patterns": [
            "explain draft",
            "review draft",
            "summarize draft",
            "giai thich nhap",
            "tom tat nhap",
        ],
    },
    {
        "intent": "coverage",
        "lane": "coverage",
        "reason": "coverage/gap analysis intent detected",
        "fallback_allowed": True,
        "patterns": [
            "coverage",
            "knowledge coverage",
            "gap report",
            "coverage report",
            "missing knowledge",
            "top gaps",
            "he dang thieu gi",
            "thieu kien thuc gi",
        ],
    },
    {
        "intent": "ingest",
        "lane": "ingest",
        "reason": "ingest/source handling intent detected",
        "fallback_allowed": True,
        "patterns": [
            "/abw-ingest",
            "ingest",
            "add to wiki",
            "process source",
            "process raw",
            "review raw",
            "queue source",
            "nap tai lieu",
            "xu ly raw",
        ],
    },
    {
        "intent": "bootstrap",
        "lane": "bootstrap",
        "reason": "explicit bootstrap/setup intent",
        "fallback_allowed": True,
        "patterns": [
            "/abw-bootstrap",
            "bootstrap",
            "greenfield",
            "new project",
            "new idea",
            "start from scratch",
            "project setup",
            "setup project",
            "bat dau moi",
        ],
    },
]

DEEP_QUERY_PATTERNS = [
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
]

QUERY_PATTERNS = [
    "what is",
    "explain",
    "summarize",
    "summary",
    "why",
    "how",
    "which",
    "where",
    "who",
    "la gi",
    "giai thich",
    "tra cuu",
    "tim trong wiki",
]


def normalize_input(text):
    lowered = str(text or "").strip().lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    without_marks = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(without_marks.split())


def extract_draft_path(task):
    match = DRAFT_PATH_PATTERN.search(str(task or ""))
    if not match:
        return None
    return match.group("draft").replace("\\", "/")


def has_any_pattern(normalized_task, patterns):
    return any(pattern in normalized_task for pattern in patterns)


def match_intent(task):
    normalized_task = normalize_input(task)
    if not normalized_task:
        return None

    draft_path = extract_draft_path(task)
    for rule in INTENT_PATTERNS:
        if not has_any_pattern(normalized_task, rule.get("patterns", [])):
            continue
        if rule.get("requires_draft_path") and not draft_path:
            continue
        params = {}
        if draft_path:
            params["draft_path"] = draft_path
        return {
            "intent": rule["intent"],
            "lane": rule["lane"],
            "reason": rule["reason"],
            "fallback_allowed": bool(rule.get("fallback_allowed", True)),
            "params": params,
        }
    return None


def looks_like_deep_query(task):
    normalized_task = normalize_input(task)
    if has_any_pattern(normalized_task, DEEP_QUERY_PATTERNS):
        return True
    if normalized_task.count("?") >= 2:
        return True
    if " and " in normalized_task and has_any_pattern(normalized_task, QUERY_PATTERNS):
        return True
    return False


def looks_like_query(task):
    normalized_task = normalize_input(task)
    if has_any_pattern(normalized_task, QUERY_PATTERNS):
        return True
    return normalized_task.endswith("?")


def supported_lanes():
    lanes = {pattern["lane"] for pattern in INTENT_PATTERNS}
    lanes.update({"query", "query_deep", "legacy_execution"})
    return lanes
