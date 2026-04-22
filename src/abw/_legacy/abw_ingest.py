import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


MAX_SUMMARY_CHARS = 500
MAX_KEY_CONCEPTS = 5
MAX_QUERY_SUGGESTIONS = 5


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def candidate_path_tokens(task):
    pattern = r"[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+"
    return [token.strip("`'\"()[]{}<>.,;:") for token in re.findall(pattern, str(task or ""))]


def extract_raw_file_path(task, workspace="."):
    workspace_root = Path(workspace).resolve()
    for token in candidate_path_tokens(task):
        candidate = Path(token)
        if not candidate.is_absolute():
            candidate = workspace_root / candidate
        try:
            relative = candidate.resolve().relative_to(workspace_root)
        except ValueError:
            continue
        relative_text = str(relative).replace("\\", "/")
        if not relative_text.startswith("raw/"):
            continue
        if candidate.exists() and candidate.is_file():
            return relative_text, candidate
    return None, None


def deterministic_id(relative_raw_path, content):
    payload = f"{relative_raw_path}\n{content}".encode("utf-8", errors="ignore")
    return "ingest-" + hashlib.sha256(payload).hexdigest()[:16]


def manifest_path(workspace="."):
    return Path(workspace) / "processed" / "manifest.jsonl"


def ingest_queue_path(workspace="."):
    return Path(workspace) / ".brain" / "ingest_queue.json"


def ingest_runs_path(workspace="."):
    return Path(workspace) / ".brain" / "ingest_runs.jsonl"


def append_jsonl(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def load_json(path, default):
    path = Path(path)
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def save_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def summarize_text(content):
    lines = []
    for raw in str(content or "").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        lines.append(stripped)
    summary = " ".join(lines).strip()
    if len(summary) <= MAX_SUMMARY_CHARS:
        return summary
    return summary[: MAX_SUMMARY_CHARS - 3].rstrip() + "..."


def extract_key_concepts(content):
    counts = {}
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", str(content or "")):
        lowered = token.lower()
        if lowered in {
            "this",
            "that",
            "with",
            "from",
            "have",
            "there",
            "their",
            "about",
            "into",
            "while",
            "where",
            "which",
        }:
            continue
        counts[lowered] = counts.get(lowered, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    return [item[0] for item in ranked[:MAX_KEY_CONCEPTS]]


def build_possible_queries(concepts, relative_raw_path):
    stem = Path(relative_raw_path).stem.replace("-", " ")
    queries = [f"explain {stem}", f"summarize {stem}"]
    for concept in concepts:
        queries.append(f"what is {concept}")
    deduped = []
    seen = set()
    for query in queries:
        lowered = query.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        deduped.append(query)
        if len(deduped) >= MAX_QUERY_SUGGESTIONS:
            break
    return deduped


def draft_relpath(relative_raw_path):
    stem = Path(relative_raw_path).stem
    return f"drafts/{stem}_draft.md"


def write_draft(workspace, relative_raw_path, summary, concepts, possible_queries, source_id):
    relpath = draft_relpath(relative_raw_path)
    path = Path(workspace) / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            f"# Draft Knowledge: {Path(relative_raw_path).stem}",
            "",
            f"- source_id: {source_id}",
            f"- raw_file: {relative_raw_path}",
            f"- status: draft",
            "",
            "## Summary",
            summary or "No summary could be extracted from the raw file.",
            "",
            "## Key Concepts",
            *([f"- {concept}" for concept in concepts] or ["- none detected"]),
            "",
            "## Possible Queries",
            *([f"- {query}" for query in possible_queries] or ["- none suggested"]),
            "",
            "## Trust Notice",
            "This draft is review-needed and must not be treated as trusted wiki knowledge.",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")
    return relpath


def append_manifest_entry(workspace, source_id, relative_raw_path):
    path = manifest_path(workspace)
    entry = {
        "id": source_id,
        "source": relative_raw_path,
        "status": "processed",
        "created_at": now_iso(),
    }
    append_jsonl(path, entry)
    return entry


def update_ingest_queue(workspace, source_id, relative_raw_path, draft_file):
    path = ingest_queue_path(workspace)
    payload = load_json(path, {"items": [], "updated_at": now_iso()})
    item = {
        "id": source_id,
        "raw": relative_raw_path,
        "draft": draft_file,
        "status": "review_needed",
    }
    payload.setdefault("items", []).append(item)
    payload["updated_at"] = now_iso()
    save_json(path, payload)
    return item


def run(task: str, workspace: str) -> dict:
    workspace = str(workspace or ".")
    relative_raw_path, raw_path = extract_raw_file_path(task, workspace=workspace)
    if raw_path is None:
        raise FileNotFoundError("No valid raw file path found in task.")

    content = raw_path.read_text(encoding="utf-8-sig", errors="ignore")
    source_id = deterministic_id(relative_raw_path, content)
    summary = summarize_text(content)
    concepts = extract_key_concepts(content)
    possible_queries = build_possible_queries(concepts, relative_raw_path)

    append_manifest_entry(workspace, source_id, relative_raw_path)
    draft_file = write_draft(
        workspace,
        relative_raw_path,
        summary,
        concepts,
        possible_queries,
        source_id,
    )
    update_ingest_queue(workspace, source_id, relative_raw_path, draft_file)

    result = {
        "status": "draft_created",
        "raw_file": relative_raw_path,
        "draft_file": draft_file,
        "queue_status": "review_needed",
    }
    append_jsonl(
        ingest_runs_path(workspace),
        {
            "timestamp": now_iso(),
            "task": str(task or ""),
            "result": result,
            "source_id": source_id,
        },
    )
    return result
