import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


APPROVE_SCHEMA_VERSION = "abw.approve_draft.v1"
APPROVE_PREVIEW_SCHEMA_VERSION = "abw.approve_draft.preview.v1"
APPROVE_RESULT_SCHEMA_VERSION = "abw.approve_draft.result.v1"
APPROVE_CONFIRMATION_TEXT = "Approve this draft as trusted wiki"

ERROR_TRUST_REQUIRED = "TRUST_REQUIRED"
ERROR_WRONG_WORKSPACE = "WRONG_WORKSPACE"
ERROR_INVALID_DRAFT_PATH = "INVALID_DRAFT_PATH"
ERROR_DRAFT_NOT_FOUND = "DRAFT_NOT_FOUND"
ERROR_QUEUE_ENTRY_MISSING = "QUEUE_ENTRY_MISSING"
ERROR_QUEUE_STATUS_MISMATCH = "QUEUE_STATUS_MISMATCH"
ERROR_STALE_DRAFT_HASH = "STALE_DRAFT_HASH"
ERROR_TARGET_WIKI_EXISTS = "TARGET_WIKI_EXISTS"
ERROR_CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
ERROR_CONFIRMATION_TOKEN_MISMATCH = "CONFIRMATION_TOKEN_MISMATCH"
ERROR_PATH_TRAVERSAL_BLOCKED = "PATH_TRAVERSAL_BLOCKED"
ERROR_SCHEMA_UNSUPPORTED = "SCHEMA_UNSUPPORTED"
ERROR_INTERNAL_ERROR = "INTERNAL_ERROR"


def candidate_path_tokens(task):
    pattern = r"[A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+"
    return [token.strip("`'\"()[]{}<>.,;:") for token in re.findall(pattern, str(task or ""))]


def extract_draft_reference(task, workspace="."):
    workspace_root = Path(workspace).resolve()
    for token in candidate_path_tokens(task):
        candidate = Path(token)
        if not candidate.is_absolute():
            candidate = workspace_root / candidate
        try:
            relative = candidate.resolve(strict=False).relative_to(workspace_root)
        except ValueError:
            continue
        relative_text = str(relative).replace("\\", "/")
        if relative_text.startswith("drafts/"):
            return relative_text
    return None


def extract_draft_path(task, workspace="."):
    draft_relpath = extract_draft_reference(task, workspace=workspace)
    if not draft_relpath:
        return None, None
    candidate = Path(workspace).resolve() / draft_relpath
    if candidate.exists() and candidate.is_file():
        return draft_relpath, candidate
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


def list_drafts(workspace):
    queue = load_json(ingest_queue_path(workspace), {"items": []})
    pending = [item for item in queue.get("items", []) if item.get("status") == "review_needed"]
    return {"pending_drafts": pending}


def wiki_relpath_from_draft(draft_relpath):
    draft_name = Path(draft_relpath).name
    stem = draft_name[:-9] if draft_name.endswith("_draft.md") else Path(draft_name).stem
    return f"wiki/{stem}.md"


def draft_id_from_relpath(draft_relpath):
    draft_name = Path(str(draft_relpath or "")).name
    if draft_name.endswith("_draft.md"):
        return draft_name[:-9]
    return Path(draft_name).stem


def compute_draft_hash(path):
    draft_path = Path(path)
    digest = hashlib.sha256()
    with draft_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def confirmation_token_for(draft_id, draft_hash):
    return f"approve:{draft_id}:{draft_hash}"


def review_audit_id(draft_relpath, draft_hash, *, preview):
    digest = hashlib.sha256(f"{draft_relpath}|{draft_hash}|{now_iso()}".encode("utf-8")).hexdigest()[:12]
    prefix = "approve-preview" if preview else "approve"
    return f"{prefix}-{digest}"


def _summary_lines(text, limit=3):
    lines = []
    for raw_line in str(text or "").splitlines():
        clean = raw_line.strip().lstrip("#").strip("-").strip()
        if clean:
            lines.append(clean)
        if len(lines) >= limit:
            break
    return lines


def _draft_preview_summary(draft_path, queue_item):
    draft_text = Path(draft_path).read_text(encoding="utf-8", errors="replace")
    key_lines = _summary_lines(draft_text, limit=3)
    title = key_lines[0] if key_lines else Path(draft_path).name
    source_path = str(queue_item.get("raw") or queue_item.get("source_path") or "").strip() or None
    review_notes = []
    if queue_item.get("status"):
        review_notes.append(f"queue_status: {queue_item.get('status')}")
    if queue_item.get("review_reason"):
        review_notes.append(f"review_reason: {queue_item.get('review_reason')}")
    return {
        "title": title,
        "source_path": source_path,
        "summary": " ".join(key_lines[:2]) if key_lines else "Draft content preview unavailable.",
        "review_notes": review_notes,
    }


