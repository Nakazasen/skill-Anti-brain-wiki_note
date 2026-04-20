import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def candidate_path_tokens(task):
    pattern = r"[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+"
    return [token.strip("`'\"()[]{}<>.,;:") for token in re.findall(pattern, str(task or ""))]


def extract_draft_path(task, workspace="."):
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
        if not relative_text.startswith("drafts/"):
            continue
        if candidate.exists() and candidate.is_file():
            return relative_text, candidate
    return None, None


def ingest_queue_path(workspace="."):
    return Path(workspace) / ".brain" / "ingest_queue.json"


def review_log_path(workspace="."):
    return Path(workspace) / ".brain" / "review_log.jsonl"


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


def append_jsonl(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def validate_queue_entry(workspace, draft_relpath):
    queue = load_json(ingest_queue_path(workspace), {"items": []})
    for item in queue.get("items", []):
        if item.get("draft") == draft_relpath:
            return queue, item
    return queue, None


def wiki_relpath_from_draft(draft_relpath):
    draft_name = Path(draft_relpath).name
    stem = draft_name[:-9] if draft_name.endswith("_draft.md") else Path(draft_name).stem
    return f"wiki/{stem}.md"


def promote_draft(workspace, draft_relpath):
    workspace_root = Path(workspace).resolve()
    draft_path = workspace_root / draft_relpath
    wiki_relpath = wiki_relpath_from_draft(draft_relpath)
    wiki_path = workspace_root / wiki_relpath
    wiki_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(draft_path), str(wiki_path))
    return wiki_relpath


def update_queue_status(workspace, draft_relpath):
    queue, item = validate_queue_entry(workspace, draft_relpath)
    if item is None:
        raise ValueError("Draft file is not present in ingest_queue.")
    item["status"] = "approved"
    item["approved_at"] = now_iso()
    save_json(ingest_queue_path(workspace), queue)
    return item


def run(task: str, workspace: str) -> dict:
    workspace = str(workspace or ".")
    draft_relpath, draft_path = extract_draft_path(task, workspace=workspace)
    if draft_path is None:
        raise FileNotFoundError("No valid draft file path found in task.")

    if not draft_relpath.startswith("drafts/"):
        raise ValueError("Draft file must be under drafts/.")

    _, queue_item = validate_queue_entry(workspace, draft_relpath)
    if queue_item is None:
        raise ValueError("Draft file is not present in ingest_queue.")

    wiki_relpath = promote_draft(workspace, draft_relpath)
    updated_item = update_queue_status(workspace, draft_relpath)

    result = {
        "status": "approved",
        "draft": draft_relpath,
        "wiki": wiki_relpath,
        "message": "Draft promoted to trusted wiki",
    }
    append_jsonl(
        review_log_path(workspace),
        {
            "timestamp": now_iso(),
            "task": str(task or ""),
            "result": result,
            "queue_item": updated_item,
        },
    )
    return result
