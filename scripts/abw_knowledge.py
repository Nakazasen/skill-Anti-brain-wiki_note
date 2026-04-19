import json
import re
from datetime import datetime, timezone
from pathlib import Path


KNOWLEDGE_TIER_RANK = {
    "E0_unknown": 0,
    "E1_fallback": 1,
    "E2_wiki": 2,
    "E3_grounded": 3,
}
KNOWLEDGE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "cho",
    "cua",
    "duoc",
    "explain",
    "for",
    "giai",
    "is",
    "la",
    "ly",
    "tai",
    "the",
    "thich",
    "this",
    "ve",
    "what",
    "why",
}
WIKI_SEARCH_DIRS = ("concepts", "entities", "timelines", "sources")


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_runtime_id():
    return str(int(datetime.now(timezone.utc).timestamp() * 1000))


def _normalize_text(text):
    lowered = str(text or "").lower()
    return re.sub(r"[^0-9a-z]+", " ", lowered, flags=re.IGNORECASE)


def _task_terms(task):
    tokens = []
    seen = set()
    for token in _normalize_text(task).split():
        if len(token) < 3 or token in KNOWLEDGE_STOPWORDS:
            continue
        if token not in seen:
            seen.add(token)
            tokens.append(token)
    return tokens


def _summarize_document(text, limit=420):
    content = str(text or "")
    if not content.strip():
        return ""

    lines = []
    in_frontmatter = False
    frontmatter_markers = 0
    for raw in content.splitlines():
        stripped = raw.strip()
        if stripped == "---" and frontmatter_markers < 2:
            in_frontmatter = not in_frontmatter
            frontmatter_markers += 1
            continue
        if in_frontmatter or not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)

    summary = " ".join(lines).strip()
    if len(summary) <= limit:
        return summary
    return summary[: limit - 3].rstrip() + "..."


def _candidate_source_tokens(task):
    pattern = r"[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+(?:#line-\d+)?"
    return [token.strip("`'\"()[]{}<>.,;:") for token in re.findall(pattern, str(task or ""))]


def _read_explicit_local_source(task, workspace="."):
    workspace_root = Path(workspace).resolve()
    for candidate in _candidate_source_tokens(task):
        line_no = None
        path_token = candidate
        if "#line-" in candidate:
            path_token, _, raw_line = candidate.partition("#line-")
            if raw_line.isdigit():
                line_no = int(raw_line)

        path = Path(path_token)
        if not path.is_absolute():
            path = workspace_root / path
        if not path.exists() or not path.is_file():
            continue

        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except OSError:
            continue

        if line_no is not None:
            lines = text.splitlines()
            if 1 <= line_no <= len(lines):
                text = lines[line_no - 1]

        summary = _summarize_document(text)
        if not summary:
            continue

        try:
            relative = str(path.relative_to(workspace_root))
        except ValueError:
            relative = str(path)

        return {
            "source": "local",
            "content": summary,
            "confidence": 0.95,
            "path": relative,
        }

    return None


def _search_wiki_context(task, workspace="."):
    workspace_root = Path(workspace).resolve()
    wiki_root = workspace_root / "wiki"
    if not wiki_root.exists():
        return None

    terms = _task_terms(task)
    if not terms:
        return None

    best = None
    for directory in WIKI_SEARCH_DIRS:
        search_dir = wiki_root / directory
        if not search_dir.exists():
            continue
        for path in search_dir.glob("*.md"):
            if path.name.startswith("."):
                continue
            try:
                text = path.read_text(encoding="utf-8-sig", errors="ignore")
            except OSError:
                continue

            haystack = f"{path.stem} {text}".lower()
            matches = sum(1 for term in terms if term in haystack)
            if matches == 0:
                continue

            score = matches
            stem = path.stem.lower()
            score += sum(2 for term in terms if term in stem)
            title_match = re.search(r'^title:\s*"?(.*?)"?$', text, flags=re.IGNORECASE | re.MULTILINE)
            if title_match:
                title = title_match.group(1).lower()
                score += sum(2 for term in terms if term in title)

            summary = _summarize_document(text)
            if not summary:
                continue

            confidence = min(0.9, 0.35 + (0.1 * matches) + (0.05 * min(score, 5)))
            candidate = {
                "source": "wiki",
                "content": summary,
                "confidence": round(confidence, 2),
                "path": str(path.relative_to(workspace_root)),
                "_score": score,
            }
            if best is None or candidate["_score"] > best["_score"]:
                best = candidate

    if not best:
        return None

    best.pop("_score", None)
    return best