def _workspace_roots(workspace):
    root = Path(workspace).expanduser().resolve()
    return root, root / "drafts", root / "wiki"


def _resolve_workspace_relative_path(workspace_root, candidate_text, *, required_prefix):
    candidate_value = str(candidate_text or "").strip().replace("\\", "/")
    if not candidate_value:
        return None, ERROR_INVALID_DRAFT_PATH, "draft_path is required."
    if any(token in candidate_value for token in ("*", "?", "[", "]")):
        return None, ERROR_INVALID_DRAFT_PATH, "Wildcard draft paths are not allowed."
    candidate = Path(candidate_value)
    if candidate.is_absolute():
        return None, ERROR_INVALID_DRAFT_PATH, "draft_path must be workspace-relative."
    resolved = (workspace_root / candidate).resolve(strict=False)
    try:
        relative = resolved.relative_to(workspace_root)
    except ValueError:
        return None, ERROR_PATH_TRAVERSAL_BLOCKED, "Resolved draft path escapes the workspace."
    relative_text = str(relative).replace("\\", "/")
    if not relative_text.startswith(required_prefix):
        return None, ERROR_INVALID_DRAFT_PATH, f"draft_path must be under {required_prefix}."
    return relative_text, None, None


def _derive_wiki_target(workspace_root, draft_relpath):
    wiki_relpath = wiki_relpath_from_draft(draft_relpath)
    resolved = (workspace_root / wiki_relpath).resolve(strict=False)
    try:
        relative = resolved.relative_to(workspace_root)
    except ValueError:
        return None, None, ERROR_PATH_TRAVERSAL_BLOCKED, "Derived wiki path escapes the workspace."
    relative_text = str(relative).replace("\\", "/")
    if not relative_text.startswith("wiki/"):
        return None, None, ERROR_PATH_TRAVERSAL_BLOCKED, "Derived wiki path is outside wiki/."
    return relative_text, resolved, None, None


def _blocked_result(
    *,
    workspace,
    draft_path,
    error_code,
    message,
    warnings=None,
    errors=None,
    audit_id=None,
):
    return {
        "schema_version": APPROVE_RESULT_SCHEMA_VERSION,
        "status": "blocked",
        "approved": False,
        "promotionPerformed": False,
        "manualReviewRequired": True,
        "workspace": str(workspace),
        "draft_path": str(draft_path or "").strip() or None,
        "message": message,
        "error_code": error_code,
        "warnings": list(warnings or []),
        "errors": list(errors or [{"code": error_code, "message": message}]),
        "no_mutation_confirmed": True,
        "audit_id": audit_id or review_audit_id(str(draft_path or "unknown"), error_code, preview=False),
    }


def build_approve_preview(*, workspace, draft_relpath, draft_hash, draft_id, queue_item, target_wiki_path):
    return {
        "schema_version": APPROVE_PREVIEW_SCHEMA_VERSION,
        "status": "preview_ready",
        "would_approve": True,
        "approved": False,
        "promotionPerformed": False,
        "manualReviewRequired": True,
        "workspace": str(workspace),
        "draft_path": draft_relpath,
        "draft_id": draft_id,
        "draft_hash": draft_hash,
        "target_wiki_path": target_wiki_path,
        "current_queue_status": str(queue_item.get("status") or "").strip() or None,
        "trusted_workspace_required": True,
        "warnings": [
            "This draft is not trusted wiki yet.",
            "Approval affects only this selected draft.",
            "No auto-promotion is performed.",
        ],
        "blocking_errors": [],
        "preview_summary": _draft_preview_summary(Path(workspace) / draft_relpath, queue_item),
        "required_confirmation": {
            "confirmation_token": confirmation_token_for(draft_id, draft_hash),
            "confirmation_text": APPROVE_CONFIRMATION_TEXT,
        },
        "audit_id": review_audit_id(draft_relpath, draft_hash, preview=True),
    }


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


