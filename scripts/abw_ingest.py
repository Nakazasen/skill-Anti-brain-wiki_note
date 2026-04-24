import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from abw.conflicts import detect_conflicts, write_conflict_reports


MAX_SUMMARY_CHARS = 500
MAX_KEY_CONCEPTS = 5
MAX_QUERY_SUGGESTIONS = 5
SUPPORTED_EXTENSIONS = {".md", ".markdown", ".txt", ".rst", ".adoc"}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def candidate_path_tokens(task):
    tokens = []
    text = str(task or "").strip()
    match = re.search(r"\b(?:ingest|process|review)\s+([^\s]+)", text, flags=re.IGNORECASE)
    if match:
        tokens.append(match.group(1))
    pattern = r"(?:raw(?:[\\/][A-Za-z0-9_./\\-]+)?)|(?:[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+)"
    tokens.extend(re.findall(pattern, text))
    deduped = []
    seen = set()
    for token in tokens:
        cleaned = str(token).strip("`'\"()[]{}<>.,;:")
        key = cleaned.lower()
        if not cleaned or key in seen:
            continue
        seen.add(key)
        deduped.append(cleaned)
    return deduped


def resolve_raw_target(path_token, workspace="."):
    workspace_root = Path(workspace).resolve()
    token = str(path_token or "").strip().replace("\\", "/")
    if token.lower() in {"raw", "raw/"}:
        token = "raw"

    candidate = Path(token)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    try:
        resolved = candidate.resolve()
        relative = resolved.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError("Ingest path must stay inside the current workspace.") from exc

    relative_text = str(relative).replace("\\", "/")
    if relative_text == "raw":
        pass
    elif not relative_text.startswith("raw/"):
        raise ValueError("Ingest path must point to raw/ (file or directory).")

    if not resolved.exists():
        raise FileNotFoundError(
            f"Ingest path not found: {relative_text}. Use: ingest raw/<file> or ingest raw/"
        )
    return relative_text, resolved


def extract_ingest_target(task, workspace="."):
    invalid_error = None
    for token in candidate_path_tokens(task):
        try:
            return resolve_raw_target(token, workspace=workspace)
        except FileNotFoundError:
            raise
        except ValueError as exc:
            invalid_error = exc
            continue
    if invalid_error is not None:
        raise ValueError(str(invalid_error))
    raise FileNotFoundError("No valid ingest path found. Use: ingest raw/<file> or ingest raw/")


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


def list_supported_raw_files(raw_target_path):
    target = Path(raw_target_path)
    if target.is_file():
        if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file extension: {target.suffix or '<none>'}. "
                f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        return [target]
    if not target.is_dir():
        raise NotADirectoryError(f"Ingest target is not a file or directory: {target}")
    files = []
    for candidate in sorted(target.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(candidate)
    if not files:
        raise FileNotFoundError(
            "No supported files found in directory. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    return files


def ingest_single_file(raw_path, relative_raw_path, workspace):
    content = raw_path.read_text(encoding="utf-8-sig", errors="ignore")
    source_id = deterministic_id(relative_raw_path, content)
    summary = summarize_text(content)
    concepts = extract_key_concepts(content)
    possible_queries = build_possible_queries(concepts, relative_raw_path)
    conflicts = detect_conflicts(relative_raw_path, content, workspace)
    conflict_reports = write_conflict_reports(conflicts, workspace) if conflicts else []

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
    return {
        "status": "draft_created",
        "raw_file": relative_raw_path,
        "draft_file": draft_file,
        "queue_status": "review_needed",
        "conflict_count": len(conflict_reports),
        "conflict_reports": conflict_reports,
        "source_id": source_id,
    }


def run(task: str, workspace: str) -> dict:
    workspace = str(workspace or ".")
    relative_target, target_path = extract_ingest_target(task, workspace=workspace)
    raw_files = list_supported_raw_files(target_path)
    items = []
    for raw_file in raw_files:
        relative_raw_path = str(raw_file.resolve().relative_to(Path(workspace).resolve())).replace("\\", "/")
        items.append(ingest_single_file(raw_file, relative_raw_path, workspace))

    first = items[0]
    result = {
        "status": "draft_created" if len(items) == 1 else "drafts_created",
        "raw_file": first["raw_file"],
        "draft_file": first["draft_file"],
        "queue_status": first["queue_status"],
        "conflict_count": sum(item["conflict_count"] for item in items),
        "conflict_reports": [report for item in items for report in item.get("conflict_reports", [])],
        "ingested_count": len(items),
        "ingested_files": [item["raw_file"] for item in items],
        "draft_files": [item["draft_file"] for item in items],
        "target": relative_target,
        "target_type": "directory" if target_path.is_dir() else "file",
    }
    append_jsonl(
        ingest_runs_path(workspace),
        {
            "timestamp": now_iso(),
            "task": str(task or ""),
            "result": result,
            "source_id": first["source_id"],
        },
    )
    return result