def _knowledge_gap_path(workspace="."):
    return Path(workspace) / ".brain" / "knowledge_gaps.json"


def log_knowledge_gap(task, workspace=".", searched_locations=None, reason="No local knowledge source matched the task."):
    path = _knowledge_gap_path(workspace)
    payload = {
        "_schema": "hybrid-abw/knowledge-gaps/1.0",
        "_description": "Log of knowledge gaps. See templates/knowledge_gaps.example.json for entry format.",
        "updated_at": now_iso(),
        "stats": {"total": 0, "open": 0, "investigating": 0, "resolved": 0},
        "gaps": [],
    }
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass

    gaps = payload.setdefault("gaps", [])
    for gap in gaps:
        if gap.get("query") == task and gap.get("status") == "open":
            payload["updated_at"] = now_iso()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return gap.get("id") or gap.get("gap_id")

    gap_id = f"gap-{new_runtime_id()}"
    gaps.append(
        {
            "id": gap_id,
            "query": task,
            "context": "ABW runner knowledge retrieval",
            "searched_locations": searched_locations or ["wiki/"],
            "notebooklm_checked": False,
            "notebooklm_notebook_id": None,
            "reason": reason,
            "priority": "medium",
            "status": "open",
            "created_at": now_iso(),
            "resolved_at": None,
            "resolution_path": None,
            "suggested_sources": [],
        }
    )
    stats = payload.setdefault("stats", {})
    stats["total"] = len(gaps)
    stats["open"] = sum(1 for gap in gaps if gap.get("status") == "open")
    stats["investigating"] = sum(1 for gap in gaps if gap.get("status") == "investigating")
    stats["resolved"] = sum(1 for gap in gaps if gap.get("status") == "resolved")
    payload["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return gap_id


def _get_knowledge_context(task, workspace="."):
    explicit = _read_explicit_local_source(task, workspace=workspace)
    if explicit:
        return explicit

    wiki_context = _search_wiki_context(task, workspace=workspace)
    if wiki_context:
        return wiki_context

    return {
        "source": "none",
        "content": "",
        "confidence": 0.0,
        "path": None,
    }


def get_knowledge_context(task: str) -> dict:
    return _get_knowledge_context(task, workspace=".")


def compute_knowledge_score(result):
    context = result.get("knowledge_context") or {}
    source = context.get("source")
    confidence = float(context.get("confidence") or 0.0)
    if source == "wiki":
        return max(1, min(3, int(round(confidence * 3))))
    if source == "local":
        return max(2, min(3, int(round(confidence * 3))))
    return 0


def compute_knowledge_tier(result):
    context = result.get("knowledge_context") or {}
    source = context.get("source")
    if source == "local":
        return "E3_grounded"
    if source == "wiki":
        return "E2_wiki"
    return "E0_unknown"


def build_source_summary(result):
    context = result.get("knowledge_context") or {}
    source = context.get("source")
    if source == "wiki":
        return "local_wiki"
    if source == "local":
        return "explicit_local"
    return "unknown"


def enrich_knowledge_result(task, workspace="."):
    context = _get_knowledge_context(task, workspace=workspace)
    result = {
        "task": task,
        "knowledge_context": context,
        "refinement_history": [],
        "strategy_trace": {},
        "semantic_fix_applied": False,
    }
    if context.get("source") == "wiki":
        result["evidence"] = f"wiki retrieval matched {context.get('path')}"
        result["gap_logged"] = False
    elif context.get("source") == "local":
        result["evidence"] = f"explicit local retrieval matched {context.get('path')}"
        result["gap_logged"] = False
    else:
        result["evidence"] = "no usable knowledge source found"
        result["gap_logged"] = True
    return result


def attach_knowledge_output(result, answer_text=None):
    context = result.get("knowledge_context") or {}
    result["knowledge_output"] = {
        "answer": answer_text if answer_text is not None else result.get("answer") or result.get("execution_result"),
        "tier": result.get("knowledge_evidence_tier"),
        "score": result.get("knowledge_source_score"),
        "gap_logged": result.get("gap_logged", False),
        "source_summary": build_source_summary(result),
        "source": context.get("source"),
        "content": context.get("content"),
        "confidence": context.get("confidence"),
    }
    return result