def approve_draft_request(payload):
    request = dict(payload or {})
    workspace_value = str(request.get("workspace") or "").strip()
    if not workspace_value:
        return _blocked_result(
            workspace="",
            draft_path=request.get("draft_path"),
            error_code=ERROR_WRONG_WORKSPACE,
            message="workspace is required.",
        )
    workspace_root, _, _ = _workspace_roots(workspace_value)
    schema_version = str(request.get("schema_version") or "").strip()
    if schema_version and schema_version != APPROVE_SCHEMA_VERSION:
        return _blocked_result(
            workspace=workspace_root,
            draft_path=request.get("draft_path"),
            error_code=ERROR_SCHEMA_UNSUPPORTED,
            message=f"Unsupported schema_version: {schema_version}",
        )

    draft_relpath, path_error, path_message = _resolve_workspace_relative_path(
        workspace_root,
        request.get("draft_path"),
        required_prefix="drafts/",
    )
    if path_error:
        return _blocked_result(
            workspace=workspace_root,
            draft_path=request.get("draft_path"),
            error_code=path_error,
            message=path_message,
        )

    draft_path = workspace_root / draft_relpath
    if not draft_path.exists() or not draft_path.is_file():
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=ERROR_DRAFT_NOT_FOUND,
            message=f"Draft file '{draft_relpath}' does not exist.",
        )

    expected_draft_id = draft_id_from_relpath(draft_relpath)
    provided_draft_id = str(request.get("draft_id") or "").strip()
    if provided_draft_id and provided_draft_id != expected_draft_id:
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=ERROR_INVALID_DRAFT_PATH,
            message=f"draft_id '{provided_draft_id}' does not match the selected draft.",
        )

    queue, queue_item = validate_queue_entry(workspace_root, draft_relpath)
    if queue_item is None:
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=ERROR_QUEUE_ENTRY_MISSING,
            message=f"Draft file '{draft_relpath}' is not present in ingest_queue.",
        )

    expected_queue_status = str(request.get("expected_queue_status") or "review_needed").strip() or "review_needed"
    if expected_queue_status != "review_needed":
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=ERROR_QUEUE_STATUS_MISMATCH,
            message="Only expected_queue_status=review_needed is supported in v1.",
        )
    actual_queue_status = str(queue_item.get("status") or "").strip()
    if actual_queue_status != expected_queue_status:
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=ERROR_QUEUE_STATUS_MISMATCH,
            message=f"Draft queue status is '{actual_queue_status or 'unknown'}', expected '{expected_queue_status}'.",
        )

    draft_hash = compute_draft_hash(draft_path)
    expected_draft_hash = str(request.get("expected_draft_hash") or "").strip()
    if expected_draft_hash and expected_draft_hash != draft_hash:
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=ERROR_STALE_DRAFT_HASH,
            message="Expected draft hash does not match the current draft hash.",
        )

    target_wiki_path, target_wiki_abs, target_error, target_message = _derive_wiki_target(workspace_root, draft_relpath)
    if target_error:
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=target_error,
            message=target_message,
        )

    if target_wiki_abs.exists():
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=ERROR_TARGET_WIKI_EXISTS,
            message=f"Target wiki path '{target_wiki_path}' already exists.",
        )

    draft_id = provided_draft_id or expected_draft_id
    if bool(request.get("dry_run", False)):
        return build_approve_preview(
            workspace=workspace_root,
            draft_relpath=draft_relpath,
            draft_hash=draft_hash,
            draft_id=draft_id,
            queue_item=queue_item,
            target_wiki_path=target_wiki_path,
        )

    confirm = request.get("confirm") if isinstance(request.get("confirm"), dict) else {}
    if confirm.get("user_confirmed") is not True:
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=ERROR_CONFIRMATION_REQUIRED,
            message="Explicit confirmation is required before approval.",
        )

    expected_token = confirmation_token_for(draft_id, draft_hash)
    confirmation_token = str(confirm.get("confirmation_token") or "").strip()
    if confirmation_token != expected_token:
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=ERROR_CONFIRMATION_TOKEN_MISMATCH,
            message="confirmation_token does not match the selected draft preview.",
        )

    confirmation_text = str(confirm.get("confirmation_text") or "").strip()
    if confirmation_text != APPROVE_CONFIRMATION_TEXT:
        return _blocked_result(
            workspace=workspace_root,
            draft_path=draft_relpath,
            error_code=ERROR_CONFIRMATION_REQUIRED,
            message="confirmation_text is missing or invalid.",
        )

    audit_id = review_audit_id(draft_relpath, draft_hash, preview=False)
    wiki_relpath = promote_draft(workspace_root, draft_relpath)
    updated_item = update_queue_status(workspace_root, draft_relpath)
    queue_transition = {
        "from": expected_queue_status,
        "to": "approved",
    }
    result = {
        "schema_version": APPROVE_RESULT_SCHEMA_VERSION,
        "status": "approved",
        "approved": True,
        "promotionPerformed": True,
        "manualReviewRequired": False,
        "workspace": str(workspace_root),
        "draft_path": draft_relpath,
        "approved_wiki_path": wiki_relpath,
        "queue_transition": queue_transition,
        "review_log_path": str(review_log_path(workspace_root).relative_to(workspace_root)).replace("\\", "/"),
        "audit_id": audit_id,
        "warnings": [],
        "errors": [],
    }
    append_jsonl(
        review_log_path(workspace_root),
        {
            "timestamp": now_iso(),
            "audit_id": audit_id,
            "mode": "approve_draft_v1",
            "operator_note": str(request.get("operator_note") or "").strip() or None,
            "request": {
                "schema_version": APPROVE_SCHEMA_VERSION,
                "draft_path": draft_relpath,
                "draft_id": draft_id,
                "expected_draft_hash": draft_hash,
                "expected_queue_status": expected_queue_status,
            },
            "result": result,
            "queue_item": updated_item,
        },
    )
    return result


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
